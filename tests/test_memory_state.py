import base64
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import get_connection, get_run
from app.main import app, get_anthropic_client
from app.pipeline import resume_conversion, run_conversion_pipeline

SUBMITTER_AUTH = "Basic " + base64.b64encode(b"submitter:submitter123").decode()

GENERATED = {
    "pydantic_model": "class M: pass",
    "fastapi_endpoint": "def endpoint(): pass",
    "rule_functions": "def rule(): pass",
    "pytest_tests": "def test_x(): pass",
}
SAMPLE_A = "tests/fixtures/miniform/valid/expense_request.json"
SAMPLE_B = "tests/fixtures/miniform/valid/leave_request.json"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DEFAULT_DB_PATH", tmp_path / "test.db")


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_resume_skips_already_converted_step(mock_convert_form, mock_write, mock_sandbox, tmp_path):
    mock_convert_form.return_value = GENERATED
    # First attempt: conversion succeeds, but the sandbox step crashes.
    mock_sandbox.side_effect = RuntimeError("docker daemon unreachable")

    client = MagicMock()
    with pytest.raises(RuntimeError):
        run_conversion_pipeline(client, SAMPLE_A, workdir=tmp_path)

    conn = get_connection(tmp_path / "test.db")
    runs = conn.execute("SELECT * FROM conversion_runs").fetchall()
    assert len(runs) == 1
    run_id = runs[0]["run_id"]
    run = get_run(conn, run_id)
    assert run["stage"] == "converted"  # conversion checkpoint was saved
    assert run["sandbox_output"] is None  # sandbox checkpoint was not

    # Resume: sandbox now succeeds. The paid conversion step must NOT rerun.
    mock_sandbox.side_effect = None
    mock_sandbox.return_value = {"passed": True, "stdout": "2 passed", "stderr": "", "returncode": 0}
    result = resume_conversion(client, run_id, workdir=tmp_path)

    assert mock_convert_form.call_count == 1  # still only called once overall
    assert result["sandbox_passed"] is True
    run = get_run(conn, run_id)
    assert run["stage"] == "validated"
    assert run["status"] == "pending_review"


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.convert_form")
def test_resume_is_a_no_op_once_validated(mock_convert_form, mock_sandbox, tmp_path):
    mock_convert_form.return_value = GENERATED
    mock_sandbox.return_value = {"passed": True, "stdout": "ok", "stderr": "", "returncode": 0}

    client = MagicMock()
    result1 = run_conversion_pipeline(client, SAMPLE_A, workdir=tmp_path)
    result2 = resume_conversion(client, result1["run_id"], workdir=tmp_path)

    assert mock_convert_form.call_count == 1
    assert mock_sandbox.call_count == 1
    assert result2["sandbox_passed"] is True


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_two_runs_do_not_leak_into_each_other(mock_convert_form, mock_write, mock_sandbox, tmp_path):
    generated_a = {**GENERATED, "pydantic_model": "class A: pass"}
    generated_b = {**GENERATED, "pydantic_model": "class B: pass"}
    mock_convert_form.side_effect = [generated_a, generated_b]
    mock_sandbox.return_value = {"passed": True, "stdout": "ok", "stderr": "", "returncode": 0}

    client = MagicMock()
    result_a = run_conversion_pipeline(client, SAMPLE_A, workdir=tmp_path)
    result_b = run_conversion_pipeline(client, SAMPLE_B, workdir=tmp_path)

    assert result_a["run_id"] != result_b["run_id"]
    assert result_a["generated_code"]["pydantic_model"] == "class A: pass"
    assert result_b["generated_code"]["pydantic_model"] == "class B: pass"

    conn = get_connection(tmp_path / "test.db")
    run_a = get_run(conn, result_a["run_id"])
    run_b = get_run(conn, result_b["run_id"])
    assert json.loads(run_a["generated_code"])["pydantic_model"] == "class A: pass"
    assert json.loads(run_b["generated_code"])["pydantic_model"] == "class B: pass"

    # write_generated_project is mocked (no real docker needed here), but the
    # call arguments prove each run was pointed at its own output directory.
    call_dirs = [call.args[0] for call in mock_write.call_args_list]
    assert len(set(call_dirs)) == 2
    assert all(str(result_a["run_id"]) in str(d) or str(result_b["run_id"]) in str(d) for d in call_dirs)


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_no_api_key_leaks_into_stored_run_data(mock_convert_form, mock_write, mock_sandbox, tmp_path):
    secret = os.environ.get("ANTHROPIC_API_KEY", "sk-ant-test-placeholder-should-never-appear")
    mock_convert_form.return_value = GENERATED
    mock_sandbox.return_value = {"passed": True, "stdout": "ok, no secrets here", "stderr": "", "returncode": 0}

    client = MagicMock()
    result = run_conversion_pipeline(client, SAMPLE_A, workdir=tmp_path)

    conn = get_connection(tmp_path / "test.db")
    run = get_run(conn, result["run_id"])
    serialized = json.dumps(run)
    assert secret not in serialized


@pytest.fixture
def api_client():
    app.dependency_overrides[get_anthropic_client] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_resume_endpoint_recovers_from_a_crashed_run(mock_convert_form, mock_write, mock_sandbox, api_client):
    mock_convert_form.return_value = GENERATED
    mock_sandbox.side_effect = RuntimeError("simulated crash")

    # The crash is unhandled on purpose (simulating e.g. a Docker daemon
    # outage) and propagates through the test client; the run is still
    # checkpointed in the database up to the point of the crash.
    with pytest.raises(RuntimeError):
        api_client.post(
            "/convert", json={"sample_name": "expense_request"}, headers={"Authorization": SUBMITTER_AUTH}
        )

    conn = get_connection()
    runs = [r for r in conn.execute("SELECT * FROM conversion_runs ORDER BY created_at DESC").fetchall()]
    run_id = runs[0]["run_id"]

    mock_sandbox.side_effect = None
    mock_sandbox.return_value = {"passed": True, "stdout": "ok", "stderr": "", "returncode": 0}
    resume_resp = api_client.post(f"/convert/{run_id}/resume", headers={"Authorization": SUBMITTER_AUTH})
    assert resume_resp.status_code == 200
    assert resume_resp.json()["sandbox_passed"] is True
    assert mock_convert_form.call_count == 1

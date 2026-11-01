import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.main import app, get_anthropic_client

SUBMITTER_AUTH = "Basic " + base64.b64encode(b"submitter:submitter123").decode()
REVIEWER_AUTH = "Basic " + base64.b64encode(b"reviewer:reviewer123").decode()

GENERATED = {
    "pydantic_model": "class M: pass",
    "fastapi_endpoint": "def endpoint(): pass",
    "rule_functions": "def rule(): pass",
    "pytest_tests": "def test_x(): pass",
}


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DEFAULT_DB_PATH", tmp_path / "test.db")


@pytest.fixture
def client():
    app.dependency_overrides[get_anthropic_client] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_happy_path_convert_and_approve(mock_convert_form, mock_write, mock_sandbox, client):
    mock_convert_form.return_value = GENERATED
    mock_sandbox.return_value = {"passed": True, "stdout": "2 passed", "stderr": "", "returncode": 0}

    resp = client.post(
        "/convert", json={"sample_name": "expense_request"}, headers={"Authorization": SUBMITTER_AUTH}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sandbox_passed"] is True
    run_id = data["run_id"]

    approve_resp = client.post(
        f"/review/{run_id}/approve", json={"note": ""}, headers={"Authorization": REVIEWER_AUTH}
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_rejection_path_sandbox_fails_then_reviewer_rejects(mock_convert_form, mock_write, mock_sandbox, client):
    mock_convert_form.return_value = GENERATED
    mock_sandbox.return_value = {"passed": False, "stdout": "1 failed", "stderr": "", "returncode": 1}

    resp = client.post(
        "/convert", json={"sample_name": "leave_request"}, headers={"Authorization": SUBMITTER_AUTH}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sandbox_passed"] is False
    run_id = data["run_id"]

    reject_resp = client.post(
        f"/review/{run_id}/reject",
        json={"note": "sandbox failed"},
        headers={"Authorization": REVIEWER_AUTH},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"


def test_unknown_sample_name_rejected(client):
    resp = client.post(
        "/convert", json={"sample_name": "does_not_exist"}, headers={"Authorization": SUBMITTER_AUTH}
    )
    assert resp.status_code == 400


def test_review_unknown_run_id_404(client):
    resp = client.post(
        "/review/nope/approve", json={"note": ""}, headers={"Authorization": REVIEWER_AUTH}
    )
    assert resp.status_code == 404

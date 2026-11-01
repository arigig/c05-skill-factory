import json

import pytest

import app.db as db_module
from app.catalog import PublishError, publish_to_catalog
from app.db import get_connection, start_run, mark_converted, mark_validated, set_review_decision
from mcp_server.server import publish_to_catalog_tool

GENERATED = {
    "pydantic_model": "class M: pass",
    "fastapi_endpoint": "def endpoint(): pass",
    "rule_functions": "def rule(): pass",
    "pytest_tests": "def test_x(): pass",
}


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DEFAULT_DB_PATH", tmp_path / "test.db")
    monkeypatch.chdir(tmp_path)


def _make_approved_run(run_id="11111111-1111-1111-1111-111111111111", form_id="expense_request"):
    conn = get_connection()
    start_run(conn, run_id, form_id, "tests/fixtures/miniform/valid/expense_request.json", "miniform_to_python", "1.0.0", "2026-01-01T00:00:00Z")
    mark_converted(conn, run_id, GENERATED)
    mark_validated(conn, run_id, {"passed": True, "stdout": "ok", "stderr": "", "returncode": 0})
    set_review_decision(conn, run_id, "approved", "reviewer1", "2026-01-01T00:05:00Z")
    return run_id


def test_invalid_run_id_format_rejected():
    with pytest.raises(PublishError, match="invalid run_id format"):
        publish_to_catalog("not-a-uuid")


def test_unknown_run_id_rejected():
    with pytest.raises(PublishError, match="run not found"):
        publish_to_catalog("22222222-2222-2222-2222-222222222222")


def test_unapproved_run_rejected():
    run_id = "33333333-3333-3333-3333-333333333333"
    conn = get_connection()
    start_run(conn, run_id, "expense_request", "tests/fixtures/miniform/valid/expense_request.json", "miniform_to_python", "1.0.0", "2026-01-01T00:00:00Z")
    mark_converted(conn, run_id, GENERATED)
    mark_validated(conn, run_id, {"passed": True, "stdout": "ok", "stderr": "", "returncode": 0})
    # status is 'pending_review', not 'approved'

    with pytest.raises(PublishError, match="not approved"):
        publish_to_catalog(run_id)


def test_rejected_run_cannot_be_published():
    run_id = "44444444-4444-4444-4444-444444444444"
    conn = get_connection()
    start_run(conn, run_id, "expense_request", "tests/fixtures/miniform/valid/expense_request.json", "miniform_to_python", "1.0.0", "2026-01-01T00:00:00Z")
    mark_converted(conn, run_id, GENERATED)
    mark_validated(conn, run_id, {"passed": False, "stdout": "fail", "stderr": "", "returncode": 1})
    set_review_decision(conn, run_id, "rejected", "reviewer1", "2026-01-01T00:05:00Z")

    with pytest.raises(PublishError, match="not approved"):
        publish_to_catalog(run_id)


def test_approved_run_publishes_successfully(tmp_path):
    run_id = _make_approved_run()
    result = publish_to_catalog(run_id, caller="reviewer1", catalog_dir=tmp_path / "catalog")

    dest = tmp_path / "catalog" / "miniform_to_python-1.0.0" / "expense_request" / run_id
    assert result["catalog_path"] == str(dest)
    assert (dest / "pydantic_model.py").read_text() == "class M: pass"
    assert (dest / "test_generated.py").read_text() == "def test_x(): pass"


def test_republishing_same_run_is_rejected(tmp_path):
    run_id = _make_approved_run()
    publish_to_catalog(run_id, catalog_dir=tmp_path / "catalog")

    with pytest.raises(PublishError, match="already published"):
        publish_to_catalog(run_id, catalog_dir=tmp_path / "catalog")


def test_every_call_is_audit_logged(tmp_path):
    run_id = _make_approved_run()
    publish_to_catalog(run_id, caller="reviewer1", catalog_dir=tmp_path / "catalog")
    try:
        publish_to_catalog("bad-id")
    except PublishError:
        pass

    log_path = tmp_path / "ops" / "audit" / "log.jsonl"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in lines]
    assert len(entries) == 2
    assert entries[0]["outcome"] == "success"
    assert entries[0]["caller"] == "reviewer1"
    assert entries[1]["outcome"] == "rejected"


def test_mcp_tool_wraps_errors_instead_of_raising():
    result = publish_to_catalog_tool("not-a-uuid")
    assert "error" in result
    assert "invalid run_id format" in result["error"]


def test_mcp_tool_publishes_successfully():
    # isolated_env already chdir'd into a fresh tmp_path, so the tool's
    # default (cwd-relative) CATALOG_DIR is isolated per test.
    run_id = _make_approved_run()
    result = publish_to_catalog_tool(run_id)
    assert "catalog_path" in result

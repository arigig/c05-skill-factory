import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.main import app, get_anthropic_client

SUBMITTER_AUTH = "Basic " + base64.b64encode(b"submitter:submitter123").decode()
REVIEWER_AUTH = "Basic " + base64.b64encode(b"reviewer:reviewer123").decode()
BAD_AUTH = "Basic " + base64.b64encode(b"nobody:wrong").decode()


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DEFAULT_DB_PATH", tmp_path / "test.db")


@pytest.fixture
def client():
    app.dependency_overrides[get_anthropic_client] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_whoami_requires_auth(client):
    resp = client.get("/whoami")
    assert resp.status_code == 401


def test_whoami_rejects_bad_credentials(client):
    resp = client.get("/whoami", headers={"Authorization": BAD_AUTH})
    assert resp.status_code == 401


def test_whoami_identifies_submitter(client):
    resp = client.get("/whoami", headers={"Authorization": SUBMITTER_AUTH})
    assert resp.status_code == 200
    assert resp.json() == {"username": "submitter", "role": "submitter"}


def test_whoami_identifies_reviewer(client):
    resp = client.get("/whoami", headers={"Authorization": REVIEWER_AUTH})
    assert resp.status_code == 200
    assert resp.json() == {"username": "reviewer", "role": "reviewer"}


def test_convert_requires_auth(client):
    resp = client.post("/convert", json={"sample_name": "expense_request"})
    assert resp.status_code == 401


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_submitter_can_convert_but_not_approve(mock_convert_form, mock_write, mock_sandbox, client):
    mock_convert_form.return_value = {
        "pydantic_model": "x", "fastapi_endpoint": "x", "rule_functions": "x", "pytest_tests": "x"
    }
    mock_sandbox.return_value = {"passed": True, "stdout": "", "stderr": "", "returncode": 0}

    resp = client.post(
        "/convert", json={"sample_name": "expense_request"}, headers={"Authorization": SUBMITTER_AUTH}
    )
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    approve_resp = client.post(
        f"/review/{run_id}/approve", json={"note": ""}, headers={"Authorization": SUBMITTER_AUTH}
    )
    assert approve_resp.status_code == 403


@patch("app.pipeline.run_sandboxed_tests")
@patch("app.pipeline.write_generated_project")
@patch("app.pipeline.convert_form")
def test_reviewer_can_approve_and_identity_is_recorded(mock_convert_form, mock_write, mock_sandbox, client):
    mock_convert_form.return_value = {
        "pydantic_model": "x", "fastapi_endpoint": "x", "rule_functions": "x", "pytest_tests": "x"
    }
    mock_sandbox.return_value = {"passed": True, "stdout": "", "stderr": "", "returncode": 0}

    resp = client.post(
        "/convert", json={"sample_name": "leave_request"}, headers={"Authorization": SUBMITTER_AUTH}
    )
    run_id = resp.json()["run_id"]

    approve_resp = client.post(
        f"/review/{run_id}/approve", json={"note": "looks good"}, headers={"Authorization": REVIEWER_AUTH}
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "approved"
    assert data["reviewer"] == "reviewer"

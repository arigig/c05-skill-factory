from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

from app.auth import Identity, get_current_identity, require_reviewer
from app.catalog import PublishError, publish_to_catalog
from app.db import get_connection, get_run, list_runs, set_review_decision
from app.gateway import GatewayError, build_client
from app.loader import MiniFormLoadError
from app.cost_ledger import BudgetExceededError
from app.pipeline import resume_conversion, run_conversion_pipeline

app = FastAPI(title="C05 Skill Factory")

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Known-safe sample inputs only — never accept an arbitrary file path from a request.
SAMPLE_FORMS = {
    "expense_request": Path("tests/fixtures/miniform/valid/expense_request.json"),
    "leave_request": Path("tests/fixtures/miniform/valid/leave_request.json"),
    "equipment_request": Path("tests/fixtures/miniform/valid/equipment_request.json"),
}


class ConvertRequest(BaseModel):
    sample_name: str


class ReviewRequest(BaseModel):
    note: str = ""


def get_anthropic_client() -> anthropic.Anthropic:
    return build_client()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/whoami")
def whoami(identity: Identity = Depends(get_current_identity)):
    return {"username": identity.username, "role": identity.role}


@app.get("/samples")
def samples(identity: Identity = Depends(get_current_identity)):
    return {"samples": list(SAMPLE_FORMS.keys())}


@app.post("/convert")
def convert(
    payload: ConvertRequest,
    identity: Identity = Depends(get_current_identity),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
):
    sample_path = SAMPLE_FORMS.get(payload.sample_name)
    if sample_path is None:
        raise HTTPException(status_code=400, detail=f"unknown sample_name: {payload.sample_name!r}")
    try:
        return run_conversion_pipeline(client, sample_path)
    except MiniFormLoadError as exc:
        raise HTTPException(status_code=400, detail=f"input rejected: {exc}")
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except GatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/convert/{run_id}/resume")
def convert_resume(
    run_id: str,
    identity: Identity = Depends(get_current_identity),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
):
    try:
        return resume_conversion(client, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except GatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/catalog/publish/{run_id}")
def catalog_publish(run_id: str, identity: Identity = Depends(require_reviewer)):
    try:
        return publish_to_catalog(run_id, caller=identity.username)
    except PublishError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/runs")
def runs(identity: Identity = Depends(get_current_identity)):
    conn = get_connection()
    return list_runs(conn)


@app.get("/runs/{run_id}")
def run_detail(run_id: str, identity: Identity = Depends(get_current_identity)):
    conn = get_connection()
    run = get_run(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.post("/review/{run_id}/approve")
def approve(run_id: str, payload: ReviewRequest, identity: Identity = Depends(require_reviewer)):
    conn = get_connection()
    if get_run(conn, run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    set_review_decision(
        conn, run_id, "approved", identity.username, datetime.now(timezone.utc).isoformat(), payload.note
    )
    return get_run(conn, run_id)


@app.post("/review/{run_id}/reject")
def reject(run_id: str, payload: ReviewRequest, identity: Identity = Depends(require_reviewer)):
    conn = get_connection()
    if get_run(conn, run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    set_review_decision(
        conn, run_id, "rejected", identity.username, datetime.now(timezone.utc).isoformat(), payload.note
    )
    return get_run(conn, run_id)

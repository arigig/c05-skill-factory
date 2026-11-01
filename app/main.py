from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

from app.db import get_connection, get_run, list_runs, set_review_decision
from app.gateway import GatewayError, build_client
from app.loader import MiniFormLoadError
from app.cost_ledger import BudgetExceededError
from app.pipeline import run_conversion_pipeline

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
    reviewer: str
    note: str = ""


def get_anthropic_client() -> anthropic.Anthropic:
    return build_client()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/samples")
def samples():
    return {"samples": list(SAMPLE_FORMS.keys())}


@app.post("/convert")
def convert(payload: ConvertRequest, client: anthropic.Anthropic = Depends(get_anthropic_client)):
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


@app.get("/runs")
def runs():
    conn = get_connection()
    return list_runs(conn)


@app.get("/runs/{run_id}")
def run_detail(run_id: str):
    conn = get_connection()
    run = get_run(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.post("/review/{run_id}/approve")
def approve(run_id: str, payload: ReviewRequest):
    conn = get_connection()
    if get_run(conn, run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    set_review_decision(
        conn, run_id, "approved", payload.reviewer, datetime.now(timezone.utc).isoformat(), payload.note
    )
    return get_run(conn, run_id)


@app.post("/review/{run_id}/reject")
def reject(run_id: str, payload: ReviewRequest):
    conn = get_connection()
    if get_run(conn, run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    set_review_decision(
        conn, run_id, "rejected", payload.reviewer, datetime.now(timezone.utc).isoformat(), payload.note
    )
    return get_run(conn, run_id)

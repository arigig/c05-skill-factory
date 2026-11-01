"""Orchestrates one end-to-end conversion run: load + validate the source
file, record provenance, call the conversion Skill via the gateway, validate
the generated code in the sandbox, and persist the run for reviewer Approve/
Reject. Nothing here writes to a catalog or pushes to Git — only a human
reviewer decision (app.db.set_review_decision) changes a run's status.
"""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import anthropic

from app.db import create_run, get_connection
from app.loader import MiniFormLoadError, load_miniform_file
from app.provenance import record_provenance
from app.sandbox import run_sandboxed_tests, write_generated_project
from app.skills.conversion import convert_form

GENERATED_RUNS_DIR = Path("ops/generated_runs")


def run_conversion_pipeline(
    client: anthropic.Anthropic,
    miniform_path: Path,
    workdir: Path = GENERATED_RUNS_DIR,
) -> dict:
    source_miniform_json = Path(miniform_path).read_text(encoding="utf-8")
    try:
        canonical = load_miniform_file(miniform_path)
    except MiniFormLoadError as exc:
        record_provenance(miniform_path, "rejected", detail=str(exc))
        raise
    record_provenance(miniform_path, "accepted")

    generated = convert_form(client, canonical, purpose=f"convert:{canonical.form_id}")

    run_id = str(uuid4())
    output_dir = Path(workdir) / run_id
    write_generated_project(output_dir, generated)
    sandbox_result = run_sandboxed_tests(output_dir)

    conn = get_connection()
    create_run(
        conn,
        run_id=run_id,
        form_id=canonical.form_id,
        generated_code=generated,
        sandbox_result=sandbox_result,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "run_id": run_id,
        "form_id": canonical.form_id,
        "sandbox_passed": sandbox_result["passed"],
        "sandbox_stdout": sandbox_result["stdout"],
        "generated_code": generated,
        "source_miniform_json": source_miniform_json,
        "source_canonical_form": canonical.model_dump(),
    }

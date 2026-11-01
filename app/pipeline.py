"""Orchestrates one end-to-end conversion run as a sequence of checkpoints:
load+validate -> convert (paid API call) -> sandbox-validate. Each checkpoint
is persisted as soon as it completes (app/db.py), so resume_conversion() can
pick up after a crash without redoing — and re-paying for — a step that
already succeeded. Nothing here writes to a catalog or pushes to Git — only
a human reviewer decision (app.db.set_review_decision) changes a run's
final status.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import anthropic

from app.db import get_connection, get_run, mark_converted, mark_validated, start_run
from app.loader import MiniFormLoadError, load_miniform_file
from app.provenance import record_provenance
from app.sandbox import run_sandboxed_tests, write_generated_project
from app.skills.conversion import convert_form, get_skill_identity

GENERATED_RUNS_DIR = Path("ops/generated_runs")


def run_conversion_pipeline(
    client: anthropic.Anthropic,
    miniform_path: Path,
    workdir: Path = GENERATED_RUNS_DIR,
) -> dict:
    try:
        canonical = load_miniform_file(miniform_path)
    except MiniFormLoadError as exc:
        record_provenance(miniform_path, "rejected", detail=str(exc))
        raise
    record_provenance(miniform_path, "accepted")

    run_id = str(uuid4())
    skill_name, skill_version = get_skill_identity()
    conn = get_connection()
    start_run(
        conn,
        run_id=run_id,
        form_id=canonical.form_id,
        source_miniform_path=str(miniform_path),
        skill_name=skill_name,
        skill_version=skill_version,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return resume_conversion(client, run_id, workdir)


def resume_conversion(
    client: anthropic.Anthropic,
    run_id: str,
    workdir: Path = GENERATED_RUNS_DIR,
) -> dict:
    conn = get_connection()
    run = get_run(conn, run_id)
    if run is None:
        raise ValueError(f"no such run: {run_id}")

    canonical = load_miniform_file(run["source_miniform_path"])

    if run["generated_code"] is None:
        generated = convert_form(client, canonical, purpose=f"convert:{canonical.form_id}")
        mark_converted(conn, run_id, generated)
    else:
        generated = json.loads(run["generated_code"])

    if run["sandbox_output"] is None:
        output_dir = Path(workdir) / run_id
        write_generated_project(output_dir, generated)
        sandbox_result = run_sandboxed_tests(output_dir)
        mark_validated(conn, run_id, sandbox_result)
    else:
        sandbox_result = json.loads(run["sandbox_output"])

    source_miniform_json = Path(run["source_miniform_path"]).read_text(encoding="utf-8")

    return {
        "run_id": run_id,
        "form_id": canonical.form_id,
        "sandbox_passed": sandbox_result["passed"],
        "sandbox_stdout": sandbox_result["stdout"],
        "generated_code": generated,
        "source_miniform_json": source_miniform_json,
        "source_canonical_form": canonical.model_dump(),
    }

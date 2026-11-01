"""The one governed, deterministic enterprise-style tool for this project:
publishing an approved conversion run's generated code into the reusable
catalog. Exposed via the local MCP server (mcp_server/server.py) and,
for the HTML page, a plain HTTP endpoint — both call this same function.

Least privilege: this function can only read the conversion_runs table and
write new files under CATALOG_DIR. It never deletes, never overwrites an
existing catalog entry, and never accepts a filesystem path from the caller
(the destination path is derived entirely from already-validated DB fields).
Approval-before-write: publishing is refused unless the run's reviewer
status is 'approved'. Every call, successful or rejected, is audit-logged.
"""
import json
from pathlib import Path
from uuid import UUID

from app.audit import record_tool_call
from app.db import get_connection, get_run

CATALOG_DIR = Path("ops/catalog")


class PublishError(Exception):
    """Raised when a run cannot be published to the catalog."""


def _reject(caller: str, run_id: str, detail: str) -> None:
    record_tool_call("publish_to_catalog", caller, {"run_id": run_id}, "rejected", detail)
    raise PublishError(detail)


def publish_to_catalog(run_id: str, caller: str = "unknown", catalog_dir: Path = CATALOG_DIR) -> dict:
    try:
        UUID(str(run_id))
    except (ValueError, AttributeError, TypeError):
        _reject(caller, str(run_id), f"invalid run_id format: {run_id!r}")

    conn = get_connection()
    run = get_run(conn, run_id)
    if run is None:
        _reject(caller, run_id, f"run not found: {run_id}")

    if run["status"] != "approved":
        _reject(caller, run_id, f"run {run_id} is not approved (status={run['status']!r}); cannot publish")

    skill_name = run["skill_name"] or "unknown-skill"
    skill_version = run["skill_version"] or "0.0.0"
    dest = Path(catalog_dir) / f"{skill_name}-{skill_version}" / run["form_id"] / run_id

    if dest.exists():
        _reject(caller, run_id, f"run {run_id} is already published at {dest}")

    generated = json.loads(run["generated_code"])
    dest.mkdir(parents=True, exist_ok=False)
    (dest / "pydantic_model.py").write_text(generated["pydantic_model"], encoding="utf-8")
    (dest / "rule_functions.py").write_text(generated["rule_functions"], encoding="utf-8")
    (dest / "fastapi_endpoint.py").write_text(generated["fastapi_endpoint"], encoding="utf-8")
    (dest / "test_generated.py").write_text(generated["pytest_tests"], encoding="utf-8")

    result = {"run_id": run_id, "catalog_path": str(dest)}
    record_tool_call("publish_to_catalog", caller, {"run_id": run_id}, "success", str(dest))
    return result

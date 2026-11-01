"""Audit log for governed tool calls (Enterprise Tools / MCP layer). Every
call — success or rejection — is recorded. Separate from app/provenance.py,
which logs lineage of source *files*, not tool invocations.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_AUDIT_LOG_PATH = Path("ops/audit/log.jsonl")


def record_tool_call(
    tool_name: str,
    caller: str,
    arguments: dict,
    outcome: str,
    detail: str = "",
    log_path: Path = DEFAULT_AUDIT_LOG_PATH,
) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "caller": caller,
        "arguments": arguments,
        "outcome": outcome,
        "detail": detail,
    }
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

"""Records lineage for every source file the factory processes: where it came
from, its content hash, when it was processed, and whether it was accepted or
rejected.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path("ops/provenance/log.jsonl")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record_provenance(
    source_path: Path,
    outcome: str,
    detail: str = "",
    log_path: Path = DEFAULT_LOG_PATH,
) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": str(source_path),
        "sha256": _sha256(source_path),
        "outcome": outcome,
        "detail": detail,
    }
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

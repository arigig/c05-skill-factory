"""SQLite-backed storage for conversion runs, checkpoints and reviewer
decisions. A run moves through stages: 'loaded' -> 'converted' ->
'validated'. Each stage's data is persisted as soon as it completes, so
resume_conversion() (app/pipeline.py) can pick up after a crash without
redoing — and re-paying for — a step that already succeeded.
"""
import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("ops/app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversion_runs (
    run_id TEXT PRIMARY KEY,
    form_id TEXT NOT NULL,
    source_miniform_path TEXT NOT NULL,
    skill_name TEXT,
    skill_version TEXT,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    sandbox_passed INTEGER,
    generated_code TEXT,
    sandbox_output TEXT,
    reviewer TEXT,
    reviewer_note TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);
"""

# Columns added after the original schema; added defensively via ALTER TABLE
# so an existing ops/app.db from an earlier iteration keeps working.
MIGRATION_COLUMNS = [
    ("source_miniform_path", "TEXT NOT NULL DEFAULT ''"),
    ("skill_name", "TEXT"),
    ("skill_version", "TEXT"),
    ("stage", "TEXT NOT NULL DEFAULT 'validated'"),
]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    for column, definition in MIGRATION_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE conversion_runs ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    return conn


def start_run(
    conn: sqlite3.Connection,
    run_id: str,
    form_id: str,
    source_miniform_path: str,
    skill_name: str,
    skill_version: str,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO conversion_runs
            (run_id, form_id, source_miniform_path, skill_name, skill_version,
             stage, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'loaded', 'in_progress', ?)
        """,
        (run_id, form_id, source_miniform_path, skill_name, skill_version, created_at),
    )
    conn.commit()


def mark_converted(conn: sqlite3.Connection, run_id: str, generated_code: dict) -> None:
    conn.execute(
        "UPDATE conversion_runs SET stage = 'converted', generated_code = ? WHERE run_id = ?",
        (json.dumps(generated_code), run_id),
    )
    conn.commit()


def mark_validated(conn: sqlite3.Connection, run_id: str, sandbox_result: dict) -> None:
    conn.execute(
        """
        UPDATE conversion_runs
        SET stage = 'validated', status = 'pending_review',
            sandbox_passed = ?, sandbox_output = ?
        WHERE run_id = ?
        """,
        (int(sandbox_result["passed"]), json.dumps(sandbox_result), run_id),
    )
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM conversion_runs WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def set_review_decision(
    conn: sqlite3.Connection,
    run_id: str,
    decision: str,
    reviewer: str,
    decided_at: str,
    note: str = "",
) -> None:
    if decision not in ("approved", "rejected"):
        raise ValueError(f"invalid decision: {decision!r}")
    conn.execute(
        """
        UPDATE conversion_runs
        SET status = ?, reviewer = ?, reviewer_note = ?, decided_at = ?
        WHERE run_id = ?
        """,
        (decision, reviewer, note, decided_at, run_id),
    )
    conn.commit()


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM conversion_runs ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]

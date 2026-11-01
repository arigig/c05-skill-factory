"""SQLite-backed storage for conversion runs and reviewer decisions."""
import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("ops/app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversion_runs (
    run_id TEXT PRIMARY KEY,
    form_id TEXT NOT NULL,
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


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def create_run(
    conn: sqlite3.Connection,
    run_id: str,
    form_id: str,
    generated_code: dict,
    sandbox_result: dict,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO conversion_runs
            (run_id, form_id, status, sandbox_passed, generated_code, sandbox_output, created_at)
        VALUES (?, ?, 'pending_review', ?, ?, ?, ?)
        """,
        (
            run_id,
            form_id,
            int(sandbox_result["passed"]),
            json.dumps(generated_code),
            json.dumps(sandbox_result),
            created_at,
        ),
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

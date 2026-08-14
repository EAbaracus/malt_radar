"""KEP Autonomous Runtime — Audit Writer.

Read-only writable audit layer for review actions, scheduler runs, job history,
and failure records. In Phase 1 operates on a separate runtime database (read-only
mode for production), ready for Phase 2+ production integration.

Schema matches P325 §6 and P326 §5 design contracts.
"""

import json
import datetime
import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS review_actions (
    action_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id      TEXT NOT NULL,
    whisky_id        TEXT,
    queue_type       TEXT NOT NULL,
    action_type      TEXT NOT NULL,
    from_state       TEXT,
    to_state         TEXT,
    reviewer         TEXT,
    justification    TEXT,
    auto_rule        TEXT,
    auto_score       REAL,
    human_interface  TEXT,
    review_duration  INTEGER,
    promotion_id     TEXT,
    rollback_ref     TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_run_log (
    run_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_start         TEXT NOT NULL,
    run_end           TEXT,
    cycle_type        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'RUNNING',
    jobs_executed     TEXT NOT NULL DEFAULT '[]',
    candidates_found  INTEGER DEFAULT 0,
    actions_executed  INTEGER DEFAULT 0,
    actions_failed    INTEGER DEFAULT 0,
    errors            TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_job_history (
    job_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL,
    job_name          TEXT NOT NULL,
    job_start         TEXT NOT NULL,
    job_end           TEXT,
    status            TEXT NOT NULL DEFAULT 'RUNNING',
    items_processed   INTEGER DEFAULT 0,
    items_failed      INTEGER DEFAULT 0,
    duration_ms       INTEGER,
    error_message     TEXT,
    metadata_json     TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_failure_log (
    failure_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER,
    job_id            INTEGER,
    failure_type      TEXT NOT NULL,
    evidence_id       TEXT,
    action_type       TEXT,
    error_message     TEXT NOT NULL,
    traceback         TEXT,
    retry_count       INTEGER DEFAULT 0,
    resolved          INTEGER DEFAULT 0,
    resolved_at       TEXT,
    created_at        TEXT NOT NULL
);
"""


class AuditWriter:
    """Read-only writable audit logger for review queues and scheduler.

    In Phase 1 all writes go to an independent runtime database so that
    the production or staging databases are NEVER touched.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialise audit database.

        Args:
            db_path: Path to the audit SQLite file.
                      Defaults to <runtime_root>/runtime/runtime.db
        """
        if db_path is None:
            db_path = str(
                Path(__file__).resolve().parent / "runtime.db"
            )
        self.db_path = db_path
        self._ensure_schema()

    # ── Schema ──────────────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self) -> None:
        """Create the 4 audit tables if they do not exist."""
        conn = self._get_connection()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def table_exists(self) -> dict[str, bool]:
        """Return which audit tables exist.  Used in tests."""
        conn = self._get_connection()
        names = {
            "review_actions", "scheduler_run_log",
            "scheduler_job_history", "scheduler_failure_log",
        }
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        existing = {r[0] for r in cur.fetchall()}
        conn.close()
        return {n: n in existing for n in sorted(names)}

    # ── Logging methods ─────────────────────────────────────────────

    def log_review_action(
        self,
        evidence_id: str,
        whisky_id: Optional[str] = None,
        queue_type: str = "automatic",
        action_type: str = "",
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        reviewer: Optional[str] = None,
        justification: Optional[str] = None,
        auto_rule: Optional[str] = None,
        auto_score: Optional[float] = None,
        promotion_id: Optional[str] = None,
    ) -> int:
        """Log one queue transition. Returns action_id."""
        now = datetime.datetime.utcnow().isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO review_actions
                   (evidence_id, whisky_id, queue_type, action_type,
                    from_state, to_state, reviewer, justification,
                    auto_rule, auto_score, promotion_id, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    evidence_id, whisky_id, queue_type, action_type,
                    from_state, to_state, reviewer, justification,
                    auto_rule, auto_score, promotion_id, now,
                ),
            )
            conn.commit()
            rid = cur.lastrowid or 0
            return rid
        finally:
            conn.close()

    def log_scheduler_run(
        self,
        run_start: str,
        cycle_type: str = "unknown",
        status: str = "RUNNING",
    ) -> int:
        """Start or record a scheduler run. Returns run_id."""
        now = datetime.datetime.utcnow().isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO scheduler_run_log
                   (run_start, cycle_type, status, created_at)
                   VALUES (?,?,?,?)""",
                (run_start, cycle_type, status, now),
            )
            conn.commit()
            rid = cur.lastrowid or 0
            return rid
        finally:
            conn.close()

    def complete_scheduler_run(
        self,
        run_id: int,
        status: str = "SUCCESS",
        candidates_found: int = 0,
        actions_executed: int = 0,
        actions_failed: int = 0,
        errors: Optional[str] = None,
    ) -> None:
        """Mark a scheduler run as completed."""
        now = datetime.datetime.utcnow().isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """UPDATE scheduler_run_log
                   SET run_end=?, status=?, candidates_found=?,
                       actions_executed=?, actions_failed=?, errors=?
                   WHERE run_id=?""",
                (now, status, candidates_found,
                 actions_executed, actions_failed, errors, run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def log_job(
        self,
        run_id: int,
        job_name: str,
        status: str = "RUNNING",
        items_processed: int = 0,
        items_failed: int = 0,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Log a job execution. Returns job_id."""
        now = datetime.datetime.utcnow().isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO scheduler_job_history
                   (run_id, job_name, job_start, status,
                    items_processed, items_failed, duration_ms,
                    error_message, metadata_json, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id, job_name, now, status,
                    items_processed, items_failed, duration_ms,
                    error_message,
                    json.dumps(metadata) if metadata else None,
                    now,
                ),
            )
            conn.commit()
            rid = cur.lastrowid or 0
            return rid
        finally:
            conn.close()

    def log_failure(
        self,
        failure_type: str,
        error_message: str,
        run_id: Optional[int] = None,
        job_id: Optional[int] = None,
        evidence_id: Optional[str] = None,
        action_type: Optional[str] = None,
        traceback: Optional[str] = None,
    ) -> int:
        """Log a failure record. Returns failure_id."""
        now = datetime.datetime.utcnow().isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO scheduler_failure_log
                   (run_id, job_id, failure_type, evidence_id,
                    action_type, error_message, traceback, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    run_id, job_id, failure_type, evidence_id,
                    action_type, error_message, traceback, now,
                ),
            )
            conn.commit()
            rid = cur.lastrowid or 0
            return rid
        finally:
            conn.close()

    # ── Queries ─────────────────────────────────────────────────────

    def get_recent_actions(
        self, evidence_id: str, limit: int = 20
    ) -> list[dict]:
        """Get action history for a candidate."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """SELECT * FROM review_actions
                   WHERE evidence_id=? ORDER BY created_at DESC LIMIT ?""",
                (evidence_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get_last_run(self) -> Optional[dict]:
        """Get the most recent scheduler run."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM scheduler_run_log ORDER BY run_id DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

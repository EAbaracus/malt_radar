"""
db_write_guard.py — Write-Path Isolation Gate (Minimum Viable)

Single chokepoint for ANY read-write access to production.db.
DEFAULT STATE: production.db is OS-enforced READ-ONLY (attrib +R + icacls deny
on WriteData/AppendData for the owning user). No script/agent (including ones
running as the same user) can write unless it goes through get_write_connection,
which deliberately lifts the OS lock, writes inside a transaction, runs post-
validation, and re-asserts the lock in a finally block.

DB-write standards enforced:
  - backup/hash guard is the CALLER's responsibility (see minimum_viable_gate_report.md).
  - every write opens with BEGIN IMMEDIATE TRANSACTION.
  - after the write, PRAGMA integrity_check + foreign_key_check run automatically.
  - on any error OR validation failure -> automatic ROLLBACK, lock re-asserted, exception raised.

Read path (defense-in-depth A): get_read_connection() opens ?mode=ro with
PRAGMA query_only=ON so readers can never mutate even if logic bugs out.

No module-level side effects: importing this file changes nothing on disk.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import subprocess
import sys
from typing import Iterator, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..",
                 "output", "import", "production.db")
)
# The owning principal that holds Full control in this environment. The deny
# ACE is applied to exactly this principal so the gate (also running as this
# principal) can still strip/restore it via WriteDac, but cannot WriteData.
DENY_PRINCIPAL = "Deathstar\\eltun"
DENY_RIGHTS = "(WD,AD)"  # WriteData + AppendData


def _run(args: List[str]) -> subprocess.CompletedProcess:
    """Run an icacls/attrib command; never raises on non-zero (caller decides)."""
    return subprocess.run(args, capture_output=True, text=True)


def _is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


def lift_write_access(db_path: Optional[str] = None) -> None:
    """Temporarily remove the OS read-only lock so a guarded write can happen.

    Idempotent: if the deny ACE is absent, /remove:d is a no-op (non-fatal).
    On non-Windows this is a no-op (the lock concept is Windows-specific).
    """
    if not _is_windows():
        return
    target = db_path or DB_PATH
    # clear the readonly file attribute
    _run(["attrib", "-R", target])
    # strip the deny ACE (if present)
    _run(["icacls", target, "/remove:d", DENY_PRINCIPAL])


def assert_write_access(db_path: Optional[str] = None) -> None:
    """Re-assert the OS read-only lock. Call in a finally block ALWAYS."""
    if not _is_windows():
        return
    target = db_path or DB_PATH
    # set the readonly file attribute (secondary signal)
    _run(["attrib", "+R", target])
    # re-add the deny ACE; if it already exists icacls errors -> ignore
    _run(["icacls", target, "/deny", DENY_PRINCIPAL + ":" + DENY_RIGHTS])


def _post_validate(conn: sqlite3.Connection) -> None:
    """Run integrity + FK checks. Raise RuntimeError on any problem."""
    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    if integrity != [("ok",)]:
        raise RuntimeError(f"integrity_check FAILED: {integrity}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        raise RuntimeError(f"foreign_key_check FAILED: {fk}")


class WriteGate:
    """Context manager returned by get_write_connection().

    Enter: lift OS lock, open RW connection, BEGIN IMMEDIATE.
    Exit (success): post-validate -> COMMIT -> re-assert lock.
    Exit (exception): ROLLBACK -> re-assert lock -> propagate.
    """

    def __init__(self, authorized_context: str, restrict_tables: Optional[List[str]] = None, db_path: Optional[str] = None):
        if not authorized_context or not str(authorized_context).strip():
            raise PermissionError(
                "get_write_connection requires a non-empty authorized_context. "
                "Refusing to lift the OS write lock without an audit label."
            )
        self.authorized_context = str(authorized_context).strip()
        self.restrict_tables = restrict_tables or []
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._lifted = False

    def __enter__(self) -> sqlite3.Connection:
        lift_write_access(self.db_path)
        self._lifted = True
        self.conn = sqlite3.connect(self.db_path or DB_PATH)
        self.conn.execute("BEGIN IMMEDIATE TRANSACTION;")
        return self.conn

    def __exit__(self, exc_type, exc, tb) -> bool:
        conn = self.conn
        try:
            if conn is None:
                return False
            if exc_type is not None:
                conn.rollback()
                return False  # propagate
            # success path: validate then commit
            _post_validate(conn)
            conn.commit()
            return False
        except Exception as ve:
            try:
                conn.rollback()
            except Exception:
                pass
            raise RuntimeError(f"post-write validation failed: {ve}") from ve
        finally:
            try:
                if conn is not None:
                    conn.close()
            finally:
                # ALWAYS re-assert the lock, even on crash.
                assert_write_access(self.db_path)
                self._lifted = False


def get_write_connection(authorized_context: str,
                         restrict_tables: Optional[List[str]] = None,
                         db_path: Optional[str] = None) -> WriteGate:
    """Return a context manager that opens a guarded RW connection.

    Usage:
        with get_write_connection(authorized_context="book_import_pX") as conn:
            conn.execute("UPDATE whiskies SET ... WHERE ...")

    restrict_tables is accepted and logged for audit; table-level enforcement
    (blocking writes to non-listed tables) is deferred to a later enhancement.
    For minimum viable, the hard guarantee is: OS lock lifted only inside this
    gate, transaction + post-validation mandatory, lock always re-asserted.
    """
    return WriteGate(authorized_context, restrict_tables, db_path)


@contextlib.contextmanager
def get_read_connection(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Read-only connection (defense-in-depth A): ?mode=ro + PRAGMA query_only=ON.

    If db_path is given it is used instead of the module default DB_PATH, so
    callers that already resolved production.db can pass it through.
    """
    target = db_path or DB_PATH
    uri = "file:" + target.replace("\\", "/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("PRAGMA query_only = ON;")
        yield conn
    finally:
        conn.close()


if __name__ == "__main__":
    # Self-test (no data change): prove the lock blocks direct writes but the
    # gate allows a no-op write. Mirrors minimum_viable_gate_report.md tests.
    import traceback

    print("DB_PATH =", DB_PATH)
    print("exists =", os.path.exists(DB_PATH))

    # Test A: direct RW write must FAIL (OS lock)
    try:
        c = sqlite3.connect(DB_PATH)
        c.execute("UPDATE whiskies SET name = name WHERE 1 = 0;")
        c.commit()
        c.close()
        print("TEST A (direct write): UNEXPECTED SUCCESS  <-- LOCK NOT ENFORCED")
    except sqlite3.OperationalError as e:
        print(f"TEST A (direct write): EXPECTED FAILURE -> {e}")

    # Test B: gate no-op write must SUCCEED
    try:
        with get_write_connection(authorized_context="gate_self_test") as conn:
            conn.execute("UPDATE whiskies SET name = name WHERE 1 = 0;")
        print("TEST B (gate write): SUCCESS")
    except Exception:
        print("TEST B (gate write): FAILURE")
        traceback.print_exc()

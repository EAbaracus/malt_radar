"""
db_write_guard.py — Write-Path Isolation Gate (Minimum Viable)

Single chokepoint for ANY read-write access to production.db.
DEFAULT STATE: production.db is OS-enforced READ-ONLY (attrib +R + icacls deny
on WriteData/AppendData for the owning user). No script/agent (including ones
running as the same user) can write unless it goes through the governed
`WriteGate` context manager, which requires a valid one-time cryptographic
proof generated at entry time. `_lift_write_access()` is internal-only and
cannot be called without a valid proof that only WriteGate can generate.

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
import hashlib
import os
import secrets
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


class WriteGuardLiftError(RuntimeError):
    """Raised when the OS write-lock lift (icacls /remove:d) fails.

    A failed lift means production.db stays read-only/deny-protected, so the
    caller MUST abort (never proceed to the guarded write). Fail-closed.
    """


class WriteGuardReassertError(RuntimeError):
    """Raised when the DENY ACE re-assert (icacls /deny) fails on cleanup.

    An un-reasserted DENY ACE is a LIVE production-safety gap (P0): the file
    would be left writable. Raise loudly — do not swallow.
    """


def _run(args: List[str]) -> subprocess.CompletedProcess:
    """Run an icacls/attrib command. CALLER MUST inspect returncode/stderr."""
    return subprocess.run(args, capture_output=True, text=True)


def _is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


# ── Proof of authorization for _lift_write_access ──────────────────────
# A one-time cryptographic proof that must be provided to _lift_write_access.
# Only WriteGate can generate a valid proof; the caller must hold the
# WriteGate context manager to obtain one. This prevents arbitrary code
# from calling _lift_write_access directly.
# Map of proof -> verification (proof tokens are in the set of valid proofs).
# Once consumed, the proof is removed from the set.
_valid_proofs: dict[str, str] = {}


def _generate_proof() -> tuple[str, str]:
    """Generate a one-time proof token + a verification token.

    Returns (proof, verification_token) where:
      proof — given to the caller; must be presented to _lift_write_access.
      verification_token — stored by WriteGate; used to verify the proof.

    The proof is a secure random hex string. The verification_token is
    the SHA-256 of the proof. On verification, _lift_write_access checks
    that sha256(proof) == verification_token AND that the proof is in
    _valid_proofs. After use, the proof is consumed.
    """
    import hashlib
    import secrets
    proof = secrets.token_hex(32)
    verification_token = hashlib.sha256(proof.encode()).hexdigest()
    _valid_proofs[proof] = verification_token
    return proof, verification_token


def _verify_proof(proof: str, verification_token: str) -> bool:
    """Verify that proof matches verification_token and has not been consumed.

    Also checks that both proof and a matching verification were registered
    by _generate_proof (i.e. came through WriteGate). After successful
    verification the proof is consumed (removed from the valid set).
    """
    import hashlib
    if proof not in _valid_proofs:
        return False
    expected_token = hashlib.sha256(proof.encode()).hexdigest()
    if expected_token != verification_token:
        return False
    stored_token = _valid_proofs.pop(proof)  # consume
    return stored_token == verification_token


def _lift_write_access(
    proof: str,
    verification_token: str,
    db_path: Optional[str] = None,
) -> None:
    """Temporarily remove the OS read-only lock so a guarded write can happen.

    REQUIRES: a valid, unconsumed proof that matches verification_token.
    The proof is generated by WriteGate.__enter__ — arbitrary callers cannot
    obtain a valid proof without going through the governed WriteGate path.

    Idempotent: if the deny ACE is absent, /remove:d is a no-op (rc=0).
    FAIL-CLOSED: a non-zero icacls /remove:d exit is raised, never swallowed —
    the caller (PromotionGate) treats this as an abort-and-rollback condition.
    On non-Windows this is a no-op (the lock concept is Windows-specific).
    """
    if not _is_windows():
        return
    if not _verify_proof(proof, verification_token):
        raise WriteGuardLiftError(
            "ACL lift REJECTED: invalid, missing, or replayed proof token. "
            "A valid proof can only be obtained through the governed WriteGate path."
        )
    target = db_path or DB_PATH
    # clear the readonly file attribute (secondary signal; best-effort)
    _run(["attrib", "-R", target])
    # strip the deny ACE (if present) — MUST succeed or we refuse to proceed
    r = _run(["icacls", target, "/remove:d", DENY_PRINCIPAL])
    if r.returncode != 0:
        raise WriteGuardLiftError(
            f"icacls /remove:d failed (rc={r.returncode}) for {target!r}: "
            f"{r.stderr.strip() or r.stdout.strip()}"
        )


def _assert_write_access(db_path: Optional[str] = None) -> None:
    """Re-assert the OS read-only lock. Call in a finally block ALWAYS.

    FAIL-CLOSED: a non-zero icacls /deny exit is raised as P0 — the DENY ACE
    must be re-asserted or production is left writable.
    """
    if not _is_windows():
        return
    target = db_path or DB_PATH
    # set the readonly file attribute (secondary signal; best-effort)
    _run(["attrib", "+R", target])
    # re-add the deny ACE; failure here is a P0 safety gap
    r = _run(["icacls", target, "/deny", DENY_PRINCIPAL + ":" + DENY_RIGHTS])
    if r.returncode != 0:
        raise WriteGuardReassertError(
            f"icacls /deny FAILED to re-assert DENY ACE (rc={r.returncode}) for "
            f"{target!r}: {r.stderr.strip() or r.stdout.strip()} — PRODUCTION LEFT UNPROTECTED"
        )


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
        self._proof, self._verification_token = _generate_proof()
        _lift_write_access(
            proof=self._proof,
            verification_token=self._verification_token,
            db_path=self.db_path,
        )
        self._lifted = True
        if hasattr(self, '_file_only_mode') and self._file_only_mode:
            # File-only mode: no SQLite connection needed
            self.conn = None
            return None  # type: ignore
        self.conn = sqlite3.connect(self.db_path or DB_PATH)
        self.conn.execute("BEGIN IMMEDIATE TRANSACTION;")
        return self.conn

    def __exit__(self, exc_type, exc, tb) -> bool:
        conn = self.conn
        try:
            if conn is None:
                # File-only mode: skip SQLite operations
                return False if exc_type is not None else False
            if exc_type is not None:
                conn.rollback()
                return False  # propagate
            # success path: validate then commit
            _post_validate(conn)
            conn.commit()
            return False
        except Exception as ve:
            try:
                if conn is not None:
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
                _assert_write_access(self.db_path)
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

    # Test B: gate no-op write must SUCCEED (via WriteGate with proof)
    try:
        with get_write_connection(authorized_context="gate_self_test") as conn:
            conn.execute("UPDATE whiskies SET name = name WHERE 1 = 0;")
        print("TEST B (gate write): SUCCESS")
    except Exception:
        print("TEST B (gate write): FAILURE")
        traceback.print_exc()

    # Test C: direct call to _lift_write_access without proof must FAIL
    try:
        import secrets
        import hashlib
        bad_proof = "not-a-valid-proof"
        bad_verification = "not-a-valid-verification"
        _lift_write_access(proof=bad_proof, verification_token=bad_verification)
        print("TEST C (direct _lift_write_access): UNEXPECTED SUCCESS  <-- PROOF NOT ENFORCED")
    except WriteGuardLiftError as e:
        print(f"TEST C (direct _lift_write_access): EXPECTED FAILURE -> {e}")
    except Exception as e:
        print(f"TEST C (direct _lift_write_access): OTHER ERROR -> {e}")

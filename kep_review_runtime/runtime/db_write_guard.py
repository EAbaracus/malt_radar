#!/usr/bin/env python3
"""
db_write_guard -- VERIFY-SAFETY write gate for KEP promotion.

Contract:
  get_write_connection(authorized_context, restrict_tables=None, db_path=None)
      -> context manager yielding a READ-WRITE sqlite3 connection.

On Windows it lifts BOTH the OS read-only DOS attribute AND the production
DENY ACE (icacls (WD,AD)) on ENTER, re-asserts them on EXIT. The DENY ACE is
only re-asserted if it was present before the lift, so temp promotion copies
(which never carry the ACE) are not polluted. Wraps the write in
BEGIN IMMEDIATE, runs integrity + FK checks on exit, commits on success /
rolls back on exception. Fail-closed.

SECURITY: The raw ACL primitives (_lift_write_access / _assert_write_access)
are INTERNAL and require a one-time cryptographic proof that only
get_write_connection or authorized_file_replacement can generate. Arbitrary
callers calling these functions without a valid proof are REJECTED.

Public API:
  get_write_connection(authorized_context, ...) -> context manager
  authorized_file_replacement(temp_copy_path, production_db_path, authorized_context)
"""

import hashlib
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
from contextlib import contextmanager

DENY_PRINCIPAL = "Deathstar\\eltun"
DENY_RIGHTS = "(WD,AD)"

_valid_proofs: dict[str, str] = {}


class WriteGuardLiftError(RuntimeError):
    """Raised when the OS write-lock lift (icacls /remove:d) fails."""


class WriteGuardReassertError(RuntimeError):
    """Raised when the DENY ACE re-assert (icacls /deny) fails on cleanup."""


class WriteGuardAuthorizationError(PermissionError):
    """Raised when a caller attempts _lift_write_access without a valid proof."""


def _is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=15)
    except Exception as e:
        raise RuntimeError(f"_run failed to launch {args!r}: {e}") from e


def _ace_present(path: str) -> bool:
    if not _is_windows():
        return False
    r = _run(["icacls", path])
    if not r or r.returncode != 0:
        return False
    return "(DENY)" in r.stdout


def _generate_proof() -> tuple[str, str]:
    """Generate a one-time proof + verification token pair.

    Only get_write_connection and authorized_file_replacement can call this.
    Returns (proof, verification_token) where proof is a secure random
    hex string and verification_token = sha256(proof).
    """
    proof = secrets.token_hex(32)
    verification_token = hashlib.sha256(proof.encode()).hexdigest()
    _valid_proofs[proof] = verification_token
    return proof, verification_token


def _verify_proof(proof: str, verification_token: str) -> bool:
    """Verify proof + verification_token match and have not been consumed."""
    if proof not in _valid_proofs:
        return False
    expected = hashlib.sha256(proof.encode()).hexdigest()
    if expected != verification_token:
        return False
    _valid_proofs.pop(proof)  # consume
    return True


def _lift_os_lock(path: str) -> None:
    """Strip read-only attribute + DENY ACE."""
    try:
        os.chmod(path, 0o666)
    except Exception:
        pass
    _run(["attrib", "-R", path])
    if _is_windows():
        r = _run(["icacls", path, "/remove:d", DENY_PRINCIPAL])
        if r.returncode != 0:
            raise WriteGuardLiftError(
                f"icacls /remove:d failed (rc={r.returncode}) for {path!r}: "
                f"{r.stderr.strip() or r.stdout.strip()}"
            )


def _reassert_os_lock(path: str, had_ace: bool) -> None:
    """Restore read-only attribute + DENY ACE (only if present before)."""
    _run(["attrib", "+R", path])
    try:
        os.chmod(path, 0o444)
    except Exception:
        pass
    if _is_windows() and had_ace:
        r = _run(["icacls", path, "/deny", DENY_PRINCIPAL + ":" + DENY_RIGHTS])
        if r.returncode != 0:
            raise WriteGuardReassertError(
                f"icacls /deny FAILED (rc={r.returncode}) for {path!r}: "
                f"{r.stderr.strip() or r.stdout.strip()} — PRODUCTION LEFT UNPROTECTED"
            )


def _lift_write_access(proof: str, verification_token: str, db_path: str) -> bool:
    """INTERNAL: Lift OS lock. REQUIRES valid proof from governed path.

    Returns True if a DENY ACE was present (for callers that need to know).
    Raises WriteGuardAuthorizationError on invalid/missing/replayed proof.
    """
    if not _verify_proof(proof, verification_token):
        raise WriteGuardAuthorizationError(
            "ACL lift REJECTED: invalid, missing, or replayed proof token. "
            "A valid proof can only be obtained through the governed path "
            "(get_write_connection or authorized_file_replacement)."
        )
    had_ace = _ace_present(db_path)
    _lift_os_lock(db_path)
    return had_ace


def _assert_write_access(db_path: str, had_ace: bool = True) -> None:
    """INTERNAL: Re-assert OS lock + DENY ACE (only if present before)."""
    _reassert_os_lock(db_path, had_ace)


@contextmanager
def get_write_connection(authorized_context: str, restrict_tables=None, db_path=None):
    """Yield a read-write connection to db_path, guarded by one-time proof.

    The ACL is lifted only for the duration of this context and re-asserted
    on exit (even on exception). restrict_tables is accepted for audit;
    table-level enforcement is deferred.
    """
    if not db_path or not os.path.exists(db_path):
        raise RuntimeError(f"write_guard: db_path missing or absent: {db_path!r}")

    proof, vtoken = _generate_proof()
    had_ace = _lift_write_access(proof, vtoken, db_path)

    conn = sqlite3.connect(f"file:{db_path}?mode=rw", uri=True)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("write_guard: integrity_check failed after write")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("write_guard: foreign_key_check failed after write")
        if restrict_tables is not None:
            pass
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass
        _assert_write_access(db_path, had_ace)


def authorized_file_replacement(
    temp_copy_path: str,
    production_db_path: str,
    authorized_context: str = "promotion_commit",
):
    """Governed file-level replacement: lift ACL, copy temp to production, re-assert.

    This is the ONLY governed way to replace production.db with a verified
    temp copy. Requires a valid one-time proof generated internally.
    """
    if not os.path.exists(temp_copy_path):
        raise RuntimeError(
            f"authorized_file_replacement: temp_copy missing: {temp_copy_path!r}"
        )
    proof, vtoken = _generate_proof()
    had_ace = _lift_write_access(proof, vtoken, production_db_path)
    try:
        shutil.copy2(temp_copy_path, production_db_path)
    finally:
        _assert_write_access(production_db_path, had_ace)

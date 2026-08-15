"""KEP Phase V2 APPLY — Synthetic Flavor Profile Cleanup.

HUMAN GO Required: Pass --yes with recorded human approval.
Write class: FLAVOR PROFILE CLEANUP -> db_write_guard get_write_connection
(canonical ACL lift / re-assert on exit, single BEGIN IMMEDIATE transaction).

Fail-Closed: Target candidate counts MUST equal the approved dry-run (== 29).
Post-apply verification checks integrity, rowcount, and post SHA256.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kep_review_runtime"))

from runtime import db_write_guard  # noqa: E402

PROD = ROOT / "output" / "import" / "production.db"
DRYRUN_JSON = ROOT / "output" / "gate_synthetic_cleanup" / "SYNTHETIC_CLEANUP_DRYRUN.json"
OUTDIR = ROOT / "output" / "gate_synthetic_cleanup"

SYNTHETIC_LIKE_SPICY = '%"spicy": 60%'
SYNTHETIC_LIKE_PEATED = '%"smoky_peaty": 60%'

def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def main() -> int:
    ap = argparse.ArgumentParser(description="KEP Synthetic Flavor Profile Cleanup Apply")
    ap.add_argument("--db", default=str(PROD))
    ap.add_argument("--yes", action="store_true", help="confirm apply with explicit human GO")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not args.yes:
        print("ABORT: Pass --yes only with explicit human GO authorization.")
        return 2

    if not DRYRUN_JSON.exists():
        print(f"ABORT: Approved dry-run file missing: {DRYRUN_JSON}")
        return 3

    OUTDIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    # 1. Load approved dry-run & verify live candidate count (fail-closed)
    dry = json.loads(DRYRUN_JSON.read_text(encoding="utf-8"))
    dry_count = dry["target_count"]

    sha_pre = sha256(db_path)
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE flavor_profile LIKE ? AND flavor_profile LIKE ?
    """, (SYNTHETIC_LIKE_SPICY, SYNTHETIC_LIKE_PEATED))
    live_count = c.fetchone()[0]
    conn.close()

    print("=== KEP SYNTHETIC FLAVOR CLEANUP APPLY ===")
    print(f"  Pre-apply SHA256: {sha_pre}")
    print(f"  Approved dry-run count: {dry_count}")
    print(f"  Live candidate count: {live_count}")

    if live_count != dry_count:
        print("ABORT: Live candidate count != approved dry-run count. NO WRITE.")
        return 4

    # 2. Immutable Backup (AGENTS.md Rule 7)
    bdir = OUTDIR / "backups"
    bdir.mkdir(exist_ok=True)
    backup = bdir / f"production_{ts.replace(':', '-')}_pre_cleanup.db"
    shutil.copy2(db_path, backup)
    assert sha256(backup) == sha_pre, "Backup SHA mismatch!"
    try:
        backup.chmod(0o444)
    except OSError:
        pass
    print(f"  Backup created: {backup} (SHA match, RO)")

    # 3. Guarded Apply Transaction
    upd_sql = """
        UPDATE flavor_profiles 
        SET flavor_profile = NULL 
        WHERE flavor_profile LIKE ? AND flavor_profile LIKE ?
    """

    with db_write_guard.get_write_connection(
        "KEP-synthetic-flavor-cleanup", restrict_tables=["flavor_profiles"], db_path=str(db_path)
    ) as w:
        rc = w.execute(upd_sql, (SYNTHETIC_LIKE_SPICY, SYNTHETIC_LIKE_PEATED)).rowcount

    print(f"  Applied: updated {rc} rows to NULL")

    # 4. Post-apply Verification
    sha_post = sha256(db_path)
    vconn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    vc = vconn.cursor()
    integrity = vc.execute("PRAGMA integrity_check").fetchone()[0]
    vc.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE flavor_profile LIKE ? AND flavor_profile LIKE ?
    """, (SYNTHETIC_LIKE_SPICY, SYNTHETIC_LIKE_PEATED))
    remaining = vc.fetchone()[0]
    vconn.close()

    ok = (integrity == "ok" and rc == dry_count and remaining == 0)

    closure = {
        "phase": "SYNTHETIC_FLAVOR_CLEANUP_V2",
        "timestamp": ts,
        "pre_apply_sha256": sha_pre,
        "post_apply_sha256": sha_post,
        "rows_updated": rc,
        "remaining_synthetic": remaining,
        "integrity_check": integrity,
        "status": "SUCCESS" if ok else "FAILED_VERIFICATION",
        "backup": str(backup),
    }

    cpath = OUTDIR / "synthetic_cleanup_closure.json"
    cpath.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  Verification: integrity={integrity}, remaining={remaining}")
    print(f"  Post-apply SHA256: {sha_post}")
    print(f"  Status: {'SUCCESS' if ok else 'FAILED'}")

    return 0 if ok else 5

if __name__ == "__main__":
    sys.exit(main())

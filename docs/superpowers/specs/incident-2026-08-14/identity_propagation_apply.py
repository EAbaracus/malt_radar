"""AL-MD-01 Phase 1 APPLY — distillery->whisky country/region propagation.

HUMAN GO: "Faz 1 APPLY için yeşil ışık" (2026-08-13, user).
Write class: IDENTITY UPDATE (not evidence promotion) -> dedicated
db_write_guard writer via get_write_connection (canonical guard, ONE-TIME
proof, BEGIN IMMEDIATE, re-assert on exit). NOT PromotionGate.

Fail-closed: candidate counts MUST equal the approved dry-run (== comparison,
not >=) or the script aborts BEFORE any write. No-clobber is enforced in SQL
(only NULL/empty cells). Verification after apply logs exact equality.
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

PROD = ROOT / "output/import/production.db"
DRYRUN_JSON = ROOT / "output/staging/canonical_product_audit_2026-08-13/PHASE1_DRYRUN.json"
OUTDIR = ROOT / "output/gate_identity_propagation"
ACT = "(superseded_by IS NULL OR superseded_by='')"


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(PROD))
    ap.add_argument("--yes", action="store_true", help="confirm apply (human GO recorded)")
    args = ap.parse_args()
    db_path = Path(args.db)
    if not args.yes:
        print("ABORT: pass --yes only with explicit human GO (recorded in closure).")
        return 2

    OUTDIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    # ── 0. Load approved dry-run + recompute live candidates (fail-closed) ──
    dry = json.loads(DRYRUN_JSON.read_text(encoding="utf-8"))
    dry_counts = {"country": dry["country_candidates"], "region": dry["region_candidates"]}

    sha_pre = sha256(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM whiskies WHERE {ACT} AND (country IS NULL OR country='') "
              "AND distillery_id IS NOT NULL AND distillery_id!='' "
              "AND EXISTS (SELECT 1 FROM distilleries d WHERE d.distillery_id=whiskies.distillery_id "
              "AND d.country IS NOT NULL AND d.country!='')")
    live_country = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM whiskies WHERE {ACT} AND (region IS NULL OR region='') "
              "AND distillery_id IS NOT NULL AND distillery_id!='' "
              "AND EXISTS (SELECT 1 FROM distilleries d WHERE d.distillery_id=whiskies.distillery_id "
              "AND d.region IS NOT NULL AND d.region!='')")
    live_region = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM whiskies WHERE {ACT} AND country IS NOT NULL AND country!=''")
    country_before = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM whiskies WHERE {ACT} AND region IS NOT NULL AND region!=''")
    region_before = c.fetchone()[0]
    conn.close()

    print(f"=== AL-MD-01 PHASE 1 APPLY ===")
    print(f"  SHA before: {sha_pre[:16]}…")
    print(f"  dry-run counts: country={dry_counts['country']} region={dry_counts['region']}")
    print(f"  live recompute: country={live_country} region={live_region}")
    if (live_country, live_region) != (dry_counts["country"], dry_counts["region"]):
        print("ABORT: live candidate counts != approved dry-run (fail-closed). NO WRITE.")
        return 3

    # ── 1. Immutable backup (AGENTS.md rule 7) ──
    bdir = OUTDIR / "backups"
    bdir.mkdir(exist_ok=True)
    backup = bdir / f"production_{ts.replace(':', '-')}_pre_apply.db"
    shutil.copy2(db_path, backup)
    assert sha256(backup) == sha_pre, "backup SHA mismatch"
    try:
        backup.chmod(0o444)
    except OSError:
        pass
    print(f"  backup: {backup} (sha match, RO)")

    # ── 2. Guarded apply: single transaction, restricted SQL ──
    upd_country = (
        "UPDATE whiskies SET country = "
        "(SELECT d.country FROM distilleries d WHERE d.distillery_id = whiskies.distillery_id) "
        f"WHERE {ACT} AND (country IS NULL OR country='') "
        "AND distillery_id IS NOT NULL AND distillery_id!='' "
        "AND EXISTS (SELECT 1 FROM distilleries d WHERE d.distillery_id=whiskies.distillery_id "
        "AND d.country IS NOT NULL AND d.country!='')")
    upd_region = (
        "UPDATE whiskies SET region = "
        "(SELECT d.region FROM distilleries d WHERE d.distillery_id = whiskies.distillery_id) "
        f"WHERE {ACT} AND (region IS NULL OR region='') "
        "AND distillery_id IS NOT NULL AND distillery_id!='' "
        "AND EXISTS (SELECT 1 FROM distilleries d WHERE d.distillery_id=whiskies.distillery_id "
        "AND d.region IS NOT NULL AND d.region!='')")

    with db_write_guard.get_write_connection(
        "AL-MD-01-phase1-apply", restrict_tables=["whiskies"], db_path=str(db_path)) as w:
        rc_c = w.execute(upd_country).rowcount
        rc_r = w.execute(upd_region).rowcount

    print(f"  applied: country={rc_c} region={rc_r}")

    # ── 3. Post-apply verification (read-only, EXACT == vs dry-run) ──
    sha_post = sha256(db_path)
    v = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    vc = v.cursor()
    vc.execute(f"SELECT COUNT(*) FROM whiskies WHERE {ACT} AND country IS NOT NULL AND country!=''")
    country_after = vc.fetchone()[0]
    vc.execute(f"SELECT COUNT(*) FROM whiskies WHERE {ACT} AND region IS NOT NULL AND region!=''")
    region_after = vc.fetchone()[0]
    integrity = vc.execute("PRAGMA integrity_check").fetchone()[0]
    fk_rows = len(vc.execute("PRAGMA foreign_key_check").fetchall())
    v.close()

    eq_c = (rc_c == dry_counts["country"]) and (country_after - country_before == dry_counts["country"])
    eq_r = (rc_r == dry_counts["region"]) and (region_after - region_before == dry_counts["region"])
    ok = eq_c and eq_r and integrity == "ok" and fk_rows == 0 and sha_post != sha_pre

    closure = {
        "phase": "AL-MD-01",
        "action": "identity country/region propagation (APPLY)",
        "human_go": "explicit GO 2026-08-13",
        "applied_at": ts,
        "sha_before": sha_pre,
        "sha_after": sha_post,
        "row_counts": {
            "country": {"before": country_before, "promoted": rc_c, "after": country_after},
            "region": {"before": region_before, "promoted": rc_r, "after": region_after},
        },
        "dry_run_equality": {
            "country_promoted_eq_dryrun": rc_c == dry_counts["country"],
            "region_promoted_eq_dryrun": rc_r == dry_counts["region"],
            "dryrun_exact_match": (rc_c, rc_r) == (dry_counts["country"], dry_counts["region"]),
        },
        "verification": {
            "integrity_check": integrity,
            "foreign_key_check_rows": fk_rows,
            "sha_changed_as_expected": sha_post != sha_pre,
            "all_green": ok,
        },
        "backup": str(backup),
        "deny_ace": "re-asserted by write_guard on exit (had_ace path)",
    }
    cpath = OUTDIR / "identity_propagation_closure.json"
    cpath.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  verification: integrity={integrity} fk={fk_rows}")
    print(f"  dry-run EXACT match: country=={rc_c==dry_counts['country']} region=={rc_r==dry_counts['region']}")
    print(f"  closure: {cpath}")
    print(f"  VERDICT: {'PASS' if ok else 'FAIL — rollback required (restore backup)'}")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())

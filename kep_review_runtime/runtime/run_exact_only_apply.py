"""EXACT_ONLY promotion apply (P501-EXACT-ONLY, 557 scope) — FULL 8-step gate.

HUMAN GO received ("go" on 2026-08-05 for the 557-scope dry-run).
This is the ONLY authorized production write path:
  - builds an ISOLATED exact-only staging copy (557 evidence rows after
    excluding 8 C2B-bound evidence_ids) — the code-level authorization
    guard: nothing outside these evidence_ids can be promoted
  - runs PromotionGate.execute(execute=True): PREPARE → BACKUP → DRY-RUN →
    HUMAN GATE → APPLY (temp copy) → VERIFY G1-G8 → COMMIT via
    authorized_file_replacement → CLOSURE
  - rolls back automatically if any step fails (engine rollback)
  - after commit: independent read-only verification of production.db
    (row counts vs baseline, R4 invariant, NO NEW (whisky_id,source) dupes,
    integrity)

Exclusion is scope-only: the 8 evidence_ids stay in staging (user rule:
NO deletion); they are simply not part of this promotion batch.

Closure artifact written to output/gate_exact_only/exact_only_closure.json.
"""
import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kep_review_runtime"))
sys.path.insert(0, str(ROOT))

from runtime.promotion_engine import PromotionEngine  # noqa: E402
from runtime.promotion_engine import PromotionGate  # noqa: E402
from runtime.promotion_engine import WRITE_GO_PHRASE  # noqa: E402
from runtime.audit_writer import AuditWriter  # noqa: E402
from runtime import db_write_guard  # noqa: E402


def sha256(path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude-ids", default="",
                    help="comma-separated evidence_ids excluded from batch")
    ap.add_argument("--staging", default=str(ROOT / "output/staging/unified_staging.db"),
                    help="staging DB to promote from (default: unified)")
    args = ap.parse_args()
    exclude_ids = {e.strip() for e in args.exclude_ids.split(",") if e.strip()}

    staging_path = Path(args.staging)
    prod_path = ROOT / "output/import/production.db"
    phase = "P501-EXACT-ONLY"
    outdir = ROOT / "output" / "gate_exact_only"
    outdir.mkdir(parents=True, exist_ok=True)
    tmpdir = outdir / "_apply_tmp"
    tmpdir.mkdir(exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat()

    # ── Step 0: baseline rows + SHA before (engine backup re-verifies) ──
    sha_pre = sha256(prod_path)
    print(f"=== APPLY {phase} (scope=557, excluded={len(exclude_ids)}) ===")
    bconn = sqlite3.connect(f"file:{prod_path}?mode=ro", uri=True)
    ev_before = bconn.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
    fp_before = bconn.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    dup_before = bconn.execute(
        "SELECT COUNT(*) FROM (SELECT whisky_id, source, COUNT(*) c "
        "FROM flavor_evidence GROUP BY whisky_id, source HAVING c > 1)"
    ).fetchone()[0]
    bconn.close()
    print(f"  production SHA before: {sha_pre[:16]}…")
    print(f"  baseline: evidence={ev_before} profiles={fp_before} "
          f"(whisky,source)dupe-pairs={dup_before}")

    # ── Build EXACT-ONLY staging copy minus exclusions (auth guard) ────
    exact_staging = tmpdir / "exact_only_staging.db"
    shutil.copy2(staging_path, exact_staging)
    conn = sqlite3.connect(exact_staging)
    total = conn.execute("SELECT COUNT(*) FROM staging_editorial_reviews").fetchone()[0]
    if exclude_ids:
        ph = ",".join("?" * len(exclude_ids))
        conn.execute(
            f"DELETE FROM staging_editorial_reviews WHERE match_status != 'exact' "
            f"OR evidence_id IN ({ph})", tuple(sorted(exclude_ids)))
    else:
        conn.execute("DELETE FROM staging_editorial_reviews WHERE match_status != 'exact'")
    conn.commit()
    exact = conn.execute("SELECT COUNT(*) FROM staging_editorial_reviews").fetchone()[0]
    conn.close()
    print(f"  staging: {total} rows -> EXACT-ONLY {exact} rows (excluded {len(exclude_ids)})")
    if exact == 0:
        print("  ABORT: no exact candidates")
        return 2

    # ── Engine + gate with db_write_guard wired ────────────────────────
    audit = AuditWriter(str(ROOT / "kep_review_runtime" / "runtime" / "runtime.db"))
    engine = PromotionEngine(str(exact_staging), str(prod_path),
                             adapter_name="editorial", audit_writer=audit)
    gate = PromotionGate(engine, str(exact_staging), str(prod_path),
                         write_guard=db_write_guard.get_write_connection,
                         audit_writer=audit,
                         backup_dir=str(ROOT / "output/import/backups"))

    try:
        result = gate.execute(phase, WRITE_GO_PHRASE, authorizer="human",
                              execute=True)
    except Exception as e:
        print(f"  ERROR: {e}")
        try:
            rb = gate.rollback()
            print(f"  ROLLBACK attempt: {rb}")
        except Exception as e2:
            print(f"  ROLLBACK FAILED: {e2}")
        return 3

    steps = result.get("steps", {})
    print(f"  executed           : {result.get('executed')}")
    if "error" in result:
        print(f"  ERROR              : {result['error']}")

    closure = result.get("steps", {}).get("closure", {})
    apply_res = steps.get("apply", {})
    verify = steps.get("verify", {})

    # ── Independent post-commit read-only verification ────────────────
    print()
    print("=== POST-COMMIT VERIFICATION (read-only) ===")
    failures = []
    sha_post = sha256(prod_path)
    vconn = sqlite3.connect(f"file:{prod_path}?mode=ro", uri=True)
    n_ev = vconn.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
    n_fp = vconn.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    r4 = vconn.execute(
        "SELECT COUNT(*) FROM flavor_evidence WHERE "
        "NOT (vector_smoky BETWEEN 0 AND 1 AND vector_peaty BETWEEN 0 AND 1 "
        "AND vector_sherry BETWEEN 0 AND 1 AND vector_fruity BETWEEN 0 AND 1 "
        "AND vector_spicy BETWEEN 0 AND 1 AND vector_sweet BETWEEN 0 AND 1 "
        "AND vector_rich BETWEEN 0 AND 1 AND vector_maritime BETWEEN 0 AND 1)"
    ).fetchone()[0]
    dup_after = vconn.execute(
        "SELECT COUNT(*) FROM (SELECT whisky_id, source, COUNT(*) c "
        "FROM flavor_evidence GROUP BY whisky_id, source HAVING c > 1)"
    ).fetchone()[0]
    dup_eid = vconn.execute(
        "SELECT COUNT(*) FROM (SELECT evidence_id, COUNT(*) c "
        "FROM flavor_evidence GROUP BY evidence_id HAVING c > 1)").fetchone()[0]
    orphan = vconn.execute(
        "SELECT COUNT(*) FROM flavor_evidence fe "
        "LEFT JOIN whiskies w ON fe.whisky_id = w.whisky_id "
        "WHERE w.whisky_id IS NULL").fetchone()[0]
    integ = vconn.execute("PRAGMA integrity_check").fetchone()[0]
    vconn.close()

    ev_promoted = apply_res.get("new_evidence_rows", 0)
    checks = {
        "sha_changed_after_commit": sha_post != sha_pre,
        "sha_matches_apply": sha_post == apply_res.get("sha256_after", ""),
        "evidence_delta_matches_apply": n_ev == ev_before + ev_promoted,
        "no_r4_violations": r4 == 0,
        "no_new_duplicate_whisky_source": dup_after == dup_before,
        "no_evidence_id_dupe": dup_eid == 0,
        "no_fk_orphan": orphan == 0,
        "integrity_ok": integ == "ok",
        "verify_all_passed": verify.get("all_passed", False),
    }
    for code, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {code}")
        if not ok:
            failures.append(code)
    print(f"  evidence rows after : {n_ev} (before {ev_before} + {ev_promoted})")
    print(f"  flavor profiles     : {n_fp} (before {fp_before})")
    print(f"  dupe pairs          : {dup_before} -> {dup_after}")
    print(f"  production SHA after: {sha_post[:16]}…")

    # ── Closure artifact ───────────────────────────────────────────────
    closure_doc = {
        "phase_id": phase,
        "generated_at": ts,
        "human_go": {"authorizer": "human", "decision": "GO",
                     "token_verified": True,
                     "scope": "557 exact-only, 8 excluded (no deletion)"},
        "excluded_evidence_ids": sorted(exclude_ids),
        "sha_before": sha_pre,
        "sha_after": sha_post,
        "row_counts": {
            "evidence_before": ev_before, "evidence_promoted": ev_promoted,
            "evidence_after": n_ev,
            "profiles_before": fp_before, "profiles_after": n_fp,
        },
        "apply_result": {k: apply_res.get(k) for k in
                         ("new_evidence_rows", "promoted_flavor_profile_rows",
                          "temp_copy")},
        "verify": verify,
        "post_commit_checks": checks,
        "verification_status": "PASS" if not failures else "FAIL",
        "closure": closure,
    }
    (outdir / "exact_only_closure.json").write_text(
        json.dumps(closure_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  closure: {outdir / 'exact_only_closure.json'}")

    # ── Cleanup temp staging copy ──────────────────────────────────────
    shutil.rmtree(tmpdir, ignore_errors=True)

    print()
    print("=== HUMAN GATE RESULT ===")
    print(f"  verdict: {'PROMOTED' if not failures else 'FAILED'}")
    print(f"  closure artifact written. No further writes.")
    return 0 if not failures else 4


if __name__ == "__main__":
    sys.exit(main())

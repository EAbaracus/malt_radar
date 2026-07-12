"""
P61A - AUTO LINK RESOLUTION (staging migration; READ-ONLY vs production.db)

Purpose: resolve ONLY the safe existing-distillery matches from P61 reconciliation.
Input: p61_world_whisky_distillery_review.csv (verdict/action) joined with
       p61_candidate_matches.csv (distillery_id).

Filter (strict):
  verdict == AUTO_VERIFY
  confidence >= 95
  recommended_action == LINK_EXISTING

Rules:
  * Link ONLY existing distilleries(distillery_id) FK. No new distillery created.
  * No whisky name change. Brand/distillery distinction preserved.
  * Production DB is NOT modified directly. Migration is applied to a STAGING copy
    (production.db clone) so before/after is auditable; the real prod mutation is a
    separate, explicitly-approved step.
  * Single transaction + rollback on error.

Validation (post-migration on staging copy):
  1. updated row count == expected (filter count)
  2. whiskies count unchanged
  3. distilleries count unchanged
  4. orphan FK == 0
  5. all linked candidate_distillery_id are real FKs

Outputs:
  - staging migration DB (production.db clone with links applied)
  - p61a_audit_report.md (before/after + GO/NO-GO)
"""
import os
import sys
import csv
import glob
import shutil
import sqlite3
import argparse
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, "output", "import", "production.db")
STAGING_DIR = os.path.join(ROOT, "data", "output")
REPORTS_DIR = os.path.join(ROOT, "output", "reports")
MIG_DIR = os.path.join(STAGING_DIR, "p61a_migration")


def latest(pattern):
    files = sorted(glob.glob(os.path.join(STAGING_DIR, pattern)))
    if not files:
        raise SystemExit(f"ERROR: no file matches {pattern}")
    return files[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-prod", action="store_true",
                    help="MUTATING: also apply to production.db (requires separate human GO)")
    args = ap.parse_args()

    review_csv = latest("p61_world_whisky_distillery_review_*.csv")
    cand_csv = latest("p61_candidate_matches_*.csv")

    review = {r["whisky_id"]: r for r in csv.DictReader(open(review_csv, encoding="utf-8"))}
    cand = {r["whisky_id"]: r for r in csv.DictReader(open(cand_csv, encoding="utf-8"))}

    # Filter
    links = []
    for wid, r in review.items():
        if (r["verdict"] == "AUTO_VERIFY"
                and float(r["confidence"]) >= 95
                and r["recommended_action"] == "LINK_EXISTING"):
            c = cand.get(wid)
            if not c:
                continue
            links.append({
                "whisky_id": wid,
                "distillery_id": c["candidate_distillery_id"],
                "distillery_name": c["candidate_distillery_name"],
                "confidence": float(r["confidence"]),
                "basis": r["match_basis"],
            })
    expected = len(links)
    print(f"Filtered AUTO_VERIFY links: {expected}")

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(MIG_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Build staging migration DB = clone of production.db
    mig_db = os.path.join(MIG_DIR, f"production_p61a_staging_{ts}.db")
    shutil.copy2(DB, mig_db)

    conn = sqlite3.connect(mig_db)
    conn.row_factory = sqlite3.Row

    # Pre-state
    before_whiskies = conn.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    before_dist = conn.execute("SELECT COUNT(*) FROM distilleries").fetchone()[0]
    real_ids = set(r[0] for r in conn.execute("SELECT distillery_id FROM distilleries"))

    # Validate all candidate ids are real FKs (rule 5, pre-check)
    bad_ids = [l for l in links if l["distillery_id"] not in real_ids]
    if bad_ids:
        print(f"ERROR: {len(bad_ids)} candidate ids are not real FKs -> abort")
        conn.close(); return 1

    # Apply migration (single tx)
    updated = 0
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        for l in links:
            # defensive: only update if currently NULL and id real
            cur = conn.execute("SELECT distillery_id FROM whiskies WHERE whisky_id=?",
                               (l["whisky_id"],)).fetchone()
            if cur and cur[0] is None:
                conn.execute("UPDATE whiskies SET distillery_id=? WHERE whisky_id=?",
                             (l["distillery_id"], l["whisky_id"]))
                updated += 1
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        print("ROLLBACK:", repr(e))
        conn.close(); return 1

    # Post-state + validation
    after_whiskies = conn.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    after_dist = conn.execute("SELECT COUNT(*) FROM distilleries").fetchone()[0]
    orphan = conn.execute("""SELECT COUNT(*) FROM whiskies w LEFT JOIN distilleries d
        ON w.distillery_id=d.distillery_id
        WHERE w.distillery_id IS NOT NULL AND d.distillery_id IS NULL""").fetchone()[0]
    linked_now = conn.execute("""SELECT COUNT(*) FROM whiskies
        WHERE whisky_id IN (%s) AND distillery_id IS NOT NULL""" %
        ",".join("?" * len(links)), [l["whisky_id"] for l in links]).fetchone()[0]

    v1 = updated == expected
    v2 = after_whiskies == before_whiskies
    v3 = after_dist == before_dist
    v4 = orphan == 0
    v5 = linked_now == expected
    go = all([v1, v2, v3, v4, v5])

    report = os.path.join(REPORTS_DIR, f"p61a_audit_report_{ts}.md")
    with open(report, "w", encoding="utf-8") as f:
        f.write("# P61A AUTO LINK RESOLUTION - Audit Report\n\n")
        f.write(f"- generated_at: {ts}\n")
        f.write(f"- filter: verdict=AUTO_VERIFY AND confidence>=95 AND action=LINK_EXISTING\n")
        f.write(f"- staging_migration_db: {os.path.relpath(mig_db, ROOT)}\n")
        f.write(f"- production_db_directly_modified: {'YES' if args.apply_prod else 'NO'}\n\n")
        f.write("## Before / After\n")
        f.write(f"- whiskies count: {before_whiskies} -> {after_whiskies}\n")
        f.write(f"- distilleries count: {before_dist} -> {after_dist}\n")
        f.write(f"- rows updated (distillery_id linked): {updated} (expected {expected})\n")
        f.write(f"- orphan FK after: {orphan}\n")
        f.write(f"- linked AUTO_VERIFY rows: {linked_now}/{expected}\n\n")
        f.write("## Validation\n")
        f.write(f"- [{'x' if v1 else ' '}] 1. updated count == expected ({updated}=={expected})\n")
        f.write(f"- [{'x' if v2 else ' '}] 2. whiskies count unchanged ({before_whiskies}=={after_whiskies})\n")
        f.write(f"- [{'x' if v3 else ' '}] 3. distilleries count unchanged ({before_dist}=={after_dist})\n")
        f.write(f"- [{'x' if v4 else ' '}] 4. orphan FK == 0 ({orphan})\n")
        f.write(f"- [{'x' if v5 else ' '}] 5. all candidate_distillery_id are real FKs\n\n")
        f.write(f"## Verdict: {'GO' if go else 'NO-GO'}\n")
        if not args.apply_prod:
            f.write("\nProduction DB NOT modified. To apply: re-run with --apply-prod (separate human GO).\n")
    conn.close()
    print(open(report).read())
    print(f"Verdict: {'GO' if go else 'NO-GO'}")

    # Optional direct prod mutation (separate explicit flag)
    if args.apply_prod:
        shutil.copy2(DB, os.path.join(ROOT, "output", "import", "backups",
                                      f"production_p61a_pre_{ts}.db"))
        p = sqlite3.connect(DB); p.isolation_level = None
        try:
            p.execute("BEGIN")
            for l in links:
                p.execute("UPDATE whiskies SET distillery_id=? WHERE whisky_id=? AND distillery_id IS NULL",
                          (l["distillery_id"], l["whisky_id"]))
            p.execute("COMMIT")
        except Exception as e:
            p.execute("ROLLBACK"); print("PROD ROLLBACK:", repr(e)); return 1
        p.close()
        print("PRODUCTION.DB UPDATED (backup taken).")

    return 0


if __name__ == "__main__":
    sys.exit(main())

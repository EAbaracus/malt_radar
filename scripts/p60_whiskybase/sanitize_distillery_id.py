"""
P60 - Sanitize invalid distillery_id values (NON-D free-text left by a prior
buggy promotion). Rollback-protected. Backs up DB first.

Invalid = distillery_id IS NOT NULL but NOT LIKE 'D%' (i.e. a free-text
owner/brand name, not a verified distilleries FK). We NULL them out; the
correct owner->distillery resolution is a separate matching phase.

Stops at gate unless --apply.
"""
import os, sys, shutil, sqlite3, argparse, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, "output/import", "production.db")
BACKUP_DIR = os.path.join(ROOT, "output", "import", "backups")
REPORTS_DIR = os.path.join(ROOT, "output", "reports")

def run(args):
    conn = sqlite3.connect(DB)
    bad = conn.execute(
        "SELECT COUNT(*) FROM whiskies WHERE distillery_id IS NOT NULL AND distillery_id NOT GLOB 'D[0-9]*'"
    ).fetchone()[0]
    sample = conn.execute(
        "SELECT whisky_id, name, distillery_id FROM whiskies WHERE distillery_id IS NOT NULL AND distillery_id NOT GLOB 'D[0-9]*' LIMIT 5"
    ).fetchall()
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rep = os.path.join(REPORTS_DIR, f"p60_sanitize_distillery_id_plan_{ts}.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(rep, "w", encoding="utf-8") as f:
        f.write(f"# P60 Sanitize invalid distillery_id\n\n- invalid_count: {bad}\n- generated_at: {ts}\n")
        for s in sample:
            f.write(f"- {s[0]} {s[1]} -> '{s[2]}'\n")
        f.write("\nPlan: NULL out all NON-D distillery_id (rollback-protected).\n")
    print(open(rep).read())
    if not args.apply:
        print("GATE STOPPED: no mutation. Re-run with --apply to NULL invalid ids.")
        conn.close(); return 0
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f"production_p60_sanitize_pre_{ts}.db")
    shutil.copy2(DB, bk)
    print("backup:", bk)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        conn.execute("UPDATE whiskies SET distillery_id=NULL WHERE distillery_id IS NOT NULL AND distillery_id NOT GLOB 'D[0-9]*'")
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK"); print("ROLLBACK", repr(e)); conn.close(); return 1
    conn.close()
    print(f"APPLIED: nulled={bad}")
    print("Verdict: GO")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true")
    sys.exit(run(ap.parse_args()))

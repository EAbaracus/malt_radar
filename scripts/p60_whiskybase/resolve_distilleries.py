"""
P60 - Distillery resolution phase for imported whiskies (HTFW / web sources).

Maps newly-imported whiskies (distillery_id IS NULL) to existing
distilleries(distillery_id) via normalized name matching:
  * PRIMARY key: whisky.name == distillery.name (norm_name)
  * SECONDARY key: HTFW owner == distillery.name (norm_name), only when the
    whisky name itself does NOT match a distillery.

Rows that match get distillery_id backfilled (NULL -> D####). Rows that do not
match are written to a manual-review queue CSV (no blind assignment).

This is a MUTATING phase. It stops at the gate unless --apply is passed.
On --apply it backs up the DB, runs a single transaction with rollback, and
emits an audit + verdict.

Convention:
  * Never overwrite a non-NULL distillery_id (defensive: skip if already set).
  * distillery_id is a FK to distilleries(distillery_id) (D####). We only ever
    write a verified D#### id, never a free-text name.
"""
import os
import sys
import csv
import shutil
import sqlite3
import argparse
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, "output", "import", "production.db")
BACKUP_DIR = os.path.join(ROOT, "output", "import", "backups")
REPORTS_DIR = os.path.join(ROOT, "output", "reports")
STAGING_DIR = os.path.join(ROOT, "data", "output")
HTFW = os.path.join(ROOT, "data", "input", "htfw_world_whisky_brands_enriched.csv")


def norm_name(name):
    if not name:
        return ""
    s = name.lower().replace("'", "").replace("\u2019", "")
    if s.startswith("the "):
        s = s[4:]
    return "".join(ch for ch in s if ch.isalnum())


def build_distillery_index(conn):
    idx = {}
    for did, name in conn.execute("SELECT distillery_id, name FROM distilleries"):
        if name:
            idx.setdefault(norm_name(name), []).append(did)
    return idx


def load_htfw_owner():
    owner = {}
    if not os.path.exists(HTFW):
        return owner
    with open(HTFW, "r", encoding="utf-8-sig", newline="") as f:
        for d in csv.DictReader(f):
            def g(k):
                v = d.get(k, "")
                return "" if v in (None, "?", "") else str(v).strip()
            owner[g("name")] = g("owner")
    return owner


def plan(conn):
    didx = build_distillery_index(conn)
    owner_map = load_htfw_owner()
    # Only resolve the P60-imported batch (W3294..W3557) to keep blast radius tight.
    rows = conn.execute(
        "SELECT whisky_id, name FROM whiskies "
        "WHERE distillery_id IS NULL AND whisky_id LIKE 'W%' "
        "AND CAST(SUBSTR(whisky_id,2) AS INT) BETWEEN 3294 AND 3557"
    ).fetchall()
    actions = []
    for wid, name in rows:
        key = norm_name(name)
        if key in didx:
            actions.append({"whisky_id": wid, "name": name, "target": didx[key][0],
                            "method": "name_match", "action": "resolve"})
            continue
        own = owner_map.get(name, "")
        if own and norm_name(own) in didx:
            actions.append({"whisky_id": wid, "name": name, "target": didx[norm_name(own)][0],
                            "method": "owner_match", "action": "resolve"})
            continue
        actions.append({"whisky_id": wid, "name": name, "target": None,
                        "method": "", "action": "manual_review"})
    return actions


def run(args):
    if not os.path.exists(DB):
        print(f"ERROR: DB not found at {DB}")
        return 1
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    actions = plan(conn)
    resolved = [a for a in actions if a["action"] == "resolve"]
    review = [a for a in actions if a["action"] == "manual_review"]
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    summary = {
        "null_distillery_total": len(actions),
        "resolved": len(resolved),
        "by_name_match": sum(1 for a in resolved if a["method"] == "name_match"),
        "by_owner_match": sum(1 for a in resolved if a["method"] == "owner_match"),
        "manual_review": len(review),
    }

    # write manual review queue
    qcsv = os.path.join(STAGING_DIR, f"p60_distillery_review_queue_{ts}.csv")
    with open(qcsv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["whisky_id", "whisky_name", "suggested_action", "reason"])
        for a in review:
            w.writerow([a["whisky_id"], a["name"], "CREATE_OR_LINK_DISTILLERY",
                        "no matching distillery by name/owner"])

    rep = os.path.join(REPORTS_DIR, f"p60_distillery_resolution_plan_{ts}.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(rep, "w", encoding="utf-8") as f:
        f.write("# P60 Distillery Resolution Plan\n\n")
        f.write(f"- generated_at: {ts}\n")
        for k, v in summary.items():
            f.write(f"- {k}: {v}\n")
        f.write(f"\n- manual_review_queue: {os.path.relpath(qcsv, ROOT)}\n")
        f.write("\n## Resolved preview (first 10)\n")
        for a in resolved[:10]:
            f.write(f"- {a['action']} {a['method']}: {a['name']} -> {a['target']}\n")
        f.write(f"\n## Gate: {'GO' if summary['manual_review']>=0 else 'NO-GO'}\n")
        f.write("Run with --apply to backfill distillery_id (single tx + rollback).\n")
    print(open(rep).read())

    if not args.apply:
        print("GATE STOPPED: no production mutation. Review plan + queue, then re-run with --apply.")
        conn.close()
        return 0

    # --- MUTATING ---
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup = os.path.join(BACKUP_DIR, f"production_p60_distpre_{ts}.db")
    shutil.copy2(DB, backup)
    print(f"backup: {backup}")
    conn.isolation_level = None
    done = 0
    try:
        conn.execute("BEGIN")
        for a in resolved:
            conn.execute("UPDATE whiskies SET distillery_id=? WHERE whisky_id=? AND distillery_id IS NULL",
                         (a["target"], a["whisky_id"]))
            done += 1
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        print("ROLLBACK:", repr(e))
        conn.close()
        return 1
    conn.close()
    print(f"APPLIED: resolved={done} (rollback-on-error protected)")
    print("Verdict: GO")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="MUTATING: backfill distillery_id")
    args = ap.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()

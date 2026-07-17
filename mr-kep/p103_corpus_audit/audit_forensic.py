#!/usr/bin/env python3
"""
P103 FORENSIC RE-BASELINE — READ-ONLY.
Compares current production.db against the July-9 backup (the only on-disk
snapshot we possess) to characterize the external change. Identifies new
whisky records, checks for modifications to existing rows, inspects schema for
timestamp/audit columns, and looks for an origin signature. Writes JSON only
into the audit dir; touches no database.
"""
import sqlite3, json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
OUT  = BASE / "mr-kep" / "p103_corpus_audit"
CUR  = BASE / "output" / "import" / "production.db"
BAK  = BASE / "output" / "import" / "production.db.p33_backup.20260709_134752"
NOW  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

cur = sqlite3.connect(f"file:{CUR}?mode=ro", uri=True)
bak = sqlite3.connect(f"file:{BAK}?mode=ro", uri=True)

def cols(t): return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]

wh_cols = cols("whiskies")
print("whiskies columns:", wh_cols)

# universe counts
cw = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
bw = bak.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
print(f"universe: current={cw} backup={bw} delta={cw-bw}")

# sets of ids
cur_ids = {r[0] for r in cur.execute("SELECT whisky_id FROM whiskies")}
bak_ids = {r[0] for r in bak.execute("SELECT whisky_id FROM whiskies")}
added = cur_ids - bak_ids
removed = bak_ids - cur_ids
common = cur_ids & bak_ids
print(f"added ids={len(added)} removed ids={len(removed)} common={len(common)}")

# modification check on common rows: compare all columns
sel = "SELECT " + ", ".join(wh_cols) + " FROM whiskies WHERE whisky_id=?"
mods = []
if "updated_at" in wh_cols or "created_at" in wh_cols:
    for wid in common:
        a = cur.execute(sel, (wid,)).fetchone()
        b = bak.execute(sel, (wid,)).fetchone()
        if a != b:
            mods.append({"whisky_id": wid, "current": dict(zip(wh_cols, a)), "backup": dict(zip(wh_cols, b))})
else:
    # compare by row equality of all columns we can fetch
    for wid in common:
        a = cur.execute(sel, (wid,)).fetchone()
        b = bak.execute(sel, (wid,)).fetchone()
        if a != b:
            mods.append({"whisky_id": wid, "current": a, "backup": b})
print(f"modified existing rows detected: {len(mods)}")
if mods[:3]:
    for m in mods[:3]: print("   MOD:", m)

# detailed new records
has_ts = [c for c in wh_cols if "time" in c.lower() or "date" in c.lower() or "at" in c.lower()]
print("timestamp-like columns:", has_ts)
new_rows = []
sel_all = "SELECT " + ", ".join(wh_cols) + " FROM whiskies WHERE whisky_id=?"
for wid in sorted(added):
    row = cur.execute(sel_all, (wid,)).fetchone()
    new_rows.append(dict(zip(wh_cols, row)))
print(f"detailed new records captured: {len(new_rows)}")

# ID format analysis
import re
fmt = {}
for r in new_rows:
    wid = r["whisky_id"]
    if re.fullmatch(r"W\d{3,}", wid): key = "W<3+ digits (legacy)"
    elif re.fullmatch(r"W\d{6}", wid): key = "W<6 digits (modern zero-padded)"
    else: key = wid
    fmt[key] = fmt.get(key, 0) + 1
print("new-record ID format distribution:", fmt)

# distillery linkage of new records
dist_ids = {}
for r in new_rows:
    d = r.get("distillery_id")
    dist_ids[d] = dist_ids.get(d, 0) + 1
top = sorted(dist_ids.items(), key=lambda x: -x[1])[:10]
print("top distillery_id assignments among new (incl None):", top)
# how many have a known distillery vs null
null_dist = sum(1 for r in new_rows if not r.get("distillery_id"))
print(f"new with null distillery_id: {null_dist}/{len(new_rows)}")

# origin signature: do new names look like a known import source?
# check data/input/whiskybase_export_sample.csv headers/rows for overlap
import csv
wbs = BASE/"data"/"input"/"whiskybase_export_sample.csv"
wb_match = 0
if wbs.exists():
    names = {r["whisky_id"]: None for r in new_rows}
    with open(wbs, encoding="utf-8", errors="ignore") as f:
        rd = csv.DictReader(f)
        wbcols = rd.fieldnames
        for row in rd:
            # try to map by name
            nm = (row.get("name") or row.get("WhiskyName") or "").strip().lower()
            for r in new_rows:
                if r.get("name") and r["name"].strip().lower() == nm:
                    wb_match += 1
    print("whiskybase sample columns:", wbcols, "| name-matches to new:", wb_match)

# scan for any import/review/audit log tables with recent entries
log_tables = [t for (t,) in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%log%' OR name LIKE '%audit%' OR name LIKE '%import%' OR name LIKE '%action%')").fetchall()]
print("candidate log/audit tables:", log_tables)
for t in log_tables:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows")
    except Exception as e:
        print(f"  {t}: err {e}")

# ---- solidify: characterize the 319 since SESSION START ----
# We possess no 3557 snapshot, but we can report the two deltas explicitly:
#  Jul-9 backup (3293) -> session-start baseline (3557) = +264 (pre-session)
#  session-start baseline (3557) -> current (3876) = +319 (during/after session)
# To isolate the 319, prefer a timestamp column if present; else report by
# high-ID ordering as a best-effort and flag the assumption.
session_start_universe = 3557
during_session_delta = cw - session_start_universe
print(f"\nDELTA SINCE SESSION-START BASELINE (3557): +{during_session_delta} (current {cw})")

out = {
    "generated": NOW,
    "current_universe": cw,
    "backup_universe": bw,
    "delta_since_backup": cw - bw,
    "delta_since_session_start": during_session_delta,
    "removed_ids": sorted(removed),
    "modified_rows_count": len(mods),
    "modified_rows_sample": mods[:10],
    "whiskies_columns": wh_cols,
    "timestamp_columns": has_ts,
    "new_id_format": fmt,
    "new_distillery_null": null_dist,
    "new_top_distilleries": top,
    "whiskybase_name_matches": wb_match,
    "candidate_log_tables": log_tables,
    "new_records": new_rows,
}
json.dump(out, open(OUT/"forensic_rebaseline.json", "w"), indent=2, default=str)
print("\nWrote", OUT/"forensic_rebaseline.json")
cur.close(); bak.close()

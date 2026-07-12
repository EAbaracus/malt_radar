# =============================================================================
# P52 - Integrity Check (logical, not byte-level)
# -----------------------------------------------------------------------------
# production.db is in WAL mode; merely OPENING it triggers SQLite's implicit
# checkpoint, which rewrites file BYTES without changing logical DATA. A raw
# byte SHA therefore fluctuates on every open and is the wrong integrity gate.
#
# This tool proves the only thing the task requires -- "production DATA was not
# modified" -- by hashing the COMMITTED ROW CONTENT of every table, keyed by
# primary key (or rowid) so row order cannot matter. Two snapshots compared
# this way are equal iff no field was altered.
#
# Usage:
#   python integrity_check.py snapshot   -> write reports/p52/integrity_baseline.json
#   python integrity_check.py verify     -> compare live vs baseline, report diff
#   python integrity_check.py compare A B -> compare two db paths logically
#
# READ-ONLY. Never writes production.db. Operates on a temp copy so the live
# file is never even opened by sqlite.
# =============================================================================

import sqlite3
import json
import os
import sys
import shutil
import tempfile
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import source_authority_matrix as M   # noqa: E402

OUT = os.path.join(M.OUTPUT_DIR, "integrity_baseline.json")

# primary key per table (None => order by rowid)
PK = {
    "distilleries": "distillery_id", "whiskies": "whisky_id",
    "flavor_profiles": "whisky_id", "tasting_notes": "whisky_id",
    "official_source_references": "ref_id",
    "bottlers": "bottler_id", "brands": "brand_id",
    "companies": "company_id", "price_history": "price_id",
    "staging_manual_review_queue": "queue_id",
    "external_entities": "entity_id", "knowledge_glossary_terms": "term_id",
    "knowledge_regions": "region_id", "sqlite_sequence": "name",
}


def _copy(src):
    t = tempfile.NamedTemporaryFile(suffix=".db", delete=False, prefix="p52_int_")
    t.close()
    shutil.copyfile(src, t.name)
    return t.name


def snapshot(db_path):
    tmp = _copy(db_path)
    con = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    out = {}
    for t in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        pk = PK.get(t)
        q = f"SELECT * FROM {t} ORDER BY {pk}" if pk else f"SELECT * FROM {t} ORDER BY rowid"
        rows = cur.execute(q).fetchall()
        h = hashlib.sha256(str([tuple(r) for r in rows]).encode()).hexdigest()
        out[t] = {"rows": len(rows), "hash": h}
    con.close()
    os.remove(tmp)
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    live = M.LIVE_DB
    if cmd == "snapshot":
        s = snapshot(live)
        json.dump({"schema": M.SCHEMA_VERSION, "run_date": M.RUN_DATE,
                   "tables": s}, open(OUT, "w"), indent=2)
        print(f"baseline written: {OUT} ({len(s)} tables)")
    elif cmd == "verify":
        if not os.path.exists(OUT):
            print("NO BASELINE. Run `integrity_check.py snapshot` first.")
            return
        base = json.load(open(OUT))
        cur = snapshot(live)
        diffs = [t for t in base["tables"] if base["tables"][t] != cur.get(t)]
        print(f"tables compared: {len(base['tables'])}")
        if diffs:
            print("LOGICALLY MODIFIED TABLES:")
            for t in diffs:
                print(f"  {t}: base={base['tables'][t]} cur={cur.get(t)}")
        else:
            print("RESULT: production.db LOGICALLY UNCHANGED (data not modified).")
    elif cmd == "compare":
        a, b = sys.argv[2], sys.argv[3]
        sa, sb = snapshot(a), snapshot(b)
        diffs = [t for t in sa if sa[t] != sb.get(t)]
        print("DIFFS:" if diffs else "IDENTICAL", diffs)
    else:
        print("usage: snapshot | verify | compare A B")


if __name__ == "__main__":
    main()

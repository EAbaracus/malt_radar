import csv
import sqlite3
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CSV = ROOT / "data/manual_sources/books/review_csv/book_tasting_note_staging_dry_run_preview.csv"
DB_PATH = ROOT / "output/import/production.db"
BACKUP_PATH = ROOT / "output/import/production_before_12t_book_staging_apply.db"

REPORT_MD = ROOT / "output/reports/12t_book_tasting_note_staging_apply_report.md"
GATE_TXT = ROOT / "output/reports/12t_book_tasting_note_staging_apply_gate.txt"

def get_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

stats = {
    "staging_before": 0,
    "staging_after": 0,
    "tasting_before": 0,
    "tasting_after": 0,
    "flavor_before": 0,
    "flavor_after": 0,
    "input_rows": 0,
    "inserted": 0,
    "blocked": 0,
}

# 1. Backup DB
shutil.copy2(DB_PATH, BACKUP_PATH)
backup_hash = get_hash(BACKUP_PATH)

# 2. Open DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def get_count(table):
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]
    except:
        return 0

stats["staging_before"] = get_count("staging_tasting_notes")
stats["tasting_before"] = get_count("tasting_notes")
stats["flavor_before"] = get_count("flavor_profiles")

# Schema inspection
cur.execute("PRAGMA table_info(staging_tasting_notes)")
staging_cols = [r["name"] for r in cur.fetchall()]

# Valid Whiskies
cur.execute("SELECT whisky_id FROM whiskies")
db_whiskies = {r[0] for r in cur.fetchall()}

# Existing
existing_staging = set()
if "whisky_id" in staging_cols and "source_system" in staging_cols:
    url_col = "source_url" if "source_url" in staging_cols else "source_name" if "source_name" in staging_cols else None
    if url_col:
        cur.execute(f"SELECT whisky_id, {url_col} FROM staging_tasting_notes WHERE source_system='local_book_anchor'")
        for r in cur.fetchall():
            existing_staging.add(f"{r[0]}_{r[1]}")

cur.execute("PRAGMA table_info(tasting_notes)")
tn_cols = [r["name"] for r in cur.fetchall()]
existing_tasting = set()
if "whisky_id" in tn_cols and "source_system" in tn_cols:
    url_col_tn = "source_url" if "source_url" in tn_cols else "source_name" if "source_name" in tn_cols else None
    if url_col_tn:
        try:
            cur.execute(f"SELECT whisky_id, {url_col_tn} FROM tasting_notes WHERE source_system='local_book_anchor'")
            for r in cur.fetchall():
                existing_tasting.add(f"{r[0]}_{r[1]}")
        except: pass

with INPUT_CSV.open("r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("import_status") != "planned_insert":
            continue
        stats["input_rows"] += 1
        wid = row.get("matched_whisky_id", "")
        source_file = row.get("source_file", "")
        dedup_key = f"{wid}_{source_file}"
        
        if wid not in db_whiskies or dedup_key in existing_staging or dedup_key in existing_tasting:
            stats["blocked"] += 1
            continue
            
        # Build insert
        insert_dict = {
            "whisky_id": wid,
            "text": row.get("candidate_text_snippet", ""),
            "source_system": "local_book_anchor",
            "approval_status": "staging_pending_review",
            "created_at": datetime.now().isoformat()
        }
        if "source_url" in staging_cols:
            insert_dict["source_url"] = source_file
        elif "source_name" in staging_cols:
            insert_dict["source_name"] = source_file
            
        if "extraction_confidence" in staging_cols:
            insert_dict["extraction_confidence"] = float(row.get("extraction_confidence", 0))
            
        cols = []
        vals = []
        for k, v in insert_dict.items():
            if k in staging_cols:
                cols.append(k)
                vals.append(v)
                
        placeholders = ",".join(["?"] * len(vals))
        col_str = ",".join(cols)
        cur.execute(f"INSERT INTO staging_tasting_notes ({col_str}) VALUES ({placeholders})", vals)
        stats["inserted"] += 1
        existing_staging.add(dedup_key)

conn.commit()

stats["staging_after"] = get_count("staging_tasting_notes")
stats["tasting_after"] = get_count("tasting_notes")
stats["flavor_after"] = get_count("flavor_profiles")

conn.close()

final_hash = get_hash(DB_PATH)

gate = "NO-GO"
if stats["inserted"] == 27 and stats["blocked"] == 0:
    gate = "GO"
elif stats["inserted"] > 0 and stats["blocked"] > 0:
    gate = "WARN_GO_PARTIAL"
    
if stats["tasting_before"] != stats["tasting_after"] or stats["flavor_before"] != stats["flavor_after"]:
    gate = "NO-GO_MODIFIED_PRODUCTION_TABLES"

lines = []
lines.append("# 12T Book Tasting Note Staging Apply Report")
lines.append("")
lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
lines.append("")
lines.append("## DB Hashes")
lines.append(f"- backup_db_hash: {backup_hash}")
lines.append(f"- final_db_hash: {final_hash}")
lines.append("")
lines.append("## Stats")
for k, v in stats.items():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Gate Decision")
lines.append(f"- gate: **{gate}**")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

GATE_TXT.write_text(
    f"{gate}\nINSERTED={stats['inserted']}\nBLOCKED={stats['blocked']}\n",
    encoding="utf-8"
)
GATE_TXT.write_text(
    "\n"
    "Estimated API Cost: $0.00\n"
    "Actual API Cost: $0.00\n"
    "Local Compute Used: Yes\n"
    "Fully Local Execution: Yes\n",
    encoding="utf-8"
)

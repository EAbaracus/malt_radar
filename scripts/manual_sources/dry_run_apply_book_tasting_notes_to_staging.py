import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_CSV = ROOT / "data/manual_sources/books/review_csv/book_anchored_tasting_note_accept_preview.csv"
DB_PATH = ROOT / "output/import/production.db"

OUT_CSV = ROOT / "data/manual_sources/books/review_csv/book_tasting_note_staging_dry_run_preview.csv"
REPORT_MD = ROOT / "output/reports/12s_book_tasting_note_staging_dry_run_report.md"
GATE_TXT = ROOT / "output/reports/12s_book_tasting_note_staging_dry_run_gate.txt"

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

stats = {
    "input_rows": 0,
    "planned_insert": 0,
    "blocked": 0,
    "missing_fk": 0,
    "duplicate_existing_tasting_note": 0,
    "duplicate_existing_staging": 0,
    "duplicate_input": 0,
    "snippet_too_long": 0
}

source_files = Counter()
planned_whiskies = Counter()

# Fetch DB data for checks
db_whiskies = set()
existing_staging = set()
existing_tasting_notes = set()

if DB_PATH.exists():
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        
        # Check whiskies
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whiskies'")
        if cur.fetchone():
            cur.execute("SELECT whisky_id FROM whiskies")
            db_whiskies = {row[0] for row in cur.fetchall()}
            
        # Check staging_tasting_notes
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staging_tasting_notes'")
        if cur.fetchone():
            try:
                cur.execute("SELECT whisky_id, source_url FROM staging_tasting_notes WHERE source_system='local_book_anchor'")
                for r in cur.fetchall():
                    existing_staging.add(f"{r[0]}_{r[1]}")
            except: pass
            
        # Check tasting_notes
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasting_notes'")
        if cur.fetchone():
            try:
                cur.execute("SELECT whisky_id, source_url FROM tasting_notes WHERE source_system='local_book_anchor'")
                for r in cur.fetchall():
                    existing_tasting_notes.add(f"{r[0]}_{r[1]}")
            except: pass
            
        conn.close()
    except Exception as e:
        print(f"Warning: DB read error: {e}")

processed = []
seen_in_input = set()

if INPUT_CSV.exists():
    with INPUT_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["input_rows"] += 1
            wid = row.get("matched_whisky_id", "")
            snippet = row.get("candidate_text_snippet", "")
            source_file = row.get("source_file", "")
            sha256 = row.get("source_sha256", "")
            
            import_status = "planned_insert"
            block_reason = ""
            
            dedup_key = f"{wid}_{source_file}"
            
            if not wid:
                import_status = "blocked"
                block_reason = "missing_whisky_id"
            elif wid not in db_whiskies:
                import_status = "blocked"
                block_reason = "missing_fk"
                stats["missing_fk"] += 1
            elif not snippet:
                import_status = "blocked"
                block_reason = "missing_snippet"
            elif not source_file:
                import_status = "blocked"
                block_reason = "missing_source_file"
            elif len(snippet) > 280:
                import_status = "blocked"
                block_reason = "snippet_too_long"
                stats["snippet_too_long"] += 1
            elif dedup_key in existing_tasting_notes:
                import_status = "blocked"
                block_reason = "duplicate_existing_tasting_note"
                stats["duplicate_existing_tasting_note"] += 1
            elif dedup_key in existing_staging:
                import_status = "blocked"
                block_reason = "duplicate_existing_staging"
                stats["duplicate_existing_staging"] += 1
            elif dedup_key in seen_in_input:
                import_status = "blocked"
                block_reason = "duplicate_input"
                stats["duplicate_input"] += 1
            
            if import_status == "planned_insert":
                stats["planned_insert"] += 1
                seen_in_input.add(dedup_key)
                source_files[source_file] += 1
                planned_whiskies[row.get("matched_whisky_name", "")] += 1
            else:
                stats["blocked"] += 1
                
            out_row = dict(row)
            out_row["source_system"] = "local_book_anchor"
            out_row["approval_status"] = "staging_pending_review"
            out_row["import_status"] = import_status
            out_row["block_reason"] = block_reason
            processed.append(out_row)

if processed:
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=processed[0].keys())
        w.writeheader()
        w.writerows(processed)

gate = "NO-GO"
if stats["planned_insert"] >= 10:
    if stats["blocked"] == 0:
        gate = "GO_FOR_STAGING_APPLY"
    else:
        gate = "WARN_GO_PARTIAL_STAGING_APPLY"
elif stats["planned_insert"] > 0:
    gate = "WARN_GO_SMALL_BATCH"

prod_gate = "PRODUCTION_IMPORT_NO-GO"

lines = []
lines.append("# 12S Book Tasting Note Staging Dry Run Report")
lines.append("")
lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
lines.append("")
lines.append("## Stats")
for k, v in stats.items():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Source File Distribution (Planned)")
for s, c in source_files.most_common():
    lines.append(f"- `{s}`: {c}")
lines.append("")
lines.append("## Planned Whisky List")
for w, c in planned_whiskies.most_common(15):
    lines.append(f"- {w}: {c}")
lines.append("")
lines.append("## Gate Decision")
lines.append(f"- staging_apply_gate: **{gate}**")
lines.append(f"- production_import_gate: **{prod_gate}**")
lines.append("")
lines.append("## Output Files")
lines.append(f"- `{OUT_CSV}`")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

GATE_TXT.write_text(
    f"{gate}\n{prod_gate}\nPLANNED={stats['planned_insert']}\nBLOCKED={stats['blocked']}\n",
    encoding="utf-8"
)

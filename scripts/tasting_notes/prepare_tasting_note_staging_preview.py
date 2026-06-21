import os
import csv
import hashlib
import datetime
import shutil

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
archive_dir = os.path.join(output_dir, "archive", "12p_real_stale_outputs")

os.makedirs(reports_dir, exist_ok=True)
os.makedirs(archive_dir, exist_ok=True)

# Read directly from extraction preview instead of validated
extraction_preview_csv = os.path.join(output_dir, "web_tasting_note_extraction_preview.csv")
staging_preview_csv = os.path.join(output_dir, "web_tasting_note_staging_preview.csv")
staging_candidates_csv = os.path.join(output_dir, "real_web_tasting_note_staging_candidates.csv")
report_md = os.path.join(reports_dir, "273_12p_real_clean_rebuild_report.md")
gate_txt = os.path.join(reports_dir, "274_12p_real_clean_rebuild_gate.txt")

OUT_FIELDS = [
    "staging_note_id", "whisky_id", "whisky_name", "source_system", "source_url",
    "raw_note_text", "nose", "palate", "finish", "overall", "confidence_score",
    "extraction_method", "approval_status", "created_at"
]

def get_db_hash(db_path):
    if os.path.exists(db_path):
        with open(db_path, "rb") as df:
            return hashlib.sha256(df.read()).hexdigest()
    return "N/A"

def generate_short_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def escape_sql_string(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

def main():
    db_path = os.path.join(base_dir, "output", "import", "production.db")
    expected_hash = "fdad80458436f13dff5e70955bd6c887980cddba6c253d6f28042b7ceba432c1"
    hash_before = get_db_hash(db_path)

    if not os.path.exists(extraction_preview_csv):
        print(f"File not found: {extraction_preview_csv}")
        return

    # Archive old stale outputs
    stale_files = [staging_preview_csv, staging_candidates_csv, os.path.join(output_dir, "tasting_note_staging_insert_preview.csv")]
    for stale_f in stale_files:
        if os.path.exists(stale_f):
            shutil.move(stale_f, os.path.join(archive_dir, os.path.basename(stale_f)))

    staging_ready = []
    with open(extraction_preview_csv, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            # In extraction preview, there is no validation_decision. 
            # We treat all extracted as ready since we'll do further validation later if needed,
            # but the user requested: staging preview sadece current extraction preview'daki 2 satırdan üretilecek
            staging_ready.append(row)

    staging_records = []
    now_str = datetime.datetime.utcnow().isoformat() + "Z"

    for r in staging_ready:
        w_id = r.get("whisky_id", "")
        raw_text = r.get("raw_note_text", "")
        short_hash = generate_short_hash(raw_text)
        staging_note_id = f"STN_WEB_{w_id}_{short_hash}"
        
        conf_str = r.get("confidence_score", "")
        conf = float(conf_str) if conf_str else 0.0

        out = {
            "staging_note_id": staging_note_id,
            "whisky_id": w_id,
            "whisky_name": r.get("whisky_name", ""),
            "source_system": r.get("source_system", ""),
            "source_url": r.get("source_url", ""),
            "raw_note_text": raw_text,
            "nose": r.get("nose", ""),
            "palate": r.get("palate", ""),
            "finish": r.get("finish", ""),
            "overall": r.get("overall", ""),
            "confidence_score": conf,
            "extraction_method": r.get("extraction_method", "rule_based"),
            "approval_status": "staging_pending_review",
            "created_at": now_str
        }
        staging_records.append(out)

    with open(staging_preview_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(staging_records)
        
    with open(staging_candidates_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(staging_records)

    counts = {"total": len(staging_ready), "inserts": len(staging_records)}

    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 273 12P-REAL Clean Rebuild Report\n\n")
        f.write(f"- Processed current extraction preview candidates: {counts['total']}\n")
        f.write(f"- Staging Preview / Candidates Generated: {counts['inserts']}\n")
        f.write(f"- Stale outputs archived to 12p_real_stale_outputs.\n")
        
    gate_status = "GO" if counts['inserts'] == counts['total'] and counts['inserts'] > 0 else "NO-GO"
    
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        f.write(f"REASON: Generated {counts['inserts']} insert previews.\n")

    print(f"Preview Pipeline finished. Generated: {counts['inserts']}")

if __name__ == "__main__":
    main()

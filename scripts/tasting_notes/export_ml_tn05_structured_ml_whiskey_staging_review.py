import sqlite3
import csv
import json
import hashlib
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    qa_csv = root / "data" / "output" / "ml_tn04_structured_ml_whiskey_staging_qa.csv"
    out_csv = root / "data" / "output" / "ml_tn05_structured_ml_whiskey_staging_review_export.csv"
    report_out = root / "output" / "reports" / "ml_tn05_structured_ml_whiskey_staging_review_export_report.md"
    gate_out = root / "output" / "reports" / "ml_tn05_structured_ml_whiskey_staging_review_export_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(staging_tasting_notes)")
    staging_cols = [row[1] for row in cur.fetchall()]
    col_idx = {name: i for i, name in enumerate(staging_cols)}
    
    cur.execute("SELECT * FROM staging_tasting_notes WHERE source_system = 'structured_ml_whiskey'")
    staging_rows = cur.fetchall()
    
    staging_dict = {}
    for row in staging_rows:
        sid = str(row[col_idx.get("staging_note_id", -1)] if "staging_note_id" in col_idx else row[0])
        staging_dict[sid] = row
        
    metrics = {
        "qa_input_count": 0,
        "exported_count": 0,
        "skipped_count": 0
    }
    
    out_rows = []
    
    if qa_csv.exists():
        with open(qa_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics["qa_input_count"] += 1
                
                qa_status = row.get("qa_status")
                sid = str(row.get("staging_note_id"))
                
                if qa_status == "qa_pass" and sid in staging_dict:
                    db_row = staging_dict[sid]
                    conclusion = db_row[col_idx.get("conclusion", -1)] if "conclusion" in col_idx else ""
                    import_rec_str = db_row[col_idx.get("import_recommendation", -1)] if "import_recommendation" in col_idx else ""
                    
                    candidate_name = ""
                    matched_whisky_name = ""
                    match_score = ""
                    source_id = ""
                    
                    if import_rec_str:
                        try:
                            rec_json = json.loads(import_rec_str)
                            candidate_name = rec_json.get("candidate_name", "")
                            matched_whisky_name = rec_json.get("matched_whisky_name", "")
                            match_score = rec_json.get("match_score", "")
                            source_id = rec_json.get("source_id", "")
                        except:
                            pass
                            
                    out_rows.append({
                        "staging_note_id": sid,
                        "whisky_id": row.get("whisky_id"),
                        "source_id": source_id,
                        "candidate_name": candidate_name,
                        "matched_whisky_name": matched_whisky_name,
                        "match_score": match_score,
                        "conclusion_summary": conclusion,
                        "qa_status": qa_status,
                        "review_decision": "approve",
                        "reviewer_notes": ""
                    })
                    metrics["exported_count"] += 1
                else:
                    metrics["skipped_count"] += 1
                    
    if out_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["exported_count"] > 0 and metrics["skipped_count"] == 0:
        gate_decision = "GO"
    elif metrics["exported_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-TN-05 Structured ML Whiskey Staging Export Report

## Metrics
- **QA Input Count:** {metrics["qa_input_count"]}
- **Exported Count:** {metrics["exported_count"]}
- **Skipped Count:** {metrics["skipped_count"]}

## Security & Verification
- **Production DB Modified:** {'true' if hash_before != hash_after else 'false'}
- **Production DB Hash:** {hash_after}

Gate decision: **{gate_decision}**
"""
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)
        
if __name__ == "__main__":
    main()

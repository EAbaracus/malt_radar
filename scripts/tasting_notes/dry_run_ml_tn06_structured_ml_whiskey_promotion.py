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
    
    in_csv = root / "data" / "output" / "ml_tn05_structured_ml_whiskey_staging_review_export.csv"
    out_csv = root / "data" / "output" / "ml_tn06_structured_ml_whiskey_promotion_dry_run.csv"
    report_out = root / "output" / "reports" / "ml_tn06_structured_ml_whiskey_promotion_dry_run_report.md"
    gate_out = root / "output" / "reports" / "ml_tn06_structured_ml_whiskey_promotion_dry_run_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id FROM whiskies")
    all_whisky_ids = set(str(row[0]) for row in cur.fetchall())
    
    cur.execute("SELECT whisky_id FROM tasting_notes WHERE source_system = 'structured_ml_whiskey'")
    existing_tasting_notes_ids = set(str(row[0]) for row in cur.fetchall())
    
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
        "input_count": 0,
        "planned_promote_count": 0,
        "blocked_count": 0,
        "missing_in_staging": 0,
        "wrong_source_system": 0,
        "missing_fk": 0,
        "missing_or_unsafe_summary": 0,
        "duplicate_in_production": 0,
        "not_pending": 0,
        "not_approved_in_review": 0
    }
    
    out_rows = []
    
    if in_csv.exists():
        with open(in_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics["input_count"] += 1
                
                sid = row.get("staging_note_id")
                review_dec = row.get("review_decision")
                wid = row.get("whisky_id")
                
                planned_status = "planned"
                reasons = []
                
                if review_dec != "approve":
                    planned_status = "blocked"
                    reasons.append("not_approved_in_review")
                    metrics["not_approved_in_review"] += 1
                    
                if sid not in staging_dict:
                    planned_status = "blocked"
                    reasons.append("missing_in_staging")
                    metrics["missing_in_staging"] += 1
                else:
                    db_row = staging_dict[sid]
                    db_src = db_row[col_idx["source_system"]]
                    db_wid = str(db_row[col_idx["whisky_id"]])
                    db_status = db_row[col_idx.get("status", -1)] if "status" in col_idx else ""
                    db_summary = db_row[col_idx.get("conclusion", -1)] if "conclusion" in col_idx else ""
                    if not db_summary: db_summary = ""
                    
                    if db_src != "structured_ml_whiskey":
                        planned_status = "blocked"
                        reasons.append("wrong_source_system")
                        metrics["wrong_source_system"] += 1
                        
                    if db_wid not in all_whisky_ids:
                        planned_status = "blocked"
                        reasons.append("missing_fk")
                        metrics["missing_fk"] += 1
                        
                    if not db_summary or len(db_summary) < 30 or len(db_summary) > 350:
                        planned_status = "blocked"
                        reasons.append("missing_or_unsafe_summary")
                        metrics["missing_or_unsafe_summary"] += 1
                        
                    if db_wid in existing_tasting_notes_ids:
                        planned_status = "blocked"
                        reasons.append("duplicate_in_production")
                        metrics["duplicate_in_production"] += 1
                        
                    if "pending" not in (db_status or "").lower():
                        planned_status = "blocked"
                        reasons.append("not_pending")
                        metrics["not_pending"] += 1
                        
                if planned_status == "planned":
                    metrics["planned_promote_count"] += 1
                else:
                    metrics["blocked_count"] += 1
                    
                out_rows.append({
                    "staging_note_id": sid,
                    "whisky_id": wid,
                    "candidate_name": row.get("candidate_name"),
                    "matched_whisky_name": row.get("matched_whisky_name"),
                    "planned_status": planned_status,
                    "block_reason": " | ".join(reasons),
                    "review_decision": review_dec
                })
                
    if out_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["planned_promote_count"] > 0 and metrics["blocked_count"] == 0:
        gate_decision = "GO"
    elif metrics["planned_promote_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-TN-06 Structured ML Whiskey Promotion Dry Run Report

## Metrics
- **Input Count:** {metrics["input_count"]}
- **Planned Promote:** {metrics["planned_promote_count"]}
- **Blocked:** {metrics["blocked_count"]}

## Block Reasons Details
- **Missing in Staging:** {metrics["missing_in_staging"]}
- **Wrong Source System:** {metrics["wrong_source_system"]}
- **Missing FK:** {metrics["missing_fk"]}
- **Missing or Unsafe Summary:** {metrics["missing_or_unsafe_summary"]}
- **Duplicate in Production:** {metrics["duplicate_in_production"]}
- **Not Pending:** {metrics["not_pending"]}
- **Not Approved in Review:** {metrics["not_approved_in_review"]}

## Security & Verification
- **DB Modified:** {'true' if hash_before != hash_after else 'false'}
- **Production DB Hash:** {hash_after}

Gate decision: **{gate_decision}**
"""
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)
        
if __name__ == "__main__":
    main()

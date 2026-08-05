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
    
    in_csv = root / "data" / "output" / "structured_ml_whiskey_source" / "high_match_safe_preview.csv"
    out_csv = root / "data" / "output" / "ml_tn02_structured_ml_whiskey_tasting_note_dry_run.csv"
    report_out = root / "output" / "reports" / "ml_tn02_structured_ml_whiskey_tasting_note_dry_run_report.md"
    gate_out = root / "output" / "reports" / "ml_tn02_structured_ml_whiskey_tasting_note_dry_run_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id FROM whiskies")
    all_whisky_ids = set(row[0] for row in cur.fetchall())
    
    cur.execute("SELECT whisky_id FROM tasting_notes WHERE source_system = 'structured_ml_whiskey'")
    existing_tasting_notes_ids = set(row[0] for row in cur.fetchall())
    
    try:
        cur.execute("SELECT whisky_id FROM staging_tasting_notes WHERE source_system = 'structured_ml_whiskey'")
        existing_staging_ids = set(row[0] for row in cur.fetchall())
    except:
        existing_staging_ids = set()
    
    cur.execute("SELECT COUNT(*) FROM tasting_notes")
    total_tasting_notes = cur.fetchone()[0]
    
    metrics = {
        "input_candidate_count": 0,
        "planned_count": 0,
        "blocked_count": 0,
        "manual_review_count": 0,
        "missing_fk_count": 0,
        "duplicate_tasting_note_count": 0,
        "duplicate_staging_note_count": 0,
        "missing_description_count": 0,
        "unsafe_match_confidence_count": 0,
        "too_short_or_generic_text_count": 0
    }
    
    out_rows = []
    
    if not in_csv.exists():
        with open(gate_out, "w", encoding="utf-8") as f:
            f.write("NO_GO")
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        with open(report_out, "w", encoding="utf-8") as f:
            f.write("Input CSV not found.")
        return
        
    detected_headers = []
    
    with open(in_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        detected_headers = reader.fieldnames
        for row in reader:
            metrics["input_candidate_count"] += 1
            
            wid = row.get("whisky_id")
            candidate_name = row.get("src_name")
            matched_name = row.get("tgt_name")
            match_score = row.get("score")
            qa_status = row.get("qa_status")
            desc = row.get("description", "").strip()
            
            planned_status = "planned"
            reasons = []
            
            if not wid or wid not in all_whisky_ids:
                planned_status = "blocked"
                reasons.append("missing_whisky_fk")
                metrics["missing_fk_count"] += 1
                
            if wid in existing_tasting_notes_ids:
                if planned_status != "blocked": planned_status = "manual_review"
                reasons.append("duplicate_tasting_note")
                metrics["duplicate_tasting_note_count"] += 1
                
            if wid in existing_staging_ids:
                if planned_status != "blocked": planned_status = "manual_review"
                reasons.append("duplicate_staging_note")
                metrics["duplicate_staging_note_count"] += 1
                
            if not desc:
                planned_status = "blocked"
                reasons.append("missing_description")
                metrics["missing_description_count"] += 1
            elif len(desc) < 30:
                planned_status = "blocked"
                reasons.append("too_short_or_generic_text")
                metrics["too_short_or_generic_text_count"] += 1
                
            if qa_status != "safe":
                if planned_status != "blocked": planned_status = "manual_review"
                reasons.append("unsafe_match_confidence")
                metrics["unsafe_match_confidence_count"] += 1
                
            safe_summary = desc[:300] + "..." if len(desc) > 300 else desc
            
            if planned_status == "planned":
                metrics["planned_count"] += 1
            elif planned_status == "blocked":
                metrics["blocked_count"] += 1
            else:
                metrics["manual_review_count"] += 1
                
            out_rows.append({
                "source_id": candidate_name,
                "matched_whisky_id": wid,
                "candidate_name": candidate_name,
                "matched_whisky_name": matched_name,
                "match_score": match_score,
                "planned_status": planned_status,
                "block_reason": " | ".join(reasons),
                "has_description": "true" if desc else "false",
                "description_length": len(desc),
                "copyright_safe_summary": safe_summary,
                "source_system": "structured_ml_whiskey",
                "review_status": "pending_review" if planned_status != "blocked" else "rejected"
            })
            
    if out_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    total_whiskies = len(all_whisky_ids)
    est_total = total_tasting_notes + metrics["planned_count"]
    est_cov = est_total / total_whiskies if total_whiskies else 0
    
    gate_decision = "NO_GO"
    if metrics["planned_count"] > 0 and metrics["blocked_count"] == 0 and metrics["manual_review_count"] == 0:
        gate_decision = "GO"
    elif metrics["planned_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-TN-02 Structured ML Whiskey Tasting Note Dry Run Report

## File Discovery
- **Detected Input File:** {in_csv.name}
- **Detected Headers:** {", ".join(detected_headers)}

## Metrics
- **Input Candidate Count:** {metrics["input_candidate_count"]}
- **Planned:** {metrics["planned_count"]}
- **Blocked:** {metrics["blocked_count"]}
- **Manual Review:** {metrics["manual_review_count"]}

## Block Reasons Details
- **Missing FK:** {metrics["missing_fk_count"]}
- **Missing Description:** {metrics["missing_description_count"]}
- **Duplicate Tasting Note:** {metrics["duplicate_tasting_note_count"]}
- **Duplicate Staging Note:** {metrics["duplicate_staging_note_count"]}
- **Unsafe Match Confidence:** {metrics["unsafe_match_confidence_count"]}
- **Too Short Or Generic Text:** {metrics["too_short_or_generic_text_count"]}

## Coverage Impact
- **Estimated Total Tasting Notes After Planned:** {est_total}
- **Estimated Tasting Note Coverage After Planned:** {est_cov:.2%}

## Security & Verification
- **DB Modified:** {'true' if hash_before != hash_after else 'false'}
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

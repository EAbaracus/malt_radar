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
    out_csv = root / "data" / "output" / "ml_fp02_structured_ml_whiskey_flavor_profile_dry_run.csv"
    report_out = root / "output" / "reports" / "ml_fp02_structured_ml_whiskey_flavor_profile_dry_run_report.md"
    gate_out = root / "output" / "reports" / "ml_fp02_structured_ml_whiskey_flavor_profile_dry_run_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id FROM whiskies")
    all_whisky_ids = set(row[0] for row in cur.fetchall())
    
    cur.execute("SELECT whisky_id FROM flavor_profiles")
    existing_profile_ids = set(row[0] for row in cur.fetchall())
    
    metrics = {
        "input_candidate_count": 0,
        "planned_count": 0,
        "blocked_count": 0,
        "manual_review_count": 0,
        "missing_fk_count": 0,
        "existing_profile_count": 0,
        "invalid_score_count": 0,
        "duplicate_count": 0,
        "missing_component_score": 0,
        "missing_source_payload": 0
    }
    
    out_rows = []
    seen_ids = set()
    
    if in_csv.exists():
        with open(in_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics["input_candidate_count"] += 1
                
                wid = row.get("whisky_id")
                
                candidate_name = row.get("src_name")
                matched_name = row.get("tgt_name")
                match_score = row.get("score")
                
                planned_status = "planned"
                reasons = []
                
                if not wid:
                    planned_status = "blocked"
                    reasons.append("missing_whisky_fk")
                    metrics["missing_fk_count"] += 1
                elif wid not in all_whisky_ids:
                    planned_status = "blocked"
                    reasons.append("missing_whisky_fk")
                    metrics["missing_fk_count"] += 1
                    
                if wid in existing_profile_ids:
                    planned_status = "blocked"
                    reasons.append("existing_flavor_profile")
                    metrics["existing_profile_count"] += 1
                    
                if wid in seen_ids and wid is not None:
                    planned_status = "blocked"
                    reasons.append("duplicate_candidate")
                    metrics["duplicate_count"] += 1
                if wid:
                    seen_ids.add(wid)
                    
                c1 = row.get("sweet")
                c2 = row.get("smoky")
                c3 = row.get("peaty")
                
                if not c1 and not c2 and not c3:
                    planned_status = "blocked"
                    reasons.append("missing_component_score")
                    metrics["missing_component_score"] += 1
                    
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
                    "sweet": "",
                    "smoky": "",
                    "peaty": "",
                    "fruity": "",
                    "spicy": "",
                    "oaky": "",
                    "floral": "",
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
    curr_profiles = len(existing_profile_ids)
    est_total = curr_profiles + metrics["planned_count"]
    est_cov = est_total / total_whiskies if total_whiskies else 0
    
    gate_decision = "NO_GO"
    if metrics["planned_count"] > 0 and metrics["blocked_count"] == 0 and metrics["manual_review_count"] == 0:
        gate_decision = "GO"
    elif metrics["planned_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-FP-02 Structured ML Whiskey Flavor Profile Dry Run Report

## Metrics
- **Input Candidate Count:** {metrics["input_candidate_count"]}
- **Planned:** {metrics["planned_count"]}
- **Blocked:** {metrics["blocked_count"]}
- **Manual Review:** {metrics["manual_review_count"]}

## Block Reasons Details
- **Missing FK:** {metrics["missing_fk_count"]}
- **Existing Profile:** {metrics["existing_profile_count"]}
- **Invalid Score:** {metrics["invalid_score_count"]}
- **Missing Score:** {metrics["missing_component_score"]}
- **Duplicate Candidate:** {metrics["duplicate_count"]}
- **Missing Source Payload:** {metrics["missing_source_payload"]}

## Coverage Impact
- **Estimated Total Flavor Profiles After Planned:** {est_total}
- **Estimated Coverage After Planned:** {est_cov:.2%}

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

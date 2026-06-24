import sqlite3
import csv
from pathlib import Path

def get_hash(filepath):
    import hashlib
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_csv = root / "data" / "output" / "nb_fp03_staging_book_flavor_profiles_review_export.csv"
    out_csv = root / "data" / "output" / "nb_fp04_book_flavor_profile_promotion_dry_run.csv"
    report_out = root / "output" / "reports" / "nb_fp04_book_flavor_profile_promotion_dry_run_report.md"
    gate_out = root / "output" / "reports" / "nb_fp04_book_flavor_profile_promotion_dry_run_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id FROM whiskies")
    all_whisky_ids = set(str(row[0]) for row in cur.fetchall())
    
    cur.execute("SELECT whisky_id FROM flavor_profiles")
    existing_flavor_profiles_ids = set(str(row[0]) for row in cur.fetchall())
    
    cur.execute("PRAGMA table_info(staging_book_flavor_profiles)")
    staging_cols = [row[1] for row in cur.fetchall()]
    col_idx = {name: i for i, name in enumerate(staging_cols)}
    
    cur.execute("SELECT * FROM staging_book_flavor_profiles")
    staging_rows = cur.fetchall()
    
    staging_dict = {}
    for row in staging_rows:
        sid = str(row[col_idx.get("staging_id", -1)] if "staging_id" in col_idx else row[0])
        staging_dict[sid] = row
        
    metrics = {
        "input_count": 0,
        "planned_promote_count": 0,
        "blocked_count": 0,
        "missing_in_staging": 0,
        "missing_fk": 0,
        "duplicate_in_production": 0,
        "not_approved_in_review": 0,
        "invalid_score": 0,
        "scale_inconsistent": 0,
        "light_rich_conflict": 0
    }
    
    out_rows = []
    
    if in_csv.exists():
        with open(in_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics["input_count"] += 1
                
                sid = row.get("staging_profile_id")
                review_dec = row.get("review_decision")
                wid = row.get("whisky_id")
                score_scale = row.get("score_scale_detected", "")
                
                planned_status = "planned"
                reasons = []
                
                if review_dec != "approve_candidate":
                    planned_status = "blocked"
                    reasons.append("not_approved_in_review")
                    metrics["not_approved_in_review"] += 1
                    
                if sid not in staging_dict:
                    planned_status = "blocked"
                    reasons.append("missing_in_staging")
                    metrics["missing_in_staging"] += 1
                else:
                    if wid not in all_whisky_ids:
                        planned_status = "blocked"
                        reasons.append("missing_fk")
                        metrics["missing_fk"] += 1
                        
                    if wid in existing_flavor_profiles_ids:
                        planned_status = "blocked"
                        reasons.append("duplicate_in_production")
                        metrics["duplicate_in_production"] += 1
                        
                    if score_scale == "invalid":
                        planned_status = "blocked"
                        reasons.append("invalid_score")
                        metrics["invalid_score"] += 1
                        
                    if row.get("light_rich_conflict") == "true":
                        planned_status = "blocked"
                        reasons.append("light_rich_conflict")
                        metrics["light_rich_conflict"] += 1
                        
                if planned_status == "planned":
                    metrics["planned_promote_count"] += 1
                else:
                    metrics["blocked_count"] += 1
                    
                out_rows.append({
                    "staging_profile_id": sid,
                    "whisky_id": wid,
                    "whisky_name": row.get("whisky_name"),
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
    if metrics["planned_promote_count"] == 2 and metrics["blocked_count"] == 0:
        gate_decision = "GO"
    elif metrics["planned_promote_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# NB-FP-04 Staging Book Flavor Profiles Promotion Dry Run Report

## Metrics
- **Input Count:** {metrics["input_count"]}
- **Planned Promote:** {metrics["planned_promote_count"]}
- **Blocked:** {metrics["blocked_count"]}

## Block Reasons Details
- **Missing in Staging:** {metrics["missing_in_staging"]}
- **Missing FK:** {metrics["missing_fk"]}
- **Duplicate in Production:** {metrics["duplicate_in_production"]}
- **Not Approved in Review:** {metrics["not_approved_in_review"]}
- **Invalid Score:** {metrics["invalid_score"]}
- **Light/Rich Conflict:** {metrics["light_rich_conflict"]}

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

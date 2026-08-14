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
    
    qa_csv = root / "data" / "output" / "nb_fp02_staging_book_flavor_profiles_qa.csv"
    out_csv = root / "data" / "output" / "nb_fp03_staging_book_flavor_profiles_review_export.csv"
    report_out = root / "output" / "reports" / "nb_fp03_staging_book_flavor_profiles_review_export_report.md"
    gate_out = root / "output" / "reports" / "nb_fp03_staging_book_flavor_profiles_review_export_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
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
                review_dec = row.get("review_decision")
                sid = str(row.get("staging_profile_id"))
                
                if qa_status == "qa_pass" and review_dec == "approve_candidate" and sid in staging_dict:
                    db_row = staging_dict[sid]
                    
                    sweet = db_row[col_idx["sweet"]] if "sweet" in col_idx else ""
                    fruity = db_row[col_idx["fruity"]] if "fruity" in col_idx else ""
                    floral = db_row[col_idx["floral"]] if "floral" in col_idx else ""
                    spicy = db_row[col_idx["spicy"]] if "spicy" in col_idx else ""
                    smoky = db_row[col_idx["smoky"]] if "smoky" in col_idx else ""
                    peaty = db_row[col_idx["peaty"]] if "peaty" in col_idx else ""
                    sherry = db_row[col_idx["sherry"]] if "sherry" in col_idx else ""
                    oak = db_row[col_idx["oak"]] if "oak" in col_idx else ""
                    rich = db_row[col_idx["rich_body"]] if "rich_body" in col_idx else ""
                    light = db_row[col_idx["light_body"]] if "light_body" in col_idx else ""
                    
                    out_rows.append({
                        "staging_profile_id": sid,
                        "whisky_id": row.get("whisky_id"),
                        "whisky_name": row.get("production_whisky_name") or row.get("staging_whisky_name"),
                        "source_book": row.get("source_book"),
                        "approval_status": row.get("approval_status"),
                        "axis_score_summary": row.get("axis_score_summary"),
                        "score_scale_detected": row.get("score_scale_detected"),
                        "sweet_score": sweet,
                        "fruity_score": fruity,
                        "floral_score": floral,
                        "spicy_score": spicy,
                        "smoky_score": smoky,
                        "peaty_score": peaty,
                        "sherry_score": sherry,
                        "oak_score": oak,
                        "rich_score": rich,
                        "light_score": light,
                        "qa_status": qa_status,
                        "review_decision": review_dec,
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
    if metrics["exported_count"] == 2 and metrics["skipped_count"] == 0:
        gate_decision = "GO"
    elif metrics["exported_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# NB-FP-03 Staging Book Flavor Profiles Export Report

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
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)
        
if __name__ == "__main__":
    main()

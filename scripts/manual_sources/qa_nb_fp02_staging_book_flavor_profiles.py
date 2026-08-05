import sqlite3
import csv
import json
import hashlib
from pathlib import Path
from collections import defaultdict

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    out_csv = root / "data" / "output" / "nb_fp02_staging_book_flavor_profiles_qa.csv"
    report_out = root / "output" / "reports" / "nb_fp02_staging_book_flavor_profiles_qa_report.md"
    gate_out = root / "output" / "reports" / "nb_fp02_staging_book_flavor_profiles_qa_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id, name, original_name FROM whiskies")
    all_whiskies = {row[0]: {"name": row[1], "original_name": row[2]} for row in cur.fetchall()}
    
    cur.execute("SELECT whisky_id FROM flavor_profiles")
    existing_flavor_profiles_ids = set(row[0] for row in cur.fetchall())
    
    cur.execute("PRAGMA table_info(staging_book_flavor_profiles)")
    columns = [row[1] for row in cur.fetchall()]
    col_idx = {name: i for i, name in enumerate(columns)}
    
    flavor_axes = ['smoky', 'peaty', 'sherry', 'fruity', 'floral', 'spicy', 'sweet', 'oak', 'maritime', 'winey', 'malty', 'nutty', 'herbal', 'waxy', 'oily', 'light_body', 'rich_body']
    
    cur.execute("SELECT * FROM staging_book_flavor_profiles")
    rows = cur.fetchall()
    
    metrics = {
        "qa_input_count": len(rows),
        "qa_pass_count": 0,
        "qa_warn_count": 0,
        "qa_fail_count": 0,
        "missing_fk_count": 0,
        "existing_flavor_profile_count": 0,
        "duplicate_staging_count": 0,
        "invalid_score_count": 0,
        "scale_inconsistent_count": 0,
        "light_rich_conflict_count": 0,
        "explicit_zero_count": 0,
        "null_score_count": 0
    }
    
    staging_whisky_source_counts = defaultdict(int)
    for row in rows:
        wid = row[col_idx["whisky_id"]]
        source = row[col_idx.get("source_book", -1)] if "source_book" in col_idx else ""
        if wid and source:
            staging_whisky_source_counts[(wid, source)] += 1
            
    out_rows = []
    
    for row in rows:
        sid = row[col_idx["staging_id"]]
        wid = row[col_idx["whisky_id"]]
        staging_wname = row[col_idx["whisky_name"]]
        source_book = row[col_idx.get("source_book", -1)] if "source_book" in col_idx else ""
        approval_status = row[col_idx.get("approval_status", -1)] if "approval_status" in col_idx else ""
        
        qa_status = "qa_pass"
        reasons = []
        
        prod_wname = ""
        if not wid or wid not in all_whiskies:
            qa_status = "qa_fail"
            reasons.append("missing_whisky_fk")
            metrics["missing_fk_count"] += 1
        else:
            prod_wname = all_whiskies[wid]["name"] or all_whiskies[wid]["original_name"]
            
        if wid in existing_flavor_profiles_ids:
            if qa_status == "qa_pass": qa_status = "qa_warn"
            reasons.append("existing_flavor_profile")
            metrics["existing_flavor_profile_count"] += 1
            
        dup_count = staging_whisky_source_counts.get((wid, source_book), 0)
        if dup_count > 1:
            qa_status = "qa_fail"
            reasons.append("duplicate_staging")
            metrics["duplicate_staging_count"] += 1
            
        if approval_status != "staging_pending_review":
            qa_status = "qa_warn"
            reasons.append("status_not_pending")
            
        scores = {}
        nulls = 0
        explicit_zeros = 0
        invalid_scores = 0
        max_score = -1
        
        for axis in flavor_axes:
            if axis in col_idx:
                val = row[col_idx[axis]]
                if val is None or str(val).strip() == "":
                    nulls += 1
                else:
                    try:
                        fval = float(val)
                        scores[axis] = fval
                        if fval == 0:
                            explicit_zeros += 1
                        if fval > max_score:
                            max_score = fval
                    except:
                        invalid_scores += 1
                        
        if len(scores) == 0:
            qa_status = "qa_fail"
            reasons.append("missing_axis_score")
            invalid_scores += 1
            
        if invalid_scores > 0:
            qa_status = "qa_fail"
            reasons.append("invalid_axis_score")
            metrics["invalid_score_count"] += 1
            
        scale_detected = "0-100" if max_score > 1 else "0-1"
        if max_score > 100 or max_score < 0:
            qa_status = "qa_fail"
            reasons.append("invalid_axis_score")
            metrics["invalid_score_count"] += 1
            scale_detected = "invalid"
            
        light = scores.get("light_body", 0)
        rich = scores.get("rich_body", 0)
        conflict = "false"
        if scale_detected == "0-100" and light >= 70 and rich >= 70:
            conflict = "true"
        elif scale_detected == "0-1" and light >= 0.7 and rich >= 0.7:
            conflict = "true"
            
        if conflict == "true":
            if qa_status == "qa_pass": qa_status = "qa_warn"
            reasons.append("light_rich_conflict")
            metrics["light_rich_conflict_count"] += 1
            
        metrics["explicit_zero_count"] += explicit_zeros
        metrics["null_score_count"] += nulls
        
        if nulls > 0 and explicit_zeros > 0:
            if qa_status == "qa_pass": qa_status = "qa_warn"
            reasons.append("explicit_zero_conflict")
            
        if qa_status == "qa_pass":
            metrics["qa_pass_count"] += 1
            review_dec = "approve_candidate"
        elif qa_status == "qa_warn":
            metrics["qa_warn_count"] += 1
            review_dec = "manual_review"
        else:
            metrics["qa_fail_count"] += 1
            review_dec = "reject_candidate"
            
        out_rows.append({
            "staging_profile_id": sid,
            "whisky_id": wid,
            "staging_whisky_name": staging_wname,
            "production_whisky_name": prod_wname,
            "source_book": source_book,
            "approval_status": approval_status,
            "qa_status": qa_status,
            "qa_reason": " | ".join(reasons),
            "axis_score_summary": f"provided:{len(scores)} null:{nulls} zero:{explicit_zeros}",
            "score_scale_detected": scale_detected,
            "has_existing_flavor_profile": "true" if wid in existing_flavor_profiles_ids else "false",
            "duplicate_staging_count": dup_count,
            "light_rich_conflict": conflict,
            "explicit_zero_count": explicit_zeros,
            "null_score_count": nulls,
            "review_decision": review_dec,
            "reviewer_notes": ""
        })
        
    if out_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["qa_pass_count"] > 0 and metrics["qa_fail_count"] == 0:
        if metrics["qa_warn_count"] > 0:
            gate_decision = "REVIEW"
        else:
            gate_decision = "GO"
    elif metrics["qa_pass_count"] > 0 and metrics["qa_warn_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# NB-FP-02 Staging Book Flavor Profiles QA Report

## Metrics
- **QA Input Count:** {metrics["qa_input_count"]}
- **QA Pass:** {metrics["qa_pass_count"]}
- **QA Warn:** {metrics["qa_warn_count"]}
- **QA Fail:** {metrics["qa_fail_count"]}

## Block Reasons Details
- **Missing FK:** {metrics["missing_fk_count"]}
- **Existing Flavor Profile:** {metrics["existing_flavor_profile_count"]}
- **Duplicate Staging:** {metrics["duplicate_staging_count"]}
- **Invalid Score:** {metrics["invalid_score_count"]}
- **Scale Inconsistent:** {metrics["scale_inconsistent_count"]}
- **Light/Rich Conflict:** {metrics["light_rich_conflict_count"]}

## Profile Details
- **Total Explicit Zeros:** {metrics["explicit_zero_count"]}
- **Total Null Scores:** {metrics["null_score_count"]}

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

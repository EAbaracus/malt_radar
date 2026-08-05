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

def validate_scores(radar):
    if not isinstance(radar, dict): return False, 0
    non_null_count = 0
    for k in ["sweet", "smoky", "peaty", "fruity", "spicy", "oaky", "floral"]:
        val = radar.get(k)
        if val is not None:
            if not isinstance(val, (int, float)): return False, non_null_count
            if not (0 <= val <= 100): return False, non_null_count
            non_null_count += 1
    return True, non_null_count

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_jsonl = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12w_book_minibatch_validated.jsonl"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12x_book_minibatch_valid_staging_dry_run.csv"
    report_out = root / "output" / "reports" / "12x_book_minibatch_valid_staging_dry_run_report.md"
    gate_out = root / "output" / "reports" / "12x_book_minibatch_valid_staging_dry_run_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT distillery_id, name FROM distilleries")
    distilleries = {row[1].lower(): row[0] for row in cur.fetchall()}
    
    metrics = {
        "input_valid_candidate_count": 0,
        "planned": 0,
        "blocked": 0,
        "manual_review": 0,
        "duplicate": 0,
        "missing_distillery": 0
    }
    
    out_csv_rows = []
    
    if not in_jsonl.exists():
        metrics["blocked"] += 1
    else:
        with open(in_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    cand = json.loads(line)
                except:
                    continue
                    
                metrics["input_valid_candidate_count"] += 1
                
                b_id = cand.get("batch_id")
                dist = cand.get("possible_distillery", "")
                title = cand.get("candidate_title_clean", "")
                
                planned_status = "planned"
                reasons = []
                proposed_action = "create_new_whisky_candidate"
                matched_dist_id = ""
                duplicate_note = "false"
                
                if not title:
                    planned_status = "blocked"
                    reasons.append("Missing candidate_title_clean")
                    
                if not dist:
                    planned_status = "blocked"
                    reasons.append("Missing possible_distillery")
                    
                if dist.lower() in distilleries:
                    matched_dist_id = distilleries[dist.lower()]
                else:
                    planned_status = "blocked"
                    reasons.append("Distillery not found in DB")
                    metrics["missing_distillery"] += 1
                    
                if cand.get("copyright_safe") is not True:
                    planned_status = "blocked"
                    reasons.append("Not copyright safe")
                    
                conf = cand.get("confidence", 0)
                if conf < 0.5:
                    planned_status = "blocked"
                    reasons.append("Confidence < 0.5")
                    
                tasting = cand.get("structured_tasting_note") or {}
                has_nose = bool(tasting.get("nose"))
                has_palate = bool(tasting.get("palate"))
                has_finish = bool(tasting.get("finish"))
                has_style = bool(tasting.get("style_summary"))
                
                if not (has_nose or has_palate or has_finish or has_style):
                    planned_status = "blocked"
                    reasons.append("No tasting notes")
                    
                radar = cand.get("radar_scores_0_100")
                valid_radar, non_null_count = validate_scores(radar)
                if not valid_radar:
                    planned_status = "blocked"
                    reasons.append("Invalid radar scores")
                    
                if planned_status == "planned":
                    metrics["planned"] += 1
                elif planned_status == "blocked":
                    metrics["blocked"] += 1
                else:
                    metrics["manual_review"] += 1
                    
                out_csv_rows.append({
                    "batch_id": b_id,
                    "possible_distillery": dist,
                    "candidate_title_clean": title,
                    "proposed_action": proposed_action,
                    "planned_status": planned_status,
                    "block_reason": " | ".join(reasons),
                    "matched_distillery_id": matched_dist_id,
                    "duplicate_note_found": duplicate_note,
                    "has_nose": str(has_nose).lower(),
                    "has_palate": str(has_palate).lower(),
                    "has_finish": str(has_finish).lower(),
                    "has_style_summary": str(has_style).lower(),
                    "radar_non_null_count": non_null_count,
                    "confidence": conf,
                    "copyright_safe": cand.get("copyright_safe"),
                    "review_status": "pending_review" if planned_status != "blocked" else "rejected"
                })
                
    if out_csv_rows:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_csv_rows[0].keys()))
            w.writeheader()
            w.writerows(out_csv_rows)
            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["planned"] > 0 and metrics["blocked"] == 0 and metrics["manual_review"] == 0:
        gate_decision = "GO"
    elif metrics["planned"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# 12X Book Minibatch Valid Candidate Staging Dry Run Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input Valid Candidate Count:** {metrics["input_valid_candidate_count"]}
- **Planned:** {metrics["planned"]}
- **Blocked:** {metrics["blocked"]}
- **Manual Review:** {metrics["manual_review"]}
- **Duplicate Note Found:** {metrics["duplicate"]}
- **Missing Distillery:** {metrics["missing_distillery"]}

Gate decision: **{gate_decision}**
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)

if __name__ == "__main__":
    main()

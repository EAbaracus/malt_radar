import sqlite3
import csv
import re
import hashlib
from pathlib import Path
from collections import defaultdict, Counter

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def normalize_key(dist, name):
    text = f"{dist or ''} {name or ''}".lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    generics = ["whisky", "whiskey", "single", "malt", "scotch", "vol", "yo", "year old", "years old"]
    for g in generics:
        text = re.sub(rf'\b{g}\b', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12o_inventory_no_match_classification.csv"
    out_existing_dist = root / "data" / "manual_sources" / "books" / "review_csv" / "12r_existing_distillery_new_expression_candidates.csv"
    out_missing_dist = root / "data" / "manual_sources" / "books" / "review_csv" / "12r_missing_distillery_candidates.csv"
    
    report_out = root / "output" / "reports" / "12r_book_new_candidate_review_pack_report.md"
    gate_out = root / "output" / "reports" / "12r_book_new_candidate_review_pack_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    
    metrics = {
        "input_rows": 0,
        "included_rows": 0,
        "excluded_retry_rows": 0,
        "excluded_noise_rows": 0,
        "existing_distillery_new_expression_raw_count": 0,
        "missing_distillery_raw_count": 0
    }
    
    candidates_existing = defaultdict(list)
    candidates_missing = defaultdict(list)
    
    with open(in_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics["input_rows"] += 1
            cls = row.get("classification")
            
            if cls == "retry_match_candidate":
                metrics["excluded_retry_rows"] += 1
                continue
            if cls in ["likely_parser_noise", "likely_cross_target_leak", "weak_candidate"]:
                metrics["excluded_noise_rows"] += 1
                continue
                
            if cls == "db_distillery_exists_expression_missing":
                metrics["existing_distillery_new_expression_raw_count"] += 1
                metrics["included_rows"] += 1
                target = candidates_existing
            elif cls == "db_distillery_missing":
                metrics["missing_distillery_raw_count"] += 1
                metrics["included_rows"] += 1
                target = candidates_missing
            else:
                continue
                
            dist = row.get("possible_distillery", "")
            if not dist:
                dist = row.get("candidate_name", "").split()[0] if row.get("candidate_name") else ""
            name = row.get("candidate_name", "")
            
            norm_key = normalize_key(dist, name)
            target[norm_key].append(row)
            
    def dedup_and_format(grouped, proposed_action):
        res = []
        for key, rows in grouped.items():
            books = set(r.get("book_source", "") for r in rows)
            classes = set(r.get("classification", "") for r in rows)
            dists = set(r.get("possible_distillery", "") for r in rows if r.get("possible_distillery"))
            
            best_row = max(rows, key=lambda x: int(x.get("raw_snippet_length") or 0))
            
            res.append({
                "possible_distillery": best_row.get("possible_distillery") or (next(iter(dists)) if dists else ""),
                "candidate_name": best_row.get("candidate_name"),
                "normalized_key": key,
                "source_count": len(rows),
                "book_sources": " | ".join(sorted(books)),
                "classifications": " | ".join(sorted(classes)),
                "nearest_db_names": best_row.get("nearest_db_names", ""),
                "confidence": best_row.get("confidence", ""),
                "has_nose": best_row.get("has_nose", ""),
                "has_palate": best_row.get("has_palate", ""),
                "has_finish": best_row.get("has_finish", ""),
                "has_score": best_row.get("has_score", ""),
                "raw_snippet_length": best_row.get("raw_snippet_length", ""),
                "proposed_action": proposed_action,
                "review_status": "pending_review",
                "notes": ""
            })
        return res
        
    out_existing = dedup_and_format(candidates_existing, "add_new_expression_candidate")
    out_missing = dedup_and_format(candidates_missing, "add_new_distillery_candidate")
    
    metrics["existing_distillery_new_expression_deduped_count"] = len(out_existing)
    metrics["missing_distillery_deduped_count"] = len(out_missing)
    
    def write_csv(data, path):
        if not data:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
            
    write_csv(out_existing, out_existing_dist)
    write_csv(out_missing, out_missing_dist)
    
    hash_after = get_hash(db_path)
    
    distillery_counts = Counter()
    for row in out_existing + out_missing:
        distillery_counts[row["possible_distillery"]] += 1
    
    top_dists = "\n".join([f"- {k}: {v}" for k, v in distillery_counts.most_common(10)])
    
    md = f"""# 12R Book New Candidate Review Pack Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Processing Metrics
- **Input Rows:** {metrics["input_rows"]}
- **Included Rows:** {metrics["included_rows"]}
- **Excluded Retry Rows:** {metrics["excluded_retry_rows"]}
- **Excluded Noise Rows:** {metrics["excluded_noise_rows"]}

## Output Details
- **Existing Distillery, New Expression (Raw):** {metrics["existing_distillery_new_expression_raw_count"]}
- **Existing Distillery, New Expression (Deduped):** {metrics["existing_distillery_new_expression_deduped_count"]}
- **Missing Distillery (Raw):** {metrics["missing_distillery_raw_count"]}
- **Missing Distillery (Deduped):** {metrics["missing_distillery_deduped_count"]}

## Top Possible Distilleries
{top_dists}
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write("REVIEW")

if __name__ == "__main__":
    main()

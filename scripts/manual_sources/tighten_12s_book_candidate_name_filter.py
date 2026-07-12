import sqlite3
import csv
import re
import hashlib
from pathlib import Path
from collections import Counter

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def evaluate_candidate(cand_name, dist):
    cn_lower = cand_name.lower().strip()
    words = cn_lower.split()
    
    if cand_name.strip().endswith('.') and len(words) > 2:
        return "parser_noise", "Ends with period (sentence)"
        
    if cand_name and cand_name[0].islower():
        return "parser_noise", "Starts with lowercase letter"
        
    aroma_words = {"apple", "mango", "caramel", "pleasant", "chili", "fruit", "nose", "palate", "finish", "sweet", "spice", "smoky", "honey", "vanilla", "hints", "notes", "flavor", "flavours", "tannins", "syrup"}
    aroma_count = sum(1 for w in words if w in aroma_words)
    if aroma_count >= 1:
        return "parser_noise", f"Contains aroma words ({aroma_count})"
        
    verb_conj = {"are", "is", "was", "were", "has", "have", "being", "with", "plus", "and", "but", "they", "its", "their", "which", "that", "it"}
    vc_count = sum(1 for w in words if w in verb_conj)
    if vc_count >= 1:
        return "parser_noise", f"Contains verbs/conjunctions ({vc_count})"

    has_age = bool(re.search(r'\b(10|12|14|15|16|17|18|21|25|30|40)\b', cn_lower) or re.search(r'\b(?:aged\s*)?\d{1,2}\s*(?:yo|y\.o\.|year|years)\b', cn_lower))
    cask_expr = ["quarter cask", "triple wood", "uigeadail", "corryvreckan", "dark origins", "cask strength", "double cask", "sherry cask", "port wood", "batch", "reserve", "vintage", "cask", "edition", "wood", "matured", "distilled"]
    has_expr = any(ex in cn_lower for ex in cask_expr)
    
    if len(words) > 6 and not (has_age or has_expr):
        return "parser_noise", "Too long (>6 words) without age/cask markers"
        
    if has_age or has_expr:
        return "strict_accept", "Contains age or known expression token"
        
    if dist and dist.lower() in cn_lower and cn_lower.startswith(dist.lower().split()[0]):
        if 2 <= len(words) <= 5:
            return "strict_accept", "Starts with distillery and has 2-5 words"
            
    if len(words) < 2 and not has_age:
        return "weak_candidate", "Too short/generic"
        
    return "manual_review", "Passed basic filters but lacks strong expression markers"

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12s_book_new_expression_validation.csv"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12s_strict_book_new_expression_candidates.csv"
    
    report_out = root / "output" / "reports" / "12s_strict_book_candidate_name_filter_report.md"
    gate_out = root / "output" / "reports" / "12s_strict_book_candidate_name_filter_gate.txt"
    
    hash_before = get_hash(db_path)
    
    metrics = {
        "input_accept_count": 0,
        "strict_accept": 0,
        "manual_review": 0,
        "parser_noise": 0,
        "weak_candidate": 0
    }
    
    out_rows = []
    
    with open(in_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("validation_status") != "accept_candidate":
                continue
                
            metrics["input_accept_count"] += 1
            cand_name = row.get("candidate_name", "")
            dist = row.get("possible_distillery", "")
            
            strict_status, strict_reason = evaluate_candidate(cand_name, dist)
            
            metrics[strict_status] += 1
            
            out_rows.append({
                "possible_distillery": dist,
                "candidate_name": cand_name,
                "strict_status": strict_status,
                "strict_reason": strict_reason,
                "nearest_db_names": row.get("nearest_db_names", ""),
                "nearest_score": row.get("nearest_score", ""),
                "source_count": row.get("source_count", ""),
                "book_sources": row.get("book_sources", ""),
                "proposed_action": "add_new_expression_candidate" if strict_status == "strict_accept" else "skip_or_review",
                "review_status": "pending_review"
            })
            
    if out_rows:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    distillery_counts = Counter()
    for row in out_rows:
        distillery_counts[row["possible_distillery"]] += 1
        
    top_dists = "\n".join([f"- {k}: {v}" for k, v in distillery_counts.most_common(10)])
    
    md = f"""# 12S-B Strict Candidate Name Filter Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input Accept Count (from 12S):** {metrics["input_accept_count"]}
- **Strict Accept:** {metrics["strict_accept"]}
- **Manual Review:** {metrics["manual_review"]}
- **Parser Noise:** {metrics["parser_noise"]}
- **Weak Candidate:** {metrics["weak_candidate"]}

## Top Distilleries
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

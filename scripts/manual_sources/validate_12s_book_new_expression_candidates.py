import sqlite3
import csv
import re
import hashlib
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def extract_age(text):
    m = re.search(r'\b(?:aged\s*)?(\d{1,2})\s*(?:yo|y\.o\.|year|years)(?:\s*old)?\b', text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'\b(10|12|14|15|16|17|18|21|25|30|40)\b', text)
    if m:
        return m.group(1)
    return None

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    generics = ["whisky", "whiskey", "scotch", "single", "malt", "vol", "yo"]
    for g in generics:
        text = re.sub(rf'\b{g}\b', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_db_whiskies(cur):
    cur.execute("""
        SELECT w.whisky_id, w.name, w.original_name, d.name, w.age_statement
        FROM whiskies w
        LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
    """)
    res = []
    for row in cur.fetchall():
        wid, name, orig, dist, age = row
        comb = str(name or "") + " " + str(orig or "")
        
        db_age = str(age) if age else extract_age(comb)
        
        ndist = normalize_text(str(dist or ""))
        expr = comb.lower().replace(str(dist or "").lower(), "")
        expr_norm = normalize_text(expr)
        
        res.append({
            "id": wid,
            "name": name,
            "dist_norm": ndist,
            "expr_norm": expr_norm,
            "expr_tokens": set(expr_norm.split()),
            "age": db_age,
            "raw": comb
        })
    return res

def is_parser_noise(text):
    noise_keywords = ["palate", "finish", "nose", "color", "colour", "aroma", "taste", "with a dash", "hints of", "flavors of", "rich", "sweet", "dry", "spicy"]
    t = text.lower()
    for kw in noise_keywords:
        if kw in t:
            return True
    if len(t.split()) > 10:
        return True
    return False

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12r_existing_distillery_new_expression_candidates.csv"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12s_book_new_expression_validation.csv"
    
    report_out = root / "output" / "reports" / "12s_book_new_expression_validation_report.md"
    gate_out = root / "output" / "reports" / "12s_book_new_expression_validation_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    db_whiskies = get_db_whiskies(cur)
    
    metrics = {
        "input_count": 0,
        "accept_candidate": 0,
        "manual_review": 0,
        "likely_duplicate": 0,
        "weak_candidate": 0,
        "parser_noise": 0
    }
    
    out_rows = []
    
    with open(in_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics["input_count"] += 1
            cand_name = row.get("candidate_name", "")
            dist = row.get("possible_distillery", "")
            
            ndist = normalize_text(dist)
            expr = cand_name.lower().replace(dist.lower(), "")
            nexpr = normalize_text(expr)
            nexpr_tokens = set(nexpr.split())
            cand_age = extract_age(cand_name)
            
            best_score = -1
            best_db_matches = []
            
            for dbw in db_whiskies:
                if (ndist and ndist in dbw["dist_norm"]) or (dbw["dist_norm"] and dbw["dist_norm"] in ndist):
                    if not nexpr_tokens and not dbw["expr_tokens"]:
                        score = 1.0 
                    elif not nexpr_tokens or not dbw["expr_tokens"]:
                        score = 0.0
                    else:
                        overlap = nexpr_tokens.intersection(dbw["expr_tokens"])
                        overlap_score = len(overlap) / max(len(nexpr_tokens), len(dbw["expr_tokens"]), 1)
                        cand_norm_str = " ".join(sorted(list(nexpr_tokens)))
                        db_norm_str = " ".join(sorted(list(dbw["expr_tokens"])))
                        ratio = SequenceMatcher(None, cand_norm_str, db_norm_str).ratio()
                        score = (overlap_score + ratio) / 2.0
                        
                        if cand_age and dbw["age"]:
                            if cand_age == dbw["age"]:
                                score += 0.1
                            else:
                                score -= 0.2
                                
                    if score > best_score:
                        best_score = score
                    
                    if score > 0.4:
                        best_db_matches.append((score, dbw["raw"]))
            
            best_db_matches.sort(key=lambda x: x[0], reverse=True)
            nearest_db_names = " | ".join([f"{m[1]} ({m[0]:.2f})" for m in best_db_matches[:5]])
            
            status = "accept_candidate"
            duplicate_reason = ""
            
            if is_parser_noise(cand_name):
                status = "parser_noise"
            elif len(nexpr_tokens) == 0:
                status = "weak_candidate"
            elif best_score >= 0.90:
                status = "likely_duplicate"
                duplicate_reason = "High score match >= 0.90"
            elif best_score >= 0.80:
                status = "manual_review"
                duplicate_reason = "Medium score match 0.80-0.90"
            else:
                if len(nexpr_tokens) < 2 and not cand_age:
                    status = "weak_candidate"
                    
            metrics[status] += 1
            
            row["validation_status"] = status
            row["nearest_db_names"] = nearest_db_names
            row["nearest_score"] = round(best_score, 3)
            row["duplicate_reason"] = duplicate_reason
            row["proposed_action"] = "add_new_expression_candidate" if status == "accept_candidate" else "skip_or_review"
            row["review_status"] = "pending_review"
            out_rows.append(row)
            
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
    
    md = f"""# 12S Book New Expression Validation Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input Count:** {metrics["input_count"]}
- **Accept Candidate:** {metrics["accept_candidate"]}
- **Manual Review:** {metrics["manual_review"]}
- **Likely Duplicate:** {metrics["likely_duplicate"]}
- **Weak Candidate:** {metrics["weak_candidate"]}
- **Parser Noise:** {metrics["parser_noise"]}

## Top Distilleries
{top_dists}
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write("REVIEW")

if __name__ == "__main__":
    main()

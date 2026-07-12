import sqlite3
import csv
import re
import hashlib
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def normalize_name(name):
    # remove generics
    generics = ["whisky", "whiskey", "single", "malt", "scotch", "tasting", "notes", "edition", "aged", "vol", "yo", "year old", "years old"]
    safe = str(name).lower()
    for g in generics:
        safe = re.sub(rf'\b{g}\b', '', safe)
    # clean up spaces and punctuation
    safe = re.sub(r'[^\w\s]', ' ', safe)
    safe = re.sub(r'\s+', ' ', safe).strip()
    return safe

def get_db_distilleries(cur):
    cur.execute("SELECT DISTINCT original_name FROM whiskies WHERE original_name IS NOT NULL")
    dist1 = [row[0] for row in cur.fetchall() if row[0]]
    cur.execute("SELECT name FROM distilleries")
    dist2 = [row[0] for row in cur.fetchall() if row[0]]
    
    dists = set()
    for d in dist1 + dist2:
        if d:
            dists.add(d.lower())
    return dists

def get_db_whiskies(cur):
    cur.execute("SELECT whisky_id, name, original_name FROM whiskies")
    return cur.fetchall()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12o_full_book_inventory.csv"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12o_inventory_no_match_classification.csv"
    report_out = root / "output" / "reports" / "12o_inventory_no_match_classification_report.md"
    gate_out = root / "output" / "reports" / "12o_inventory_no_match_classification_gate.txt"
    
    hash_before = get_hash(db_path)
    
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    db_distilleries = get_db_distilleries(cur)
    db_whiskies = get_db_whiskies(cur)
    
    # Pre-tokenize db whiskies for faster search
    db_whisky_tokens = []
    for w in db_whiskies:
        wid, name, orig = w
        comb = str(name or "") + " " + str(orig or "")
        norm = normalize_name(comb)
        db_whisky_tokens.append({
            "id": wid,
            "raw": comb,
            "norm": norm,
            "tokens": set(norm.split())
        })
        
    classifications = []
    
    counts = {
        "input_no_match_count": 0,
        "db_distillery_exists_expression_missing": 0,
        "db_distillery_missing": 0,
        "likely_parser_noise": 0,
        "likely_cross_target_leak": 0,
        "weak_candidate": 0,
        "retry_match_candidate": 0
    }
    
    with open(in_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("match_status") != "no_match":
                continue
                
            counts["input_no_match_count"] += 1
            
            cand_name = row.get("candidate_name", "")
            norm_name = normalize_name(cand_name)
            tokens = set(norm_name.split())
            
            # noise check
            if len(tokens) == 0 or len(cand_name) < 4:
                cls = "likely_parser_noise"
                nearest = []
            else:
                first_word = norm_name.split()[0] if norm_name else ""
                
                matches = []
                distillery_exists = False
                
                for dbw in db_whisky_tokens:
                    overlap = tokens.intersection(dbw["tokens"])
                    if overlap:
                        score = len(overlap) / float(len(tokens) + 0.001)
                        matches.append((score, dbw["raw"]))
                        
                    if first_word and first_word in dbw["tokens"]:
                        distillery_exists = True
                        
                matches.sort(key=lambda x: x[0], reverse=True)
                nearest = [m[1] for m in matches[:5] if m[0] > 0.2]
                
                if not distillery_exists:
                    for d in db_distilleries:
                        if first_word in d or any(t in d for t in tokens):
                            distillery_exists = True
                            break
                            
                if len(nearest) > 0:
                    cls = "retry_match_candidate"
                elif distillery_exists:
                    cls = "db_distillery_exists_expression_missing"
                else:
                    cls = "db_distillery_missing"
                    
            counts[cls] += 1
            
            row["classification"] = cls
            row["nearest_db_names"] = " | ".join(nearest)
            classifications.append(row)
            
    if classifications:
        fieldnames = list(classifications[0].keys())
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(classifications)
            
    hash_after = get_hash(db_path)
    
    md = f"""# 12O-B Inventory Match Tuning Audit

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input No Match Count:** {counts["input_no_match_count"]}
- **DB Distillery Exists, Expression Missing:** {counts["db_distillery_exists_expression_missing"]}
- **DB Distillery Missing:** {counts["db_distillery_missing"]}
- **Retry Match Candidate:** {counts["retry_match_candidate"]}
- **Likely Parser Noise:** {counts["likely_parser_noise"]}
- **Likely Cross Target Leak:** {counts["likely_cross_target_leak"]}
- **Weak Candidate:** {counts["weak_candidate"]}

## Summary
The no-match candidates from 12O have been re-classified using token normalization and fuzzy scoring.
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

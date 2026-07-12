import sqlite3
import csv
import re
import hashlib
from pathlib import Path
from difflib import SequenceMatcher

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
    generics = ["whisky", "whiskey", "scotch", "single", "malt", "tasting", "notes", "edition", "release", "aged", "years", "year", "old", "official", "bottling", "vol", "yo"]
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
        comb = str(name or "") + " " + str(orig or "") + " " + str(dist or "")
        norm = normalize_text(comb)
        db_age = str(age) if age else extract_age(comb)
        
        res.append({
            "id": wid,
            "name": name,
            "dist": dist or "",
            "raw": comb,
            "norm": norm,
            "tokens": set(norm.split()),
            "age": db_age
        })
    return res

def score_match(cand_tokens, cand_age, cand_dist, dbw):
    score = 0.0
    
    if not cand_tokens:
        return 0.0, False, False
        
    overlap = cand_tokens.intersection(dbw["tokens"])
    overlap_score = len(overlap) / max(len(cand_tokens), len(dbw["tokens"]), 1)
    
    cand_norm = " ".join(sorted(list(cand_tokens)))
    db_norm = " ".join(sorted(list(dbw["tokens"])))
    ratio = SequenceMatcher(None, cand_norm, db_norm).ratio()
    
    age_match_bonus = 0.0
    is_age_match = False
    if cand_age and dbw["age"]:
        if cand_age == dbw["age"]:
            age_match_bonus = 0.2
            is_age_match = True
        else:
            age_match_bonus = -0.2 
            
    dist_match_bonus = 0.0
    is_dist_match = False
    if cand_dist and dbw["dist"]:
        if normalize_text(cand_dist) in dbw["norm"]:
            dist_match_bonus = 0.15
            is_dist_match = True
            
    rare_tokens = {"uigeadail", "corryvreckan", "lasanta", "quinta", "ruban", "nectar", "signet", "quarter", "triple", "wood", "dark", "origins", "double", "cask"}
    rare_cand = cand_tokens.intersection(rare_tokens)
    rare_bonus = 0.0
    if rare_cand:
        if rare_cand.issubset(dbw["tokens"]):
            rare_bonus = 0.2
        else:
            rare_bonus = -0.1
            
    final_score = (overlap_score * 0.4) + (ratio * 0.4) + age_match_bonus + dist_match_bonus + rare_bonus
    
    return min(max(final_score, 0.0), 1.0), is_age_match, is_dist_match

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12o_inventory_no_match_classification.csv"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12p_retry_match_resolution.csv"
    report_out = root / "output" / "reports" / "12p_retry_match_resolution_report.md"
    gate_out = root / "output" / "reports" / "12p_retry_match_resolution_gate.txt"
    
    hash_before = get_hash(db_path)
    
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    db_whiskies = get_db_whiskies(cur)
    
    resolved_high = 0
    resolved_review = 0
    unresolved = 0
    total = 0
    
    out_rows = []
    
    with open(in_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("classification") != "retry_match_candidate":
                continue
                
            total += 1
            cand_name = row.get("candidate_name", "")
            cand_dist = row.get("possible_distillery", "")
            if not cand_dist and cand_name:
                cand_dist = cand_name.split()[0]
                
            cand_age = extract_age(cand_name)
            cand_norm = normalize_text(cand_name)
            cand_tokens = set(cand_norm.split())
            
            best_score = -1
            best_match = None
            best_age_match = False
            best_dist_match = False
            
            top_matches = []
            
            for dbw in db_whiskies:
                score, is_age_match, is_dist_match = score_match(cand_tokens, cand_age, cand_dist, dbw)
                top_matches.append((score, dbw))
                if score > best_score:
                    best_score = score
                    best_match = dbw
                    best_age_match = is_age_match
                    best_dist_match = is_dist_match
                    
            top_matches.sort(key=lambda x: x[0], reverse=True)
            top_5 = " | ".join([f"{m[1]['name']} ({m[0]:.2f})" for m in top_matches[:5]])
            
            res_status = "unresolved"
            if best_score >= 0.92:
                res_status = "resolved_high"
                resolved_high += 1
            elif best_score >= 0.84:
                res_status = "resolved_review"
                resolved_review += 1
            else:
                unresolved += 1
                
            out_rows.append({
                "candidate_name": cand_name,
                "possible_distillery": cand_dist,
                "classification": row.get("classification"),
                "best_match_whisky_id": best_match["id"] if best_match else "",
                "best_match_name": best_match["name"] if best_match else "",
                "best_match_distillery": best_match["dist"] if best_match else "",
                "final_score": round(best_score, 3),
                "resolved_status": res_status,
                "age_match": best_age_match,
                "distillery_match": best_dist_match,
                "alias_used": cand_norm,
                "top_5_matches": top_5
            })
            
    if out_rows:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    md = f"""# 12P Matcher Tune Audit Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input Retry Count:** {total}
- **Resolved High (>=0.92):** {resolved_high}
- **Resolved Review (>=0.84):** {resolved_review}
- **Unresolved (<0.84):** {unresolved}

## Summary
The 142 retry_match_candidate rows were re-evaluated with advanced token normalization, age matching, and sequence similarity logic.
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

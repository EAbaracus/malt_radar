import sqlite3
import csv
import re
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from difflib import SequenceMatcher

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def extract_and_remove_abv(title):
    m = re.search(r',?\s*\b(\d{2}(?:\.\d)?)\s*(?:%|vol\.?|alc\.?|abv\.?)\b', title, re.IGNORECASE)
    abv = None
    if m:
        abv = m.group(1)
        title = title[:m.start()] + title[m.end():]
    return abv, title.strip()

def extract_and_remove_age(title):
    m = re.search(r',?\s*\b(?:aged\s*)?(\d{1,2})\s*(?:-?yo|-?y\.o\.|-?year|-?years)(?:\s*-?old)?\b', title, re.IGNORECASE)
    age = None
    if m:
        age = m.group(1)
        title = title[:m.start()] + title[m.end():]
        return age, title.strip()
    
    m = re.search(r'\b(10|12|14|15|16|17|18|21|25|30|40)\b', title)
    if m:
        age = m.group(1)
    return age, title

def clean_title(title, dist):
    t = str(title).strip()
    if dist:
        dist_esc = re.escape(dist)
        t = re.sub(rf'(?i)^{dist_esc}\s+{dist_esc}\b', dist, t)
        
    abv, t = extract_and_remove_abv(t)
    age, t = extract_and_remove_age(t)
    
    t_clean = re.sub(r'[^\w\s]', ' ', t)
    t_clean = re.sub(r'\s+', ' ', t_clean).strip()
    
    t_clean = t_clean.title()
    
    norm_key = t_clean.lower()
    generics = ["whisky", "whiskey", "scotch", "single", "malt"]
    for g in generics:
        norm_key = re.sub(rf'\b{g}\b', ' ', norm_key)
    norm_key = re.sub(r'\s+', ' ', norm_key).strip()
    
    return t_clean, norm_key, age, abv

def get_db_whiskies(cur):
    cur.execute("""
        SELECT w.whisky_id, w.name, d.name, w.age_statement
        FROM whiskies w
        JOIN distilleries d ON w.distillery_id = d.distillery_id
    """)
    res = []
    for row in cur.fetchall():
        wid, name, dist, age = row
        comb = f"{name or ''}"
        
        expr_norm = comb.lower()
        expr_norm = re.sub(r'[^\w\s]', ' ', expr_norm)
        generics = ["whisky", "whiskey", "scotch", "single", "malt", "vol", "yo", "year", "years", "old", "aged"]
        for g in generics:
            expr_norm = re.sub(rf'\b{g}\b', ' ', expr_norm)
        expr_norm = re.sub(r'\s+', ' ', expr_norm).strip()
        
        res.append({
            "id": wid,
            "name": name,
            "dist": dist,
            "expr_norm": expr_norm,
            "expr_tokens": set(expr_norm.split()),
            "age": str(age) if age else None
        })
    return res

def score_match(cand_tokens, cand_age, cand_dist, dbw):
    score = 0.0
    debug_parts = []
    
    if cand_dist and cand_dist.lower() == str(dbw["dist"]).lower():
        score += 0.2
        debug_parts.append("+dist(0.2)")
        
    if not cand_tokens and not dbw["expr_tokens"]:
        score += 0.5
        debug_parts.append("+empty_expr(0.5)")
    elif not cand_tokens or not dbw["expr_tokens"]:
        pass
    else:
        overlap = cand_tokens.intersection(dbw["expr_tokens"])
        overlap_score = len(overlap) / max(len(cand_tokens), len(dbw["expr_tokens"]), 1)
        
        cand_norm_str = " ".join(sorted(list(cand_tokens)))
        db_norm_str = " ".join(sorted(list(dbw["expr_tokens"])))
        ratio = SequenceMatcher(None, cand_norm_str, db_norm_str).ratio()
        
        base = (overlap_score * 0.4) + (ratio * 0.4)
        score += base
        debug_parts.append(f"+text({base:.2f})")
        
    if cand_age and dbw["age"]:
        if cand_age == dbw["age"]:
            score += 0.15
            debug_parts.append("+age(0.15)")
        else:
            score -= 0.2
            debug_parts.append("-age(-0.2)")
            
    rare_tokens = {"uigeadail", "corryvreckan", "quarter", "triple", "dark", "origins", "cask", "strength", "sherry", "port", "wood"}
    rare_cand = cand_tokens.intersection(rare_tokens)
    if rare_cand and rare_cand.issubset(dbw["expr_tokens"]):
        score += 0.1
        debug_parts.append("+rare(0.1)")
        
    return min(max(score, 0.0), 1.0), " ".join(debug_parts)

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12u_book_entry_boundary_candidates.csv"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12u_clean_book_entry_title_rematch.csv"
    report_out = root / "output" / "reports" / "12u_book_title_cleanup_rematch_report.md"
    gate_out = root / "output" / "reports" / "12u_book_title_cleanup_rematch_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    db_whiskies = get_db_whiskies(cur)
    
    metrics = {
        "input_rows": 0,
        "deduped_rows": 0,
        "cleaned_title_count": 0,
        "duplicate_title_count": 0,
        "high_match": 0,
        "review_match": 0,
        "no_match": 0
    }
    
    dedup_map = {}
    
    with open(in_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics["input_rows"] += 1
            orig = row.get("candidate_title", "")
            dist = row.get("possible_distillery", "")
            
            t_clean, norm_key, age, abv = clean_title(orig, dist)
            if not age:
                age = row.get("age", "")
            if not abv:
                abv = row.get("abv", "")
                
            dedup_key = f"{dist.lower()}|{norm_key}|{age}|{abv}"
            
            if dedup_key in dedup_map:
                metrics["duplicate_title_count"] += 1
                dedup_map[dedup_key]["source_count"] += 1
                bs = set(dedup_map[dedup_key]["book_sources"].split(" | "))
                bs.add(row.get("book_source", ""))
                dedup_map[dedup_key]["book_sources"] = " | ".join(sorted(list(bs)))
            else:
                metrics["cleaned_title_count"] += 1
                dedup_map[dedup_key] = {
                    "book_source": row.get("book_source", ""),
                    "possible_distillery": dist,
                    "candidate_title_original": orig,
                    "candidate_title_clean": t_clean,
                    "normalized_key": norm_key,
                    "age": age,
                    "abv": abv,
                    "source_count": 1,
                    "book_sources": row.get("book_source", ""),
                    "title_confidence": row.get("title_confidence", ""),
                    "body_confidence": row.get("body_confidence", "")
                }
                
    out_rows = []
    
    for _, cand in dedup_map.items():
        metrics["deduped_rows"] += 1
        
        cand_tokens = set(cand["normalized_key"].split())
        cand_age = cand["age"]
        cand_dist = cand["possible_distillery"]
        
        dist_tokens = set(cand_dist.lower().split())
        cand_tokens = cand_tokens - dist_tokens
        
        best_score = -1
        best_match = None
        best_debug = ""
        
        for dbw in db_whiskies:
            if dbw["dist"].lower() == cand_dist.lower():
                score, debug = score_match(cand_tokens, cand_age, cand_dist, dbw)
                if score > best_score:
                    best_score = score
                    best_match = dbw
                    best_debug = debug
                    
        match_status = "NO_MATCH"
        if best_score >= 0.92:
            match_status = "HIGH"
            metrics["high_match"] += 1
        elif best_score >= 0.84:
            match_status = "REVIEW"
            metrics["review_match"] += 1
        else:
            metrics["no_match"] += 1
            
        cand["match_status"] = match_status
        cand["best_match_whisky_id"] = best_match["id"] if best_match else ""
        cand["best_match_name"] = best_match["name"] if best_match else ""
        cand["match_score"] = round(best_score, 3) if best_match else ""
        cand["match_debug"] = best_debug
        cand["review_status"] = "pending_review"
        out_rows.append(cand)
        
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
    
    md = f"""# 12U-B Book Title Cleanup and Rematch Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input Rows:** {metrics["input_rows"]}
- **Deduped Rows:** {metrics["deduped_rows"]}
- **Cleaned Title Count:** {metrics["cleaned_title_count"]}
- **Duplicate Title Count:** {metrics["duplicate_title_count"]}

## Match Breakdown
- **High Match (>= 0.92):** {metrics["high_match"]}
- **Review Match (>= 0.84):** {metrics["review_match"]}
- **No Match (< 0.84):** {metrics["no_match"]}

## Top Distilleries
{top_dists}
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write("REVIEW")

if __name__ == "__main__":
    main()

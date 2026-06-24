import sqlite3
import csv
import json
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
    if m: return m.group(1)
    m = re.search(r'\b(10|12|14|15|16|17|18|21|25|30|40)\b', text)
    if m: return m.group(1)
    return None

def extract_abv(text):
    m = re.search(r'\b(\d{2}(?:\.\d)?)\s*(?:%|vol|abv)\b', text, re.IGNORECASE)
    if m: return m.group(1)
    return None

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    generics = ["whisky", "whiskey", "scotch", "single", "malt", "vol", "yo", "year", "years", "old", "aged"]
    for g in generics:
        text = re.sub(rf'\b{g}\b', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_db_distilleries(cur):
    cur.execute("SELECT name FROM distilleries")
    return sorted([row[0] for row in cur.fetchall()], key=len, reverse=True)

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
        db_age = str(age) if age else extract_age(comb)
        
        expr_norm = normalize_text(comb)
        
        res.append({
            "id": wid,
            "name": name,
            "dist": dist,
            "expr_norm": expr_norm,
            "expr_tokens": set(expr_norm.split()),
            "age": db_age,
            "raw": comb
        })
    return res

def is_valid_title(line, distilleries):
    line_clean = line.strip()
    if not line_clean: return None, "Empty"
    
    words = line_clean.split()
    if not (2 <= len(words) <= 9):
        return None, f"Length {len(words)} not in 2-8"
        
    line_lower = line_clean.lower()
    
    matched_dist = None
    for d in distilleries:
        if line_lower.startswith(d.lower()):
            next_char_idx = len(d)
            if next_char_idx == len(line_lower) or not line_lower[next_char_idx].isalpha():
                matched_dist = d
                break
                
    if not matched_dist:
        return None, "No distillery match"
        
    if line_clean.endswith('.') and not re.search(r'(vol\.|y\.o\.|alc\.|abv\.)$', line_lower):
        return None, "Ends with period"
        
    aroma_words = {"apple", "mango", "caramel", "pleasant", "chili", "fruit", "nose", "palate", "finish", "sweet", "spice", "smoky", "honey", "vanilla", "hints", "notes", "flavor", "aroma"}
    verb_conj = {"are", "is", "was", "were", "has", "have", "being", "with", "plus", "and", "but", "they", "its", "their", "which", "that"}
    
    w_lower = set(w.lower().strip(',.') for w in words)
    if len(w_lower.intersection(aroma_words)) > 0:
        return None, "Contains aroma words"
    if len(w_lower.intersection(verb_conj)) > 0:
        return None, "Contains verbs/conjunctions"
        
    caps_count = sum(1 for w in words if w[0].isupper() or w.isdigit())
    if caps_count < len(words) / 2.0:
        return None, "Not title case"
        
    return matched_dist, "OK"

def score_match(cand_tokens, cand_age, dbw):
    if not cand_tokens and not dbw["expr_tokens"]: return 1.0
    if not cand_tokens or not dbw["expr_tokens"]: return 0.0
    
    overlap = cand_tokens.intersection(dbw["expr_tokens"])
    overlap_score = len(overlap) / max(len(cand_tokens), len(dbw["expr_tokens"]), 1)
    
    cand_norm_str = " ".join(sorted(list(cand_tokens)))
    db_norm_str = " ".join(sorted(list(dbw["expr_tokens"])))
    ratio = SequenceMatcher(None, cand_norm_str, db_norm_str).ratio()
    
    score = (overlap_score + ratio) / 2.0
    
    if cand_age and dbw["age"]:
        if cand_age == dbw["age"]:
            score += 0.15
        else:
            score -= 0.2
            
    return min(max(score, 0.0), 1.0)

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    chunks_dir = root / "data" / "manual_sources" / "books" / "chunks"
    
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12u_book_entry_boundary_candidates.csv"
    report_out = root / "output" / "reports" / "12u_book_entry_boundary_parser_report.md"
    gate_out = root / "output" / "reports" / "12u_book_entry_boundary_parser_gate.txt"
    
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    distilleries = get_db_distilleries(cur)
    db_whiskies = get_db_whiskies(cur)
    
    metrics = {
        "chunks_scanned": 0,
        "candidate_titles_found": 0,
        "parser_noise_rejected": 0,
        "high_match": 0,
        "review_match": 0,
        "no_match": 0
    }
    
    candidates = []
    
    if chunks_dir.exists():
        for jsonl_file in chunks_dir.glob("*.jsonl"):
            book_name = jsonl_file.stem
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for row_idx, line in enumerate(f):
                    if not line.strip(): continue
                    metrics["chunks_scanned"] += 1
                    try:
                        data = json.loads(line)
                        text = data.get("chunk_text", "") or data.get("text", "")
                    except:
                        text = line
                    
                    lines = text.split('\n')
                    current_cand = None
                    
                    for l in lines:
                        l = l.strip()
                        if not l: continue
                        
                        matched_dist, reason = is_valid_title(l, distilleries)
                        if matched_dist:
                            if current_cand:
                                candidates.append(current_cand)
                            current_cand = {
                                "book_source": book_name,
                                "candidate_title": l,
                                "possible_distillery": matched_dist,
                                "body_lines": [],
                                "parser_reason": "Matched Title"
                            }
                            metrics["candidate_titles_found"] += 1
                        else:
                            if current_cand:
                                current_cand["body_lines"].append(l)
                            else:
                                metrics["parser_noise_rejected"] += 1
                                
                    if current_cand:
                        candidates.append(current_cand)

    out_rows = []
    
    for cand in candidates:
        title = cand["candidate_title"]
        dist = cand["possible_distillery"]
        body = " ".join(cand["body_lines"]).lower()
        
        has_nose = "nose" in body
        has_palate = "palate" in body or "taste" in body
        has_finish = "finish" in body
        style_summary_present = len(body) > 100
        
        age = extract_age(title) or extract_age(body)
        abv = extract_abv(title) or extract_abv(body)
        
        expr = title.lower().replace(dist.lower(), "")
        nexpr_tokens = set(normalize_text(expr).split())
        
        best_score = -1
        best_match = None
        
        for dbw in db_whiskies:
            if dbw["dist"] == dist:
                score = score_match(nexpr_tokens, age, dbw)
                if score > best_score:
                    best_score = score
                    best_match = dbw
                    
        match_status = "NO_MATCH"
        if best_score >= 0.85:
            match_status = "HIGH"
            metrics["high_match"] += 1
        elif best_score >= 0.60:
            match_status = "REVIEW"
            metrics["review_match"] += 1
        else:
            metrics["no_match"] += 1
            
        out_rows.append({
            "book_source": cand["book_source"],
            "candidate_title": title,
            "possible_distillery": dist,
            "candidate_type": "expression",
            "age": age or "",
            "abv": abv or "",
            "has_nose": has_nose,
            "has_palate": has_palate,
            "has_finish": has_finish,
            "style_summary_present": style_summary_present,
            "title_confidence": "HIGH",
            "body_confidence": "HIGH" if style_summary_present else "LOW",
            "match_status": match_status,
            "best_match_whisky_id": best_match["id"] if best_match else "",
            "best_match_name": best_match["name"] if best_match else "",
            "match_score": round(best_score, 3) if best_match else "",
            "parser_reason": cand["parser_reason"],
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
    
    md = f"""# 12U Book Entry Boundary Parser Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Chunks Scanned:** {metrics["chunks_scanned"]}
- **Candidate Titles Found:** {metrics["candidate_titles_found"]}
- **Parser Noise Rejected (Lines):** {metrics["parser_noise_rejected"]}

## Match Breakdown
- **High Match:** {metrics["high_match"]}
- **Review Match:** {metrics["review_match"]}
- **No Match:** {metrics["no_match"]}

## Top Distilleries
{top_dists}
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write("REVIEW")

if __name__ == "__main__":
    main()

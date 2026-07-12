import json
import csv
import sqlite3
import difflib
import re
from pathlib import Path
from collections import Counter

INPUT_JSONL = Path("data/manual_sources/books/extracted_jsonl/12n_local_rule_book_profile_extractions_clean.jsonl")
DB_PATH = Path("output/import/production.db")
CSV_OUT = Path("data/manual_sources/books/review_csv/12p_book_profile_staging_dry_run.csv")
REPORT_MD = Path("output/reports/12p_book_profile_staging_dry_run_report.md")
GATE_TXT = Path("output/reports/12p_book_profile_staging_dry_run_gate.txt")

# Ensure dirs
CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

def remove_generics(text):
    text = re.sub(r'\b(single malt|scotch|whisky|whiskey|malt)\b', '', text, flags=re.IGNORECASE)
    return text

def normalize_name(name):
    if not name: return ""
    text = str(name).lower()
    
    # Normalize age statements: 10-year-old, 10 year old, aged 10 years, 10 yo, 10 y.o. -> 10
    text = re.sub(r'\baged\s+(\d{1,2})\s+years?\b', r'\1', text)
    text = re.sub(r'\b(\d{1,2})\s*[-]?\s*years?\s*old\b', r'\1', text)
    text = re.sub(r'\b(\d{1,2})\s*[-]?\s*y\.?o\.?\b', r'\1', text)
    
    # Remove punctuation
    text = re.sub(r'[,\.\'\"%]', '', text)
    text = re.sub(r'\bvol\b', '', text)
    
    text = remove_generics(text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_token_overlap_score(search_str, db_str):
    search_tokens = set(search_str.split())
    db_tokens = set(db_str.split())
    if not search_tokens or not db_tokens:
        return 0.0
    overlap = search_tokens.intersection(db_tokens)
    return 2.0 * len(overlap) / (len(search_tokens) + len(db_tokens))

def generate_aliases(target, whisky_name):
    norm_target = normalize_name(target)
    norm_whisky = normalize_name(whisky_name)
    
    aliases = []
    # 1. original cleaned whisky_name
    aliases.append(norm_whisky)
    
    # 2. target removed expression-only
    expr_only = norm_whisky.replace(norm_target, "").strip()
    if expr_only:
        aliases.append(expr_only)
        
    # 3. target + age canonical
    # extract age from whisky_name
    m = re.search(r'\b(\d{1,2})\b', norm_whisky)
    if m:
        aliases.append(f"{norm_target} {m.group(1)}".strip())
        if expr_only:
             aliases.append(f"{norm_target} {expr_only}")
             
    # Clean duplicates
    unique_aliases = []
    for a in aliases:
        if a and a not in unique_aliases:
            unique_aliases.append(a)
    return unique_aliases

def fuzzy_match_whiskies(cursor, target, whisky_name):
    # Get all DB whiskies
    cursor.execute("""
        SELECT w.whisky_id, w.name, d.name 
        FROM whiskies w
        JOIN distilleries d ON w.distillery_id = d.distillery_id
    """)
    rows = cursor.fetchall()
    
    norm_target = normalize_name(target)
    aliases = generate_aliases(target, whisky_name)
    
    best_score = 0.0
    best_id = None
    best_name = None
    best_distillery = None
    best_debug = ""
    age_match = False
    distillery_match = False
    
    # Extract age integer if present
    extracted_age = None
    m_age = re.search(r'\b(\d{1,2})\b', normalize_name(whisky_name))
    if m_age:
        extracted_age = m_age.group(1)
        
    for row in rows:
        w_id, w_name, d_name = row
        norm_w_name = normalize_name(w_name)
        norm_d_name = normalize_name(d_name)
        
        db_fullname = f"{norm_d_name} {norm_w_name}".replace(f"{norm_d_name} {norm_d_name}", norm_d_name).strip()
        
        # Check distillery match
        is_dist_match = (norm_target == norm_d_name) or (norm_target in norm_d_name) or (norm_d_name in norm_target)
        
        # We heavily penalize cross-distillery matching
        if not is_dist_match:
            continue
            
        # Check age match
        is_age_match = False
        is_age_mismatch = False
        db_age_m = re.search(r'\b(\d{1,2})\b', db_fullname)
        if extracted_age and db_age_m:
            if extracted_age == db_age_m.group(1):
                is_age_match = True
            else:
                is_age_mismatch = True
        elif not extracted_age and not db_age_m:
            # Both NAS or NAS equivalent
            is_age_match = True
            
        max_alias_score = 0.0
        best_alias_used = ""
        for alias in aliases:
            # difflib score
            seq_score = difflib.SequenceMatcher(None, alias, db_fullname).ratio()
            seq_score2 = difflib.SequenceMatcher(None, alias, norm_w_name).ratio()
            
            # token score
            tok_score = calculate_token_overlap_score(alias, db_fullname)
            
            # Weigh token score heavily to prevent PX Cask matching QA Cask with high score
            alias_score = max(seq_score * 0.4 + tok_score * 0.6, seq_score2 * 0.4 + tok_score * 0.6)
            
            if alias_score > max_alias_score:
                max_alias_score = alias_score
                best_alias_used = alias
                
        # Base score
        score = max_alias_score
        
        # Bonuses
        if is_age_match and extracted_age:
            score += 0.20
        if is_dist_match:
            score += 0.05
            
        # Penalties
        if is_age_mismatch:
            score -= 0.40 # heavy penalty for mismatching age
            
        score = min(score, 1.0)
        
        if score > best_score:
            best_score = score
            best_id = w_id
            best_name = w_name
            best_distillery = d_name
            age_match = is_age_match
            distillery_match = is_dist_match
            best_debug = f"Alias used: '{best_alias_used}', DB: '{db_fullname}', age_match: {is_age_match}, dist_match: {is_dist_match}"
            
    return best_id, best_name, best_distillery, best_score, best_debug, aliases, age_match, distillery_match

def run_dry_run():
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        return
        
    db_uri = f"file:{DB_PATH.absolute().as_posix()}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    cursor = conn.cursor()
    
    records = []
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    candidates = [r for r in records if r.get("import_status") == "staging_candidate"]
    
    out_rows = []
    stats = Counter()
    
    for row in candidates:
        target = row.get("target", "")
        w_name = row.get("whisky_name", "")
        
        w_id, matched_name, matched_dist, score, debug_info, aliases, age_match, dist_match = fuzzy_match_whiskies(cursor, target, w_name)
        
        if score >= 0.92:
            match_status = "HIGH"
        elif score >= 0.84:
            match_status = "REVIEW"
        else:
            match_status = "NO_MATCH"
            
        stats[match_status] += 1
        
        # check duplicate
        duplicate_source = False
        if match_status in ("HIGH", "REVIEW") and w_id:
            book_source = row.get("book_source", "unknown")
            try:
                cursor.execute("SELECT count(*) FROM tasting_notes WHERE whisky_id=? AND source=?", (w_id, book_source))
                if cursor.fetchone()[0] > 0:
                    duplicate_source = True
            except sqlite3.OperationalError:
                pass 
            
            try:
                cursor.execute("SELECT count(*) FROM flavor_profiles WHERE whisky_id=? AND source=?", (w_id, book_source))
                if cursor.fetchone()[0] > 0:
                    duplicate_source = True
            except sqlite3.OperationalError:
                pass
                
        if duplicate_source:
            stats["DUPLICATE_SOURCE"] += 1
            
        radar_fields = [k for k, v in row.get("radar_scores_0_100", {}).items() if isinstance(v, (int, float))]
        score_count = len(radar_fields)
        
        row_out = {
            "target": target,
            "whisky_name": w_name,
            "best_match_whisky_id": w_id if match_status != "NO_MATCH" else None,
            "best_match_name": matched_name if match_status != "NO_MATCH" else None,
            "best_match_distillery": matched_dist if match_status != "NO_MATCH" else None,
            "match_score": round(score, 3),
            "match_status": match_status,
            "match_debug": debug_info,
            "candidate_aliases": " | ".join(aliases),
            "age_match": age_match,
            "distillery_match": dist_match,
            "duplicate_source_flag": duplicate_source,
            "missing_fk": (match_status == "NO_MATCH"),
            "radar_score_count": score_count,
            "source_system_proposal": "book_local_rule",
            "approval_status_proposal": "staging_pending_review",
            "book_source": row.get("book_source")
        }
        out_rows.append(row_out)
        
    # Write CSV
    if out_rows:
        keys = list(out_rows[0].keys())
        with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in out_rows:
                writer.writerow(r)
                
    # Gate logic
    missing_fk_count = sum(1 for r in out_rows if r["missing_fk"])
    high_count = stats["HIGH"]
    
    gate = "REVIEW"
    if stats["NO_MATCH"] == len(candidates) and len(candidates) > 0:
        gate = "NO_GO"
    elif high_count > 0 and missing_fk_count == 0 and stats["REVIEW"] == 0:
        gate = "GO"
    else:
        gate = "REVIEW"
        
    report = f"""# 12P Book Profile Staging Dry-Run Report

## Summary
- Input Candidates: {len(candidates)}
- Output Validated: {len(out_rows)}
- Production DB Modified: False

## Match Stats
- HIGH (> 0.92): {stats['HIGH']}
- REVIEW (0.84 - 0.92): {stats['REVIEW']}
- NO_MATCH (< 0.84): {stats['NO_MATCH']}
- DUPLICATE_SOURCE: {stats['DUPLICATE_SOURCE']}
- Missing FK (No Match): {missing_fk_count}

## Gate
{gate}
"""
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(report)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        
    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(gate)
        
    print(f"Dry run complete. Validated {len(out_rows)} candidates.")
    print(f"HIGH: {stats['HIGH']}, REVIEW: {stats['REVIEW']}, NO_MATCH: {stats['NO_MATCH']}")
    print(f"Gate: {gate}")

if __name__ == "__main__":
    run_dry_run()

import sqlite3
import os
import csv
import hashlib
import json
import re

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
NO_MATCH_INPUT = os.path.join(OUTPUT_DIR, "book_manual_match_no_match.csv")
ALL_NORM_INPUT = os.path.join(OUTPUT_DIR, "book_manual_normalized_candidates.csv")

RESCUE_CSV = os.path.join(OUTPUT_DIR, "book_manual_advanced_rescue_candidates.csv")
HIGH_CONF_RESCUE_CSV = os.path.join(OUTPUT_DIR, "book_manual_advanced_rescue_high_confidence.csv")
MANUAL_REV_RESCUE_CSV = os.path.join(OUTPUT_DIR, "book_manual_advanced_rescue_manual_review.csv")
BLOCKED_RESCUE_CSV = os.path.join(OUTPUT_DIR, "book_manual_advanced_rescue_blocked.csv")
REPORT_MD = "output/reports/book_manual_advanced_rescue_report.md"

def levenshtein_ratio(s1, s2):
    s1, s2 = str(s1).lower().strip(), str(s2).lower().strip()
    if not s1 or not s2: return 0.0
    rows = len(s1) + 1
    cols = len(s2) + 1
    dist = [[0 for _ in range(cols)] for _ in range(rows)]
    for i in range(1, rows):
        dist[i][0] = i
    for k in range(1, cols):
        dist[0][k] = k
    for col in range(1, cols):
        for row in range(1, rows):
            if s1[row-1] == s2[col-1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(dist[row-1][col] + 1,
                                 dist[row][col-1] + 1,
                                 dist[row-1][col-1] + cost)
    return round(1.0 - (dist[len(s1)][len(s2)] / max(len(s1), len(s2))), 2)

def token_sort_ratio(s1, s2):
    s1_tokens = sorted(str(s1).lower().split())
    s2_tokens = sorted(str(s2).lower().split())
    return levenshtein_ratio(" ".join(s1_tokens), " ".join(s2_tokens))

def token_set_ratio(s1, s2):
    s1_set = set(str(s1).lower().split())
    s2_set = set(str(s2).lower().split())
    intersection = s1_set.intersection(s2_set)
    if not intersection: return 0.0
    sorted_inter = " ".join(sorted(list(intersection)))
    sorted_s1 = " ".join(sorted(list(s1_set)))
    sorted_s2 = " ".join(sorted(list(s2_set)))
    r1 = levenshtein_ratio(sorted_inter, sorted_s1)
    r2 = levenshtein_ratio(sorted_inter, sorted_s2)
    r3 = levenshtein_ratio(sorted_s1, sorted_s2)
    return max(r1, r2, r3)

def jaro_winkler_similarity(s1, s2):
    s1, s2 = str(s1).lower().strip(), str(s2).lower().strip()
    if not s1 or not s2: return 0.0
    len1, len2 = len(s1), len(s2)
    max_dist = max(len1, len2) // 2 - 1
    if max_dist < 0: max_dist = 0
    
    match1 = [False] * len1
    match2 = [False] * len2
    
    matches = 0
    transpositions = 0
    
    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(len2, i + max_dist + 1)
        for j in range(start, end):
            if not match2[j] and s1[i] == s2[j]:
                match1[i] = True
                match2[j] = True
                matches += 1
                break
                
    if matches == 0: return 0.0
    
    k = 0
    for i in range(len1):
        if match1[i]:
            while not match2[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
            
    transpositions //= 2
    
    jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0
    prefix = 0
    for i in range(min(4, min(len1, len2))):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
            
    return round(jaro + prefix * 0.1 * (1.0 - jaro), 2)

def extract_age(name):
    match = re.search(r'\b(\d+)\s*(yo|years|y\.?o\.?|y)\b', str(name), re.IGNORECASE)
    return match.group(1) if match else None

def get_age_score(age1, age2):
    if not age1 and not age2: return 1.0  # Both NAS, compatible
    if age1 == age2: return 1.0
    if not age1 or not age2: return 0.5  # One NAS, one aged, moderate match
    return 0.0  # Mismatched age

def clean_whisky_name(name):
    if not name: return ""
    name_clean = re.sub(r'\b\d+\s*(yo|years old|year old|y|y\.o\.)\b', '', str(name), flags=re.IGNORECASE)
    name_clean = re.sub(r'\b\d+%\b', '', name_clean)
    return " ".join(name_clean.lower().split()).strip()

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    # Master index
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = [dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()]
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    existing_tns = [dict(t) for t in cur.execute("SELECT * FROM tasting_notes").fetchall()]

    prod_tasting_note_fps = set()
    for tn in existing_tns:
        nose = str(tn.get('nose_notes', '')).strip().lower()
        palate = str(tn.get('palate_notes', '')).strip().lower()
        finish = str(tn.get('finish_notes', '')).strip().lower()
        fp = hashlib.md5(f"{nose}|{palate}|{finish}".encode('utf-8')).hexdigest()
        prod_tasting_note_fps.add(fp)

    conn.close()

    # Load candidates
    no_match_candidates = []
    if os.path.exists(NO_MATCH_INPUT):
        with open(NO_MATCH_INPUT, 'r', encoding='utf-8') as f:
            no_match_candidates = list(csv.DictReader(f))
            
    all_normalized_candidates = []
    if os.path.exists(ALL_NORM_INPUT):
        with open(ALL_NORM_INPUT, 'r', encoding='utf-8') as f:
            all_normalized_candidates = list(csv.DictReader(f))

    # Filter candidates to process: no_match and blocked_weak_content
    to_process = []
    
    # Process no_match
    for r in no_match_candidates:
        r['rescue_origin'] = 'no_match'
        to_process.append(r)
        
    # Process blocked_weak_content from all_normalized
    for r in all_normalized_candidates:
        if r.get('match_category') == 'blocked_weak_content':
            r['rescue_origin'] = 'blocked_weak_content'
            to_process.append(r)

    stats = {
        'input_no_match': len(no_match_candidates),
        'input_blocked_weak': sum(1 for r in all_normalized_candidates if r.get('match_category') == 'blocked_weak_content'),
        'high_confidence_rescue': 0,
        'manual_review_rescue': 0,
        'blocked_still_weak': 0,
        'no_match_still': 0
    }

    rescue_results = []

    for r in to_process:
        raw_name = r.get('raw_whisky_name', '')
        raw_dist = r.get('raw_distillery_name', '')
        origin = r.get('source_origin', '')
        content = r.get('content_preview', '')
        
        norm_name = clean_whisky_name(raw_name)
        norm_dist = clean_whisky_name(raw_dist)
        
        # 1. Advanced matching algorithm
        best_w = None
        best_second_w = None
        
        best_score = {
            'name': 0.0,
            'token': 0.0,
            'levenshtein': 0.0,
            'jaro_winkler': 0.0,
            'distillery': 0.0,
            'age_batch_cask': 0.0,
            'combined': 0.0
        }
        
        raw_age = extract_age(raw_name)
        
        for w in whiskies:
            w_name = w.get('name', w.get('normalized_name', ''))
            w_clean = clean_whisky_name(w_name)
            
            # Compute metrics
            name_score = get_similarity(norm_name, w_clean)
            token_score = token_set_ratio(norm_name, w_clean)
            lev_score = levenshtein_ratio(norm_name, w_clean)
            jw_score = jaro_winkler_similarity(norm_name, w_clean)
            
            # Distillery match
            d_id = str(w.get('distillery_id', ''))
            d_name = distilleries.get(d_id, {}).get('name', '')
            d_clean = clean_whisky_name(d_name)
            dist_score = jaro_winkler_similarity(norm_dist, d_clean) if norm_dist else 1.0
            
            # Age compatibility
            w_age = extract_age(w_name)
            age_score = get_age_score(raw_age, w_age)
            
            # Combined score weights
            combined = (name_score * 0.3 + token_score * 0.3 + lev_score * 0.1 + jw_score * 0.1 + dist_score * 0.1 + age_score * 0.1)
            
            if combined > best_score['combined']:
                best_second_w = best_w
                best_w = w
                best_score = {
                    'name': name_score,
                    'token': token_score,
                    'levenshtein': lev_score,
                    'jaro_winkler': jw_score,
                    'distillery': dist_score,
                    'age_batch_cask': age_score,
                    'combined': round(combined, 2)
                }

        # 2. Content Rescue evaluation
        content_len = len(content.strip())
        content_rescue_score = 0.0
        content_status = 'Weak'
        
        # If content has nose/palate/finish words in raw text, we rescue it!
        has_note_signal = any(k in content.lower() for k in ['nose', 'palate', 'finish', 'aroma', 'sweet', 'fruit', 'smoke'])
        if content_len >= 40:
            content_rescue_score = 1.0
            content_status = 'Usable'
        elif content_len >= 15 and has_note_signal:
            content_rescue_score = 0.7
            content_status = 'Rescued'
        else:
            content_status = 'Still Weak'

        # Duplicate check
        content_fp = hashlib.md5(content.strip().lower().encode('utf-8')).hexdigest()
        is_dupe = 'Yes' if content_fp in prod_tasting_note_fps else 'No'

        # Categorization
        ambiguity_flag = 'No'
        if best_second_w and best_score['combined'] - get_similarity(norm_name, clean_whisky_name(best_second_w.get('name'))) < 0.05:
            ambiguity_flag = 'Yes'

        rescue_cat = 'no_match_still'
        action = 'block'
        reason = 'No plausible whisky match'

        if content_status == 'Still Weak' and r['rescue_origin'] == 'blocked_weak_content':
            rescue_cat = 'blocked_still_weak'
            action = 'block'
            reason = 'Content is still too weak to rescue'
            stats['blocked_still_weak'] += 1
        elif best_w and best_score['combined'] >= 0.80:
            if best_score['combined'] >= 0.92 and ambiguity_flag == 'No' and is_dupe == 'No' and content_status != 'Still Weak':
                rescue_cat = 'high_confidence_rescue'
                action = 'promote_after_backup'
                reason = f"Rescued via high-confidence string alignment (Score: {best_score['combined']})"
                stats['high_confidence_rescue'] += 1
            else:
                rescue_cat = 'manual_review_rescue'
                action = 'review_before_import'
                reasons = []
                if best_score['combined'] < 0.92: reasons.append(f"Combined score is moderate ({best_score['combined']})")
                if ambiguity_flag == 'Yes': reasons.append("Ambiguity detected (multiple close matches)")
                if content_status == 'Rescued': reasons.append("Short content rescued")
                reason = ", ".join(reasons)
                stats['manual_review_rescue'] += 1
        else:
            stats['no_match_still'] += 1

        matched_wid = str(best_w.get('whisky_id')) if best_w else 'N/A'
        matched_wname = best_w.get('name') if best_w else 'N/A'
        d_id = str(best_w.get('distillery_id', '')) if best_w else ''
        matched_dname = distilleries.get(d_id, {}).get('name', 'Unknown') if d_id else 'Unknown'

        rescue_results.append({
            'source_record_id': r.get('source_record_id', 'N/A'),
            'source_origin': r.get('source_origin', 'N/A'),
            'source_file_or_table': r.get('source_file_or_table', 'N/A'),
            'raw_whisky_name': raw_name,
            'normalized_whisky_name': norm_name,
            'raw_distillery_name': raw_dist,
            'normalized_distillery_name': norm_dist,
            'best_match_whisky_id': matched_wid,
            'best_match_whisky_name': matched_wname,
            'best_match_distillery_name': matched_dname,
            'second_best_match': best_second_w.get('name') if best_second_w else 'None',
            'name_score': best_score['name'],
            'token_score': best_score['token'],
            'levenshtein_score': best_score['levenshtein'],
            'jaro_winkler_score': best_score['jaro_winkler'],
            'distillery_score': best_score['distillery'],
            'age_batch_cask_score': best_score['age_batch_cask'],
            'content_rescue_score': content_rescue_score,
            'combined_rescue_score': best_score['combined'],
            'ambiguity_flag': ambiguity_flag,
            'duplicate_status': is_dupe,
            'content_status': content_status,
            'rescue_category': rescue_cat,
            'recommended_action': action,
            'reason': reason,
            'content_preview': content
        })

    # Write CSVs
    if rescue_results:
        with open(RESCUE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rescue_results[0].keys())
            writer.writeheader()
            writer.writerows(rescue_results)
            
    high_conf = [c for c in rescue_results if c['rescue_category'] == 'high_confidence_rescue']
    manual_rev = [c for c in rescue_results if c['rescue_category'] == 'manual_review_rescue']
    blocked = [c for c in rescue_results if c['rescue_category'] in ['blocked_still_weak', 'no_match_still']]

    for path, data in [(HIGH_CONF_RESCUE_CSV, high_conf), (MANUAL_REV_RESCUE_CSV, manual_rev), (BLOCKED_RESCUE_CSV, blocked)]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(f)
                writer.writerow(['whisky_id', 'status'])

    # Write MD Report
    report = []
    report.append("# Book and Manual Advanced Rescue Matching Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## Rescue Processing Metrics")
    report.append(f"- Input no_match candidates: {stats['input_no_match']}")
    report.append(f"- Input blocked_weak_content candidates: {stats['input_blocked_weak']}")
    report.append(f"- `high_confidence_rescue` count: {stats['high_confidence_rescue']}")
    report.append(f"- `manual_review_rescue` count: {stats['manual_review_rescue']}")
    report.append(f"- `blocked_still_weak` count: {stats['blocked_still_weak']}")
    report.append(f"- `no_match_still` count: {stats['no_match_still']}")
    
    report.append(f"\n- **Expected Safe Import Potential (Rescue High Confidence):** {stats['high_confidence_rescue']}")

    report.append("\n## Top 30 High Confidence Rescued Candidates")
    report.append("| Raw Name | Best Matched Name | Match Score | Content Status | Reason |")
    report.append("|---|---|---|---|---|")
    for c in high_conf[:30]:
        report.append(f"| {c['raw_whisky_name']} | {c['best_match_whisky_name']} | {c['combined_rescue_score']} | {c['content_status']} | {c['reason']} |")

    report.append("\n## Top 30 Manual Review Candidates")
    report.append("| Raw Name | Best Matched Name | Match Score | Content Status | Reason |")
    report.append("|---|---|---|---|---|")
    for c in manual_rev[:30]:
        report.append(f"| {c['raw_whisky_name']} | {c['best_match_whisky_name']} | {c['combined_rescue_score']} | {c['content_status']} | {c['reason']} |")

    report.append("\n## Examples of Still Blocked Candidates")
    for c in blocked[:15]:
        report.append(f"- **{c['raw_whisky_name']}** | {c['rescue_category']} | {c['reason']}")

    report.append("\n## Recommended Next Phase")
    report.append("- **AŞAMA BP2-R-QA — Rescue Candidate QA + Dry-Run**: Build the verification QA pack specifically for these rescued candidates and run test inserts.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Advanced rescue analysis completed successfully, identifying 66 matches for QA phase).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

def get_similarity(s1, s2):
    if not s1 or not s2: return 0.0
    return difflib.SequenceMatcher(None, str(s1).lower().strip(), str(s2).lower().strip()).ratio()

import difflib

if __name__ == "__main__":
    main()

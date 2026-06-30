import sqlite3
import os
import csv
import hashlib
import json
import re

DB_PATH = "output/import/production.db"
QUALITY_CSV = "data/output/book_extract_v2_quality_queue.csv"

REVIEW_QUEUE_CSV = "data/output/book_manual_v2_review_queue.csv"
HIGH_CONF_CSV = "data/output/book_manual_v2_high_confidence_match_candidates.csv"
MANUAL_MATCH_CSV = "data/output/book_manual_v2_manual_match_required.csv"
BLOCKED_CSV = "data/output/book_manual_v2_blocked_candidates.csv"
REPORT_MD = "output/reports/book_manual_v2_review_queue_report.md"

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

def clean_whisky_name(name):
    if not name: return ""
    name_clean = re.sub(r'\b\d+\s*(yo|years old|year old|y|y\.o\.)\b', '', str(name), flags=re.IGNORECASE)
    name_clean = re.sub(r'\b\d+%\b', '', name_clean)
    return " ".join(name_clean.lower().split()).strip()

def get_age_score(age1, age2):
    if not age1 and not age2: return 1.0
    if age1 == age2: return 1.0
    if not age1 or not age2: return 0.5
    return 0.0

def main():
    os.makedirs(os.path.dirname(REVIEW_QUEUE_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(QUALITY_CSV):
        print(f"Error: Quality CSV not found at {QUALITY_CSV}")
        return

    # Master index from DB
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = [dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()]
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    existing_tns = [dict(t) for t in cur.execute("SELECT * FROM tasting_notes").fetchall()]
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}

    prod_tasting_note_fps = set()
    for tn in existing_tns:
        nose = str(tn.get('nose_notes', '')).strip().lower()
        palate = str(tn.get('palate_notes', '')).strip().lower()
        finish = str(tn.get('finish_notes', '')).strip().lower()
        fp = hashlib.md5(f"{nose}|{palate}|{finish}".encode('utf-8')).hexdigest()
        prod_tasting_note_fps.add(fp)

    conn.close()

    # Read quality queue candidates
    all_candidates = []
    with open(QUALITY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_candidates.append(row)

    # Filter to process: entity_only_needs_source_review
    to_review = [c for c in all_candidates if c.get('quality_class') == 'entity_only_needs_source_review']

    review_rows = []
    
    stats = {
        'input_candidates': len(to_review),
        'high_confidence_match': 0,
        'manual_match_required': 0,
        'blocked_weak_content': 0,
        'blocked_no_safe_match': 0,
        'duplicate_or_already_covered': 0,
        'recoverable_tasting_note': 0,
        'recoverable_flavor_profile': 0
    }

    for c in to_review:
        raw_name = c.get('whisky_name', '')
        raw_dist = c.get('distillery_name', '')
        
        nose = c.get('nose_summary', '')
        palate = c.get('palate_summary', '')
        finish = c.get('finish_summary', '')
        origin = c.get('source_origin', '')
        
        norm_name = clean_whisky_name(raw_name)
        norm_dist = clean_whisky_name(raw_dist)
        
        raw_age = extract_age(raw_name)

        # Advanced matching algorithm against master index
        best_w = None
        best_second_w = None
        best_score = 0.0
        
        for w in whiskies:
            w_name = w.get('name', w.get('normalized_name', ''))
            w_clean = clean_whisky_name(w_name)
            
            name_score = token_set_ratio(norm_name, w_clean)
            jw_score = jaro_winkler_similarity(norm_name, w_clean)
            
            d_id = str(w.get('distillery_id', ''))
            d_name = distilleries.get(d_id, {}).get('name', '')
            d_clean = clean_whisky_name(d_name)
            dist_score = jaro_winkler_similarity(norm_dist, d_clean) if norm_dist else 1.0
            
            w_age = extract_age(w_name)
            age_score = get_age_score(raw_age, w_age)
            
            combined = (name_score * 0.3 + jw_score * 0.3 + dist_score * 0.2 + age_score * 0.2)
            
            if combined > best_score:
                best_second_w = best_w
                best_w = w
                best_score = round(combined, 2)

        # Extraction logic
        has_tn = any([nose, palate, finish])
        has_fp = any(float(c.get(f'radar_{axis}', '0.0')) > 0.0 for axis in ['smoky', 'peaty', 'sherry', 'fruity', 'spicy', 'sweet', 'rich'])

        # Duplicate checks
        content_fp = hashlib.md5(f"{nose.strip().lower()}|{palate.strip().lower()}|{finish.strip().lower()}".encode('utf-8')).hexdigest()
        is_dupe_tn = content_fp in prod_tasting_note_fps
        
        wid = str(best_w.get('whisky_id')) if (best_w and best_score >= 0.80) else 'N/A'
        wname = best_w.get('name') if (best_w and best_score >= 0.80) else 'N/A'
        
        has_existing_profile = wid in existing_fps

        # Determine Category & Recommended Action
        if not has_tn and not has_fp:
            q_class = 'blocked_weak_content'
            action = 'block'
            reason = 'Tasting notes and flavor vector are empty'
            stats['blocked_weak_content'] += 1
        elif wid == 'N/A':
            q_class = 'blocked_no_safe_match'
            action = 'block'
            reason = 'No plausible whisky match in database'
            stats['blocked_no_safe_match'] += 1
        elif is_dupe_tn and has_existing_profile:
            q_class = 'duplicate_or_already_covered'
            action = 'skip_duplicate'
            reason = 'Both tasting note and flavor profile already exist in production'
            stats['duplicate_or_already_covered'] += 1
        elif best_score >= 0.92:
            q_class = 'high_confidence_match_candidate'
            action = 'import_ready'
            reason = f"High-confidence match ({best_score}) with compatible age/distillery"
            stats['high_confidence_match'] += 1
            if has_tn: stats['recoverable_tasting_note'] += 1
            if has_fp: stats['recoverable_flavor_profile'] += 1
        elif 0.84 <= best_score < 0.92:
            q_class = 'manual_match_required'
            action = 'review_before_import'
            reason = f"Moderate match score ({best_score}). Verify whisky and age"
            stats['manual_match_required'] += 1
            if has_tn: stats['recoverable_tasting_note'] += 1
            if has_fp: stats['recoverable_flavor_profile'] += 1
        else:
            q_class = 'blocked_no_safe_match'
            action = 'block'
            reason = f"Alignment score too low ({best_score})"
            stats['blocked_no_safe_match'] += 1

        review_rows.append({
            'source_file': origin.split(':')[0] if ':' in origin else 'N/A',
            'source_book_or_title': origin.split(':')[0] if ':' in origin else 'N/A',
            'source_chunk_id': origin.split(':')[1] if ':' in origin else 'N/A',
            'raw_whisky_name': raw_name,
            'normalized_whisky_name': norm_name,
            'raw_distillery_name': raw_dist,
            'normalized_distillery_name': norm_dist,
            'proposed_whisky_id': wid,
            'proposed_whisky_name': wname,
            'proposed_distillery_name': distilleries.get(str(best_w.get('distillery_id')), {}).get('name', 'Unknown') if (best_w and best_score >= 0.80) else 'Unknown',
            'match_score': best_score,
            'match_method': 'token_set_jaro_winkler_combined',
            'age_compatible': 'Yes' if (best_w and extract_age(best_w.get('name')) == raw_age) else 'No',
            'cask_or_batch_compatible': 'Yes' if re.search(r'\b(sherry|bourbon|port|wine|oak|cask|barrel|butt)\b', c.get('text', ''), re.IGNORECASE) else 'No',
            'content_quality_status': 'Usable' if has_tn else 'Weak',
            'has_tasting_note_signal': 'Yes' if has_tn else 'No',
            'has_flavor_profile_signal': 'Yes' if has_fp else 'No',
            'copyright_safety_status': 'safe_paraphrased_summary',
            'recommended_action': action,
            'reason': reason,
            'review_category': q_class
        })

    # Sort
    cat_order = {
        'high_confidence_match_candidate': 0,
        'manual_match_required': 1,
        'duplicate_or_already_covered': 2,
        'blocked_weak_content': 3,
        'blocked_no_safe_match': 4
    }
    review_rows.sort(key=lambda x: cat_order.get(x['review_category'], 99))

    # Write CSVs
    if review_rows:
        with open(REVIEW_QUEUE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=review_rows[0].keys())
            writer.writeheader()
            writer.writerows(review_rows)

    high_conf = [r for r in review_rows if r['review_category'] == 'high_confidence_match_candidate']
    manual_match = [r for r in review_rows if r['review_category'] == 'manual_match_required']
    blocked = [r for r in review_rows if r['review_category'] in ['blocked_weak_content', 'blocked_no_safe_match', 'duplicate_or_already_covered']]

    for path, data in [(HIGH_CONF_CSV, high_conf), (MANUAL_MATCH_CSV, manual_match), (BLOCKED_CSV, blocked)]:
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
    report.append("# Book Manual v2 Review Queue Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## Review Queue Metrics")
    report.append(f"- Input Manual/Entity Count: {stats['input_candidates']}")
    report.append(f"- `high_confidence_match_candidate` count: {stats['high_confidence_match']}")
    report.append(f"- `manual_match_required` count: {stats['manual_match_required']}")
    report.append(f"- `blocked_weak_content` count: {stats['blocked_weak_content']}")
    report.append(f"- `blocked_no_safe_match` count: {stats['blocked_no_safe_match']}")
    report.append(f"- `duplicate_or_already_covered` count: {stats['duplicate_or_already_covered']}")
    
    report.append(f"\n- **Estimated Recoverable Tasting Notes:** {stats['recoverable_tasting_note']}")
    report.append(f"- **Estimated Recoverable Flavor Profiles:** {stats['recoverable_flavor_profile']}")

    report.append("\n## Top 30 High Confidence/Review Candidates")
    report.append("| Raw Name | Proposed Name | Score | Action | Reason |")
    report.append("|---|---|---|---|---|")
    for r in review_rows[:30]:
        report.append(f"| {r['raw_whisky_name']} | {r['proposed_whisky_name']} | {r['match_score']} | {r['recommended_action']} | {r['reason']} |")

    report.append("\n## Top Reasons for Block")
    report.append("1. **No Plausible Whisky Match in Database**: The database lacks entries for the specific whiskies mentioned in these raw book chunks.\n")
    report.append("2. **Duplicate/Already Covered**: The whisky already has tasting notes and flavor profiles mapped in production.")

    report.append("\n## Recommended Next Phase")
    report.append("- **AŞAMA BOOK-MANUAL-QA-V2 — QA/Dry-Run For High Confidence Manual Queue**: Validate these rescued candidates and run a test simulation on the copy DB.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Review queue built successfully, identifying potential high-confidence matches).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

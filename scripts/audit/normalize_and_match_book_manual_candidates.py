import sqlite3
import os
import csv
import hashlib
import difflib

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
UNIFIED_INPUT = os.path.join(OUTPUT_DIR, "deep_book_manual_inventory_unified.csv")
UNMATCHED_INPUT = os.path.join(OUTPUT_DIR, "deep_book_manual_inventory_unmatched.csv")

NORM_CSV = os.path.join(OUTPUT_DIR, "book_manual_normalized_candidates.csv")
MATCH_CSV = os.path.join(OUTPUT_DIR, "book_manual_match_candidates.csv")
HIGH_CONF_CSV = os.path.join(OUTPUT_DIR, "book_manual_match_high_confidence.csv")
MANUAL_REV_CSV = os.path.join(OUTPUT_DIR, "book_manual_match_manual_review.csv")
NO_MATCH_CSV = os.path.join(OUTPUT_DIR, "book_manual_match_no_match.csv")
REPORT_MD = "output/reports/book_manual_normalize_match_report.md"

def get_similarity(s1, s2):
    if not s1 or not s2: return 0.0
    return difflib.SequenceMatcher(None, str(s1).lower().strip(), str(s2).lower().strip()).ratio()

def clean_whisky_name(name):
    if not name: return ""
    # Remove age patterns temporarily for base comparison
    name_clean = re.sub(r'\b\d+\s*(yo|years old|year old|y|y\.o\.)\b', '', str(name), flags=re.IGNORECASE)
    name_clean = re.sub(r'\b\d+%\b', '', name_clean)
    return " ".join(name_clean.lower().split()).strip()

import re

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Master index
    whiskies = [dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()]
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    existing_tns = [dict(t) for t in cur.execute("SELECT * FROM tasting_notes").fetchall()]
    
    # Hash existing production tasting notes content to detect duplicate fingerprints
    prod_tasting_note_fps = set()
    for tn in existing_tns:
        nose = str(tn.get('nose_notes', '')).strip().lower()
        palate = str(tn.get('palate_notes', '')).strip().lower()
        finish = str(tn.get('finish_notes', '')).strip().lower()
        fp = hashlib.md5(f"{nose}|{palate}|{finish}".encode('utf-8')).hexdigest()
        prod_tasting_note_fps.add(fp)

    conn.close()

    # Read inputs
    unified_records = []
    if os.path.exists(UNIFIED_INPUT):
        with open(UNIFIED_INPUT, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            unified_records = list(reader)
            
    unmatched_records = []
    if os.path.exists(UNMATCHED_INPUT):
        with open(UNMATCHED_INPUT, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            unmatched_records = list(reader)

    stats = {
        'total_input': len(unified_records) + len(unmatched_records),
        'already_in_production_excluded': 0,
        'normalized': 0,
        'high_confidence': 0,
        'manual_review': 0,
        'no_match': 0,
        'blocked_duplicate': 0,
        'blocked_weak': 0
    }

    normalized_candidates = []
    match_candidates = []

    # Map candidate sources
    # 1. Process Unified Mapped Candidates
    for idx, r in enumerate(unified_records):
        status = r.get('status')
        wid = r.get('whisky_id')
        
        if status == 'already_in_production':
            stats['already_in_production_excluded'] += 1
            continue
            
        raw_name = r.get('whisky_name', '')
        raw_dist = r.get('distillery_name', '')
        origin = r.get('source_origin', '')
        content = r.get('content_preview', '')
        
        stats['normalized'] += 1
        
        norm_name = clean_whisky_name(raw_name)
        norm_dist = clean_whisky_name(raw_dist)
        
        # Verify content fingerprint
        content_fp = hashlib.md5(content.strip().lower().encode('utf-8')).hexdigest()
        is_dupe = 'No'
        if content_fp in prod_tasting_note_fps:
            is_dupe = 'Yes'
            
        content_quality = 'Strong' if len(content.strip()) >= 40 else 'Weak'
        
        match_cat = 'high_confidence_match'
        action = 'promote_after_backup'
        reason = 'Already mapped via valid Staging whisky_id'
        
        # Override based on checks
        if is_dupe == 'Yes':
            match_cat = 'blocked_duplicate_fingerprint'
            action = 'skip_duplicate'
            reason = 'Content already exists in production tasting notes'
            stats['blocked_duplicate'] += 1
        elif content_quality == 'Weak':
            match_cat = 'blocked_weak_content'
            action = 'enrich_or_skip'
            reason = 'Content is too short'
            stats['blocked_weak'] += 1
        else:
            stats['high_confidence'] += 1

        match_row = {
            'source_record_id': f"unified_{idx}",
            'source_origin': origin,
            'source_file_or_table': origin.split(':')[0] if ':' in origin else origin,
            'source_system': 'book_manual',
            'source_name': 'NotebookLM' if 'notebook' in origin.lower() else 'CompleteGuide',
            'source_url': '',
            'raw_whisky_name': raw_name,
            'normalized_whisky_name': norm_name,
            'raw_distillery_name': raw_dist,
            'normalized_distillery_name': norm_dist,
            'matched_whisky_id': wid,
            'matched_whisky_name': raw_name,
            'matched_distillery_name': raw_dist,
            'whisky_match_score': 1.0,
            'distillery_match_score': 1.0,
            'combined_match_score': 1.0,
            'duplicate_status': is_dupe,
            'content_quality': content_quality,
            'match_category': match_cat,
            'recommended_action': action,
            'reason': reason,
            'content_preview': content
        }
        normalized_candidates.append(match_row)
        match_candidates.append(match_row)

    # 2. Process Unmatched Candidates (Require Algorithmic Alignment)
    for idx, r in enumerate(unmatched_records):
        raw_name = r.get('raw_whisky_name', '')
        raw_dist = r.get('raw_distillery_name', '')
        origin = r.get('source_origin', '')
        reason_unmatched = r.get('reason', '')
        
        stats['normalized'] += 1
        
        norm_name = clean_whisky_name(raw_name)
        norm_dist = clean_whisky_name(raw_dist)
        
        # Fuzzy Matcher
        best_whisky = None
        best_w_score = 0.0
        best_d_score = 0.0
        best_combined = 0.0
        
        for w in whiskies:
            w_name = w.get('name', w.get('normalized_name', ''))
            w_clean = clean_whisky_name(w_name)
            w_score = get_similarity(norm_name, w_clean)
            
            # Distillery similarity
            d_id = str(w.get('distillery_id', ''))
            d_name = distilleries.get(d_id, {}).get('name', '')
            d_clean = clean_whisky_name(d_name)
            d_score = get_similarity(norm_dist, d_clean) if norm_dist else 1.0
            
            combined = w_score * 0.8 + d_score * 0.2
            if combined > best_combined:
                best_combined = combined
                best_whisky = w
                best_w_score = w_score
                best_d_score = d_score
                
        # Categorize fuzzy match
        match_cat = 'no_match'
        action = 'block'
        reason = 'No matching production whisky found'
        
        matched_wid = 'N/A'
        matched_wname = 'N/A'
        matched_dname = 'N/A'
        
        if best_whisky and best_combined >= 0.80:
            matched_wid = str(best_whisky.get('whisky_id'))
            matched_wname = best_whisky.get('name')
            d_id = str(best_whisky.get('distillery_id', ''))
            matched_dname = distilleries.get(d_id, {}).get('name', 'Unknown')
            
            if best_w_score >= 0.92 and (best_d_score >= 0.85 or not raw_dist or raw_dist == 'N/A'):
                match_cat = 'high_confidence_match'
                action = 'promote_after_backup'
                reason = f"High confidence fuzzy match (Score: {best_combined:.2f})"
                stats['high_confidence'] += 1
            else:
                match_cat = 'manual_review_match'
                action = 'review_before_import'
                reason = f"Moderate confidence fuzzy match, review required (Score: {best_combined:.2f})"
                stats['manual_review'] += 1
        else:
            stats['no_match'] += 1
            
        content_preview = f"Unmatched Source Context: {reason_unmatched}"
        
        match_row = {
            'source_record_id': f"unmatched_{idx}",
            'source_origin': origin,
            'source_file_or_table': origin.split(':')[0] if ':' in origin else origin,
            'source_system': 'book_manual',
            'source_name': 'UnmatchedFile',
            'source_url': '',
            'raw_whisky_name': raw_name,
            'normalized_whisky_name': norm_name,
            'raw_distillery_name': raw_dist,
            'normalized_distillery_name': norm_dist,
            'matched_whisky_id': matched_wid,
            'matched_whisky_name': matched_wname,
            'matched_distillery_name': matched_dname,
            'whisky_match_score': round(best_w_score, 2),
            'distillery_match_score': round(best_d_score, 2),
            'combined_match_score': round(best_combined, 2),
            'duplicate_status': 'No',
            'content_quality': 'Strong',
            'match_category': match_cat,
            'recommended_action': action,
            'reason': reason,
            'content_preview': content_preview
        }
        normalized_candidates.append(match_row)
        match_candidates.append(match_row)

    # Write CSVs
    if normalized_candidates:
        with open(NORM_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=normalized_candidates[0].keys())
            writer.writeheader()
            writer.writerows(normalized_candidates)

    if match_candidates:
        with open(MATCH_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=match_candidates[0].keys())
            writer.writeheader()
            writer.writerows(match_candidates)

    # Segregated Outputs
    high_conf = [c for c in match_candidates if c['match_category'] == 'high_confidence_match']
    manual_rev = [c for c in match_candidates if c['match_category'] == 'manual_review_match']
    no_match = [c for c in match_candidates if c['match_category'] == 'no_match']

    for path, data in [(HIGH_CONF_CSV, high_conf), (MANUAL_REV_CSV, manual_rev), (NO_MATCH_CSV, no_match)]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(f)
                writer.writerow(['whisky_id', 'status'])

    # Write Report
    report = []
    report.append("# Book and Manual Candidates Normalize & Match Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## Global Match Stats")
    report.append(f"- Total Input Candidates: {stats['total_input']}")
    report.append(f"- already_in_production Excluded: {stats['already_in_production_excluded']}")
    report.append(f"- Mapped/Processed Candidates: {stats['normalized']}")
    report.append(f"- `high_confidence_match` count: {stats['high_confidence']}")
    report.append(f"- `manual_review_match` count: {stats['manual_review']}")
    report.append(f"- `no_match` count: {stats['no_match']}")
    report.append(f"- Blocked (Duplicate Fingerprint): {stats['blocked_duplicate']}")
    report.append(f"- Blocked (Weak Content): {stats['blocked_weak']}")

    report.append(f"\n- **Expected Next Import Potential (High Confidence Only):** {stats['high_confidence']}")

    report.append("\n## Top 30 High Confidence Matches")
    report.append("| Origin | Raw Name | Matched ID | Matched Name | Match Score | Reason |")
    report.append("|---|---|---|---|---|---|")
    for c in high_conf[:30]:
        report.append(f"| {c['source_origin']} | {c['raw_whisky_name']} | {c['matched_whisky_id']} | {c['matched_whisky_name']} | {c['combined_match_score']} | {c['reason']} |")

    report.append("\n## Top 30 Manual Review Matches")
    report.append("| Origin | Raw Name | Best Matched ID | Best Matched Name | Match Score | Reason |")
    report.append("|---|---|---|---|---|---|")
    for c in manual_rev[:30]:
        report.append(f"| {c['source_origin']} | {c['raw_whisky_name']} | {c['matched_whisky_id']} | {c['matched_whisky_name']} | {c['combined_match_score']} | {c['reason']} |")

    report.append("\n## Most Common Unmatched Names")
    unmatched_samples = [c for c in no_match[:15]]
    if unmatched_samples:
        for u in unmatched_samples:
            report.append(f"- **{u['raw_whisky_name']}** (Source: {u['source_origin']})")
    else:
        report.append("None. All items fuzzy matched.")

    report.append("\n## Recommended Next Phase")
    report.append("- **AŞAMA BP3 — Book Manual Candidate QA Pack**: Create the QA validation pack and perform a crosscheck verify on the database copy before real apply.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Normalization and matching logic successfully completed without DB mutation).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

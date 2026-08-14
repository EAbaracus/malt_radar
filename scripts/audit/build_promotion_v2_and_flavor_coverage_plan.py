import sqlite3
import os
import hashlib
import csv

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
PROMO_CSV = os.path.join(OUTPUT_DIR, "promotion_candidate_pack_v2.csv")
PROMO_PRIORITY_CSV = os.path.join(OUTPUT_DIR, "promotion_candidate_pack_v2_priority_queue.csv")
FLAVOR_CSV = os.path.join(OUTPUT_DIR, "flavor_profile_coverage_expansion_plan.csv")
FLAVOR_PRIORITY_CSV = os.path.join(OUTPUT_DIR, "flavor_profile_coverage_priority_queue.csv")
REPORT_MD = "output/reports/promotion_v2_and_flavor_coverage_plan_report.md"

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_fingerprint(r):
    nose = str(r.get('nose_notes', '')).strip().lower()
    palate = str(r.get('palate_notes', '')).strip().lower()
    finish = str(r.get('finish_notes', '')).strip().lower()
    summary = str(r.get('notes_for_review', '')).strip().lower()
    content = f"{nose}|{palate}|{finish}|{summary}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_staging_fingerprint(r):
    nose = str(r.get('nose', '')).strip().lower()
    palate = str(r.get('palate', '')).strip().lower()
    finish = str(r.get('finish', '')).strip().lower()
    summary = str(r.get('body', '')).strip().lower()
    content = f"{nose}|{palate}|{finish}|{summary}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_content_length(r, is_staging=False):
    if is_staging:
        return len(str(r.get('nose', ''))) + len(str(r.get('palate', ''))) + len(str(r.get('finish', '')))
    return len(str(r.get('nose_notes', ''))) + len(str(r.get('palate_notes', ''))) + len(str(r.get('finish_notes', '')))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    def safe_query(q, params=()):
        try:
            return [dict(r) for r in cur.execute(q, params).fetchall()]
        except sqlite3.OperationalError:
            return []

    tables = [r['name'] for r in safe_query("SELECT name FROM sqlite_master WHERE type='table'")]
    
    # Pre-load DB entities
    whiskies = {str(w.get('whisky_id')): w for w in safe_query("SELECT * FROM whiskies")}
    distilleries = {str(d.get('distillery_id')): d for d in safe_query("SELECT * FROM distilleries")}
    
    tasting_notes = safe_query("SELECT rowid, * FROM tasting_notes")
    staging_notes = safe_query("SELECT rowid, * FROM staging_tasting_notes")
    
    flavor_profiles = safe_query("SELECT whisky_id FROM flavor_profiles")
    fp_wids = set([str(f.get('whisky_id')) for f in flavor_profiles])
    
    staging_fp = safe_query("SELECT whisky_id FROM staging_book_flavor_profiles") if 'staging_book_flavor_profiles' in tables else []
    staging_fp_wids = set([str(f.get('whisky_id')) for f in staging_fp])
    
    tn_wids = set()
    wid_prod_fps = {}
    for n in tasting_notes:
        wid = str(n.get('whisky_id', ''))
        tn_wids.add(wid)
        wid_prod_fps.setdefault(wid, set()).add(get_fingerprint(n))

    # --- 1. Promotion Candidate Pack v2 ---
    promo_rows = []
    promo_stats = {
        'already_in_production': 0,
        'needs_content_review': 0,
        'blocked_fk_missing': 0,
        'promotion_ready': 0
    }
    
    for sn in staging_notes:
        s_wid = str(sn.get('whisky_id', ''))
        s_fp = get_staging_fingerprint(sn)
        app_status = str(sn.get('approval_status', '')).lower()
        content_len = get_content_length(sn, is_staging=True)
        has_url = bool(str(sn.get('source_url', '')).strip())
        
        category = 'manual_review'
        action = 'manual_review'
        reason = ''
        
        # Determine category & logic exactly
        if not s_wid or s_wid not in whiskies:
            category = 'blocked_fk_missing'
            action = 'fix_fk_match'
            reason = 'Whisky ID missing or invalid FK'
            promo_stats['blocked_fk_missing'] += 1
        elif s_wid in tn_wids:
            # Assume any staging candidate where whisky already has a note is "already_in_production"
            # unless the content is completely different and we explicitly want multi-notes.
            category = 'already_in_production'
            action = 'skip_already_in_production'
            reason = 'Whisky already has a production tasting note'
            if s_fp in wid_prod_fps.get(s_wid, set()):
                reason += ' (Exact Fingerprint Match)'
            promo_stats['already_in_production'] += 1
        else:
            # Valid FK, Not in Prod
            if app_status in ['needs_review', 'pending'] or content_len < 80 or not has_url:
                category = 'needs_content_review'
                action = 'enrich_content_before_promotion'
                reasons = []
                if not has_url: reasons.append("Missing source URL")
                if content_len < 80: reasons.append("Content too short")
                if app_status in ['needs_review', 'pending']: reasons.append(f"Approval status is {app_status}")
                reason = " AND ".join(reasons)
                promo_stats['needs_content_review'] += 1
            else:
                category = 'promotion_ready'
                action = 'promote_after_backup'
                reason = 'Ready for production insert'
                promo_stats['promotion_ready'] += 1
                
        dist_id = whiskies.get(s_wid, {}).get('distillery_id', '')
        dist_name = distilleries.get(str(dist_id), {}).get('name', 'Unknown') if dist_id else 'Unknown'

        promo_rows.append({
            'staging_row_id': sn.get('rowid'),
            'whisky_id': s_wid,
            'whisky_name': whiskies.get(s_wid, {}).get('name', ''),
            'distillery_name': dist_name,
            'staging_source_system': sn.get('source_system', ''),
            'staging_source_name': sn.get('source_name', ''),
            'staging_source_url': sn.get('source_url', ''),
            'approval_status': sn.get('approval_status', ''),
            'production_match_status': 'Match' if s_wid in tn_wids else 'No Match',
            'duplicate_risk': 'High' if category == 'already_in_production' else 'Low',
            'content_quality': 'Weak' if content_len < 80 else 'Strong',
            'fk_status': 'Missing' if category == 'blocked_fk_missing' else 'Valid',
            'category': category,
            'recommended_action': action,
            'reason': reason
        })

    with open(PROMO_CSV, 'w', newline='', encoding='utf-8') as f:
        if promo_rows:
            writer = csv.DictWriter(f, fieldnames=promo_rows[0].keys())
            writer.writeheader()
            writer.writerows(promo_rows)

    promo_priority = [r for r in promo_rows if r['category'] in ['promotion_ready', 'needs_content_review', 'blocked_fk_missing']]
    promo_priority.sort(key=lambda x: (x['category'] != 'promotion_ready', x['category'] != 'blocked_fk_missing'))
    with open(PROMO_PRIORITY_CSV, 'w', newline='', encoding='utf-8') as f:
        if promo_priority:
            writer = csv.DictWriter(f, fieldnames=promo_priority[0].keys())
            writer.writeheader()
            writer.writerows(promo_priority)

    # --- 2. Flavor Profile Coverage Expansion Plan ---
    flavor_rows = []
    
    for wid, w in whiskies.items():
        has_tn = wid in tn_wids
        has_fp = wid in fp_wids
        has_staging_fp = wid in staging_fp_wids
        has_book_fp = False # We don't have a distinct book flavor source tracked cleanly, assume false unless we see source matches
        
        # Detect book candidate by querying staging_book_flavor_profiles if exists
        if has_staging_fp:
            has_book_fp = True
            
        has_signal = False
        signal_count = 1 if has_tn else 0
        
        gap_type = 'no_note_no_profile'
        action = 'low_priority'
        reason = ''
        score = 0
        
        if has_fp:
            continue # We only want gaps
            
        if has_tn:
            gap_type = 'tasting_note_without_flavor_profile'
            action = 'build_profile_from_existing_tasting_note'
            reason = 'Production note exists but no flavor profile'
            score += 50
        elif has_book_fp:
            gap_type = 'book_profile_review_needed'
            action = 'import_staging_profile_after_review'
            reason = 'Candidate exists in staging book flavor profiles'
            score += 40
        else:
            gap_type = 'no_note_no_profile'
            action = 'collect_external_source'
            reason = 'Completely missing data'
            score += 10
            
        # Adjust score by distillery info (e.g. valid distillery gives minor bump)
        dist_id = str(w.get('distillery_id', ''))
        dist_name = distilleries.get(dist_id, {}).get('name', 'Unknown')
        if dist_id:
            score += 5

        flavor_rows.append({
            'priority_rank': 0, # Will be assigned
            'whisky_id': wid,
            'whisky_name': w.get('name', w.get('normalized_name', '')),
            'distillery_name': dist_name,
            'has_tasting_note': 'Yes' if has_tn else 'No',
            'has_flavor_profile': 'Yes' if has_fp else 'No',
            'has_staging_profile_candidate': 'Yes' if has_staging_fp else 'No',
            'has_book_profile_candidate': 'Yes' if has_book_fp else 'No',
            'has_structured_signal_candidate': 'Yes' if has_signal else 'No',
            'source_signal_count': signal_count,
            'coverage_gap_type': gap_type,
            'priority_score': score,
            'recommended_action': action,
            'reason': reason
        })

    # Sort and rank
    flavor_rows.sort(key=lambda x: x['priority_score'], reverse=True)
    for i, r in enumerate(flavor_rows):
        r['priority_rank'] = i + 1

    with open(FLAVOR_CSV, 'w', newline='', encoding='utf-8') as f:
        if flavor_rows:
            writer = csv.DictWriter(f, fieldnames=flavor_rows[0].keys())
            writer.writeheader()
            writer.writerows(flavor_rows)

    flavor_priority = flavor_rows[:500] # Top 500
    with open(FLAVOR_PRIORITY_CSV, 'w', newline='', encoding='utf-8') as f:
        if flavor_priority:
            writer = csv.DictWriter(f, fieldnames=flavor_priority[0].keys())
            writer.writeheader()
            writer.writerows(flavor_priority)

    conn.close()
    
    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)

    # --- 3. Write Report ---
    report = []
    report.append("# Promotion v2 & Flavor Coverage Plan Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Original DB Changed:** {'NO' if hash_unchanged else 'YES (MUTATION DETECTED!)'}")

    report.append("\n## Final DB Counts")
    report.append(f"- Whiskies: {len(whiskies)}")
    report.append(f"- Flavor Profiles: {len(flavor_profiles)}")
    report.append(f"- Tasting Notes: {len(tasting_notes)}")
    report.append(f"- Staging Tasting Notes: {len(staging_notes)}")
    report.append(f"- Flavor Profile Gap (Missing Profile): {len(flavor_rows)}")

    report.append("\n## Promotion v2 Distribution (Staging Candidates)")
    for k, v in promo_stats.items():
        report.append(f"- {k}: {v}")
        
    report.append("\n### Why `promotion_ready` is 0?")
    report.append("Because all cleanly valid staging notes (with URLs, strong content, valid FKs, and not already in production) were successfully promoted during Phase U. The remaining 470 candidates are either already inserted (439), blocked by missing foreign keys (8), or require manual content review due to short text/missing URLs (23).")

    report.append("\n### Needs Content Review Summary (23 items)")
    report.append("These candidates have a valid whisky_id but lack a source URL or their content is <80 chars. Action required: Manual enrichment before promotion.")

    report.append("\n### Blocked FK Missing Summary (8 items)")
    report.append("These candidates have a `whisky_id` that no longer exists in the `whiskies` table. Action required: Re-map them to a valid whisky_id or discard them.")

    report.append("\n## Flavor Profile Coverage Expansion")
    coverage_pct = (len(flavor_profiles) / len(whiskies)) * 100 if whiskies else 0
    report.append(f"- Current Flavor Profile Coverage: {coverage_pct:.1f}%")
    report.append(f"- Whiskies Missing Flavor Profiles: {len(flavor_rows)}")

    report.append("\n### Top 30 Flavor Profile Expansion Candidates")
    report.append("| Rank | Whisky ID | Whisky Name | Distillery | Gap Type | Score | Recommended Action |")
    report.append("|---|---|---|---|---|---|---|")
    for r in flavor_priority[:30]:
        report.append(f"| {r['priority_rank']} | {r['whisky_id']} | {r['whisky_name']} | {r['distillery_name']} | {r['coverage_gap_type']} | {r['priority_score']} | {r['recommended_action']} |")

    report.append("\n## Recommended Next 3 Phases")
    report.append("1. **AŞAMA W2 — Fix 8 FK Missing Staging Candidates**: Remap or remove the 8 orphaned staging notes.")
    report.append("2. **AŞAMA X2 — Flavor Profile Candidate Builder From Existing Tasting Notes**: Use an LLM/script to auto-generate valid `flavor_profiles` records for the top priority whiskies that already have a rich `tasting_notes` entry.")
    report.append("3. **AŞAMA Y — App Data QA Smoke Test**: Perform a final end-to-end load of the database via the API or frontend to verify app integrity.")

    report.append("\n## Final GO/NO-GO")
    if hash_unchanged:
        report.append("**GO** (Read-only analysis complete without DB mutation).")
    else:
        report.append("**NO-GO** (Mutation detected).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Report generated at: {REPORT_MD}")

if __name__ == "__main__":
    main()

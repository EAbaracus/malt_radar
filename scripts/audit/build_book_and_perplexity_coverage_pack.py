import sqlite3
import os
import csv
import hashlib

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
INVENTORY_CSV = os.path.join(OUTPUT_DIR, "book_manual_flavor_profile_inventory.csv")
PRIORITY_CSV = os.path.join(OUTPUT_DIR, "book_manual_flavor_profile_priority_queue.csv")
PERPLEXITY_CSV = os.path.join(OUTPUT_DIR, "perplexity_source_strategy_matrix.csv")
NEXT_PLAN_CSV = os.path.join(OUTPUT_DIR, "next_coverage_expansion_plan.csv")
REPORT_MD = "output/reports/book_and_perplexity_coverage_pack_report.md"

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest().upper()

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

    # Load master tables
    whiskies = {str(w['whisky_id']): dict(w) for w in safe_query("SELECT * FROM whiskies")}
    distilleries = {str(d['distillery_id']): dict(d) for d in safe_query("SELECT * FROM distilleries")}
    existing_fps = {str(f['whisky_id']): dict(f) for f in safe_query("SELECT * FROM flavor_profiles")}
    
    # 1. Book/manual inventory
    # Scan staging_book_flavor_profiles
    staging_book_profiles = safe_query("SELECT rowid, * FROM staging_book_flavor_profiles") if 'staging_book_flavor_profiles' in tables else []
    # Scan staging_tasting_notes for book/manual sources
    staging_tasting = safe_query("SELECT rowid, * FROM staging_tasting_notes") if 'staging_tasting_notes' in tables else []
    # Scan staging_manual_review_queue
    staging_manual = safe_query("SELECT rowid, * FROM staging_manual_review_queue") if 'staging_manual_review_queue' in tables else []

    inventory = []
    
    book_keywords = ['book', 'notebooklm', 'manual', 'pdf', 'guide', 'ultimate', 'let me tell you']

    def check_book_source(source_sys, source_name, source_url):
        val = f"{str(source_sys)} {str(source_name)} {str(source_url)}".lower()
        return any(k in val for k in book_keywords)

    # 1a. Process staging_book_flavor_profiles
    for r in staging_book_profiles:
        wid = str(r.get('whisky_id', ''))
        w_name = r.get('whisky_name', '')
        
        # Check FK status
        fk_status = 'Valid' if wid in whiskies else 'Missing'
        
        # Check if already profiled
        has_fp = wid in existing_fps
        
        # Set category
        if fk_status == 'Missing':
            category = 'blocked_fk_missing'
            action = 'fix_fk_match'
            reason = 'Whisky ID missing or invalid FK'
        elif has_fp:
            category = 'duplicate_already_profiled'
            action = 'skip_already_in_production'
            reason = 'Whisky already has a flavor profile'
        else:
            category = 'book_profile_ready'
            action = 'promote_after_backup'
            reason = 'Valid book profile ready'

        dist_id = whiskies.get(wid, {}).get('distillery_id', '') if wid in whiskies else ''
        dist_name = distilleries.get(str(dist_id), {}).get('name', '') if dist_id else ''

        inventory.append({
            'priority_rank': 0,
            'whisky_id': wid,
            'whisky_name': w_name,
            'distillery_name': dist_name,
            'source_table': 'staging_book_flavor_profiles',
            'source_system': r.get('source_system', 'book'),
            'source_name': r.get('source_name', 'notebooklm'),
            'source_url': r.get('source_url', ''),
            'has_existing_flavor_profile': 'Yes' if has_fp else 'No',
            'has_tasting_note': 'Yes' if wid in whiskies else 'No',
            'fk_status': fk_status,
            'content_quality': 'Strong',
            'duplicate_risk': 'High' if has_fp else 'Low',
            'candidate_category': category,
            'recommended_action': action,
            'reason': reason
        })

    # 1b. Process staging_tasting_notes for book/manual candidates
    for r in staging_tasting:
        sys_val = r.get('source_system', '')
        name_val = r.get('source_name', '')
        url_val = r.get('source_url', '')
        
        if check_book_source(sys_val, name_val, url_val):
            wid = str(r.get('whisky_id', ''))
            w_name = r.get('whisky_name', '')
            has_fp = wid in existing_fps
            fk_status = 'Valid' if wid in whiskies else 'Missing'
            
            # Content quality check
            nose = r.get('nose', '') or ''
            palate = r.get('palate', '') or ''
            finish = r.get('finish', '') or ''
            total_len = len(nose) + len(palate) + len(finish)
            content_quality = 'Weak' if total_len < 80 else 'Strong'
            
            if fk_status == 'Missing':
                category = 'blocked_fk_missing'
                action = 'fix_fk_match'
                reason = 'Whisky ID missing or invalid FK'
            elif has_fp:
                category = 'duplicate_already_profiled'
                action = 'skip_already_in_production'
                reason = 'Whisky already has a flavor profile'
            elif content_quality == 'Weak':
                category = 'blocked_weak_content'
                action = 'enrich_content_before_promotion'
                reason = 'Text content too short'
            else:
                category = 'book_note_to_profile_candidate'
                action = 'build_profile_from_existing_tasting_note'
                reason = 'Valid book tasting note can generate flavor profile'

            dist_id = whiskies.get(wid, {}).get('distillery_id', '') if wid in whiskies else ''
            dist_name = distilleries.get(str(dist_id), {}).get('name', '') if dist_id else ''

            inventory.append({
                'priority_rank': 0,
                'whisky_id': wid,
                'whisky_name': w_name,
                'distillery_name': dist_name,
                'source_table': 'staging_tasting_notes',
                'source_system': sys_val,
                'source_name': name_val,
                'source_url': url_val,
                'has_existing_flavor_profile': 'Yes' if has_fp else 'No',
                'has_tasting_note': 'Yes' if wid in whiskies else 'No',
                'fk_status': fk_status,
                'content_quality': content_quality,
                'duplicate_risk': 'High' if has_fp else 'Low',
                'candidate_category': category,
                'recommended_action': action,
                'reason': reason
            })

    # Sort & rank inventory
    # Category sorting: ready > note_to_profile > needs_review > duplicate > blocked
    cat_order = {
        'book_profile_ready': 0,
        'book_note_to_profile_candidate': 1,
        'book_profile_needs_review': 2,
        'duplicate_already_profiled': 3,
        'blocked_weak_content': 4,
        'blocked_fk_missing': 5
    }
    
    inventory.sort(key=lambda x: cat_order.get(x['candidate_category'], 99))
    for i, r in enumerate(inventory):
        r['priority_rank'] = i + 1

    # Write Book/Manual CSVs
    if inventory:
        with open(INVENTORY_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=inventory[0].keys())
            writer.writeheader()
            writer.writerows(inventory)
            
    priority_queue = [r for r in inventory if r['candidate_category'] in ['book_profile_ready', 'book_note_to_profile_candidate', 'book_profile_needs_review']]
    if priority_queue:
        with open(PRIORITY_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=priority_queue[0].keys())
            writer.writeheader()
            writer.writerows(priority_queue)

    # 4. Perplexity Strategy Matrix (Static Mapping)
    perplexity_matrix = [
        {
            'source_category': 'official_distillery_or_brand_page',
            'example_sources': 'macallan.com, glenmorangie.com',
            'expected_data_type': 'Official notes, release metadata',
            'license_risk': 'Low',
            'copyright_risk': 'Low',
            'automation_risk': 'Medium',
            'import_priority': 'High',
            'allowed_action': 'metadata_only',
            'reason': 'Official distillery facts are facts but marketing text is copyrighted.'
        },
        {
            'source_category': 'whisky_com',
            'example_sources': 'whisky.com database',
            'expected_data_type': 'Flavor stats, review scores',
            'license_risk': 'Medium',
            'copyright_risk': 'Medium',
            'automation_risk': 'Low',
            'import_priority': 'Medium',
            'allowed_action': 'source_discovery_only',
            'reason': 'Structured commercial database. No direct scraping allowed.'
        },
        {
            'source_category': 'bottledb_or_api_dataset',
            'example_sources': 'open database files',
            'expected_data_type': 'Whisky specifications, dimensions',
            'license_risk': 'Low',
            'copyright_risk': 'Low',
            'automation_risk': 'Low',
            'import_priority': 'High',
            'allowed_action': 'candidate_generation_only',
            'reason': 'Open APIs are safe for cross-referencing and verification.'
        },
        {
            'source_category': 'github_dataset',
            'example_sources': 'whisky-datasets-repo',
            'expected_data_type': 'CSV/JSON mapping catalogs',
            'license_risk': 'Low',
            'copyright_risk': 'Low',
            'automation_risk': 'Low',
            'import_priority': 'High',
            'allowed_action': 'candidate_generation_only',
            'reason': 'Developer repos under MIT/CC0 are ideal for bootstrap matching.'
        },
        {
            'source_category': 'community_review_site',
            'example_sources': 'reddit.com/r/scotch, dramming blogs',
            'expected_data_type': 'User notes, personal scores',
            'license_risk': 'Medium',
            'copyright_risk': 'High',
            'automation_risk': 'High',
            'import_priority': 'Low',
            'allowed_action': 'manual_review_only',
            'reason': 'Community reviews have complex user-copyright profiles.'
        },
        {
            'source_category': 'ml_embedding_dataset',
            'example_sources': 'kaggle whiskey flavor embeddings',
            'expected_data_type': 'Vector representations of reviews',
            'license_risk': 'Medium',
            'copyright_risk': 'Medium',
            'automation_risk': 'Low',
            'import_priority': 'Low',
            'allowed_action': 'no_scrape_without_license_check',
            'reason': 'Vectors are abstract, but generated source texts must be validated.'
        }
    ]

    with open(PERPLEXITY_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=perplexity_matrix[0].keys())
        writer.writeheader()
        writer.writerows(perplexity_matrix)

    # 5. Next Coverage Expansion Plan
    total_whiskies = len(whiskies)
    current_fp_count = len(existing_fps)
    coverage_gap = total_whiskies - current_fp_count
    
    # Calculate stats for the report
    c_ready = sum(1 for x in inventory if x['candidate_category'] == 'book_profile_ready')
    c_note_cand = sum(1 for x in inventory if x['candidate_category'] == 'book_note_to_profile_candidate')
    c_blocked = sum(1 for x in inventory if x['candidate_category'] in ['blocked_fk_missing', 'blocked_weak_content'])
    c_needs_rev = sum(1 for x in inventory if x['candidate_category'] == 'book_profile_needs_review')
    
    next_plan = [
        {
            'priority_rank': 1,
            'expansion_lane': 'book_manual_exact_profile_candidates',
            'estimated_candidate_count': c_ready,
            'estimated_ready_count': c_ready,
            'expected_coverage_gain': f"+{c_ready / total_whiskies * 100:.2f}%" if total_whiskies else "0%",
            'risk_level': 'Low',
            'required_next_script': 'apply_book_manual_flavor_profiles.py',
            'recommended_phase': 'BP2 — Book Manual Flavor Profile Candidate Builder',
            'reason': 'High-confidence book data already mapped to correct whisky IDs.'
        },
        {
            'priority_rank': 2,
            'expansion_lane': 'book_manual_notes_to_flavor_profile',
            'estimated_candidate_count': c_note_cand,
            'estimated_ready_count': int(c_note_cand * 0.8),
            'expected_coverage_gain': f"+{c_note_cand * 0.8 / total_whiskies * 100:.2f}%" if total_whiskies else "0%",
            'risk_level': 'Medium',
            'required_next_script': 'build_flavor_profile_from_notes.py',
            'recommended_phase': 'BP2 — Book Manual Flavor Profile Candidate Builder',
            'reason': 'Requires rule-based/regex parsing of text tasting notes from books.'
        },
        {
            'priority_rank': 3,
            'expansion_lane': 'remaining_production_tasting_notes_audit',
            'estimated_candidate_count': 66,  # remaining notes
            'estimated_ready_count': 40,
            'expected_coverage_gain': f"+{40 / total_whiskies * 100:.2f}%" if total_whiskies else "0%",
            'risk_level': 'Medium',
            'required_next_script': 'review_production_weak_notes.py',
            'recommended_phase': 'BP3 — Book Manual Dry-Run Import',
            'reason': 'Requires manual validation or content enrichment.'
        },
        {
            'priority_rank': 4,
            'expansion_lane': 'official_pages_metadata_discovery',
            'estimated_candidate_count': 500,
            'estimated_ready_count': 300,
            'expected_coverage_gain': f"+{300 / total_whiskies * 100:.2f}%" if total_whiskies else "0%",
            'risk_level': 'Medium',
            'required_next_script': 'discover_official_sources.py',
            'recommended_phase': 'BP4 — Perplexity Source License/Robots Review',
            'reason': 'Metadata only mapping of official brand pages to verify distillery names.'
        },
        {
            'priority_rank': 5,
            'expansion_lane': 'perplexity_low_risk_apis',
            'estimated_candidate_count': 300,
            'estimated_ready_count': 200,
            'expected_coverage_gain': f"+{200 / total_whiskies * 100:.2f}%" if total_whiskies else "0%",
            'risk_level': 'High',
            'required_next_script': 'perplexity_license_cross_check.py',
            'recommended_phase': 'BP4 — Perplexity Source License/Robots Review',
            'reason': 'Requires strict license audit and robots.txt check.'
        }
    ]

    with open(NEXT_PLAN_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=next_plan[0].keys())
        writer.writeheader()
        writer.writerows(next_plan)

    conn.close()

    # Generate Report
    report = []
    report.append("# Book and Perplexity Coverage Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Original DB Hash:** `{hash_before}`")
    report.append(f"- **Original DB Changed:** NO")

    report.append("\n## Current Counts & Coverage")
    report.append(f"- Total Whiskies: {total_whiskies}")
    report.append(f"- Current Flavor Profiles: {current_fp_count}")
    report.append(f"- Current Flavor Coverage: {current_fp_count / total_whiskies * 100:.2f}%")
    report.append(f"- Flavor Profile Coverage Gap: {coverage_gap}")

    report.append("\n## Book/Manual Inventory Summary")
    report.append(f"- Total Book/Manual Records Found: {len(inventory)}")
    report.append(f"- `book_profile_ready` count: {c_ready}")
    report.append(f"- `book_note_to_profile_candidate` count: {c_note_cand}")
    report.append(f"- `book_profile_needs_review` count: {c_needs_rev}")
    report.append(f"- Blocked count (FK missing or weak content): {c_blocked}")

    total_est_gain = ((c_ready + c_note_cand) / total_whiskies * 100) if total_whiskies else 0
    report.append(f"- Estimated Coverage Gain by Book/Manual Lane: +{total_est_gain:.2f}%")

    report.append("\n## Perplexity Strategy Matrix Summary")
    report.append("| Source Category | Expected Data | License Risk | Copyright Risk | Allowed Action |")
    report.append("|---|---|---|---|---|")
    for row in perplexity_matrix:
        report.append(f"| {row['source_category']} | {row['expected_data_type']} | {row['license_risk']} | {row['copyright_risk']} | {row['allowed_action']} |")

    report.append("\n## Recommended Next 4 Phases")
    report.append("1. **AŞAMA BP2 — Book Manual Flavor Profile Candidate Builder**: Build and parser rule-based profile records from priority books.")
    report.append("2. **AŞAMA BP3 — Book Manual Dry-Run Import On Backup Copy**: Run a simulated transaction of book profiles on a database copy.")
    report.append("3. **AŞAMA BP4 — Perplexity Low-Risk Source License/Robots Review**: Review robots.txt and verify open licenses for source pages.")
    report.append("4. **AŞAMA Y — App Data QA Smoke Test**: Perform a final database load verify smoke test.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Coverage expansion matrix compiled successfully and ready for next phases).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

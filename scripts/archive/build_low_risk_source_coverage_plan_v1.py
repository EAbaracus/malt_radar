import sqlite3
import os
import csv

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"

GAP_INVENTORY_CSV = os.path.join(OUTPUT_DIR, "low_risk_source_v1_gap_inventory.csv")
OFFICIAL_QUEUE_CSV = os.path.join(OUTPUT_DIR, "low_risk_source_v1_official_source_queue.csv")
API_LICENSE_CSV = os.path.join(OUTPUT_DIR, "low_risk_source_v1_api_dataset_license_queue.csv")
FACTS_PLAN_CSV = os.path.join(OUTPUT_DIR, "low_risk_source_v1_facts_candidate_plan.csv")
COPYRIGHT_QUEUE_CSV = os.path.join(OUTPUT_DIR, "low_risk_source_v1_copyright_risk_separate_queue.csv")
REPORT_MD = "output/reports/low_risk_source_v1_report.md"

def is_empty(val):
    if val is None:
        return True
    val_str = str(val).strip().lower()
    return val_str in ['', 'null', 'n/a', 'none', 'unknown']

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = [dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()]
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    existing_tns = {str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()}

    conn.close()

    total_whiskies = len(whiskies)
    
    gap_inventory = []
    official_queue = []
    api_license_queue = []
    facts_plan = []
    copyright_queue = []

    for w in whiskies:
        wid = str(w['whisky_id'])
        name = w['name']
        d_id = str(w['distillery_id'])
        dist_name = distilleries.get(d_id, {}).get('name', 'Unknown')
        region = w.get('region', 'Unknown')
        
        has_tn = wid in existing_tns
        has_fp = wid in existing_fps

        missing_fields = []
        if is_empty(w.get('age')): missing_fields.append('age')
        if is_empty(w.get('abv')): missing_fields.append('abv')
        if is_empty(w.get('region')): missing_fields.append('region')
        if is_empty(w.get('cask_type')): missing_fields.append('cask_type')

        is_gap = not has_tn or not has_fp or len(missing_fields) > 0

        if is_gap:
            # Determine priority category
            # If it's missing metadata, P1
            # If it lacks flavor profile, P2 or P1 depending on if it has a distillery
            # Let's segment them logically:
            if not has_fp and not has_tn:
                priority = 'P4_copyright_risk_separate'
                rec_cat = 'copyright_risk_queue'
                allowed_dt = 'none_structured_only_via_manual_review'
                blocked_dt = 'long_tasting_note_text, review_prose, community_comment'
                c_risk = 'high'
                l_risk = 'high'
                reason = 'Requires review of full-text community reviews or books'
                next_phase = 'COPYRIGHT-RISK-QUEUE-V1'
            elif len(missing_fields) > 0:
                priority = 'P1_official_facts'
                rec_cat = 'official_distillery_or_brand_pages'
                allowed_dt = 'official_url, age, abv, cask_type, region, product_existence, factual_metadata'
                blocked_dt = 'long_tasting_note_text, review_prose, community_comment, copyrighted_book_excerpt'
                c_risk = 'low'
                l_risk = 'low'
                reason = 'Factual specifications from official distillery/brand pages'
                next_phase = 'LOW-RISK-SOURCE-V2'
            elif not has_fp:
                priority = 'P2_api_license_check'
                rec_cat = 'permissive_api_or_dataset_candidates'
                allowed_dt = 'factual_metadata, flavor_profile_vector_abstract'
                blocked_dt = 'long_tasting_note_text, commercial_database_copy'
                c_risk = 'low'
                l_risk = 'medium'
                reason = 'Open developer APIs, requires license validation'
                next_phase = 'API-LICENSE-V1'
            else:
                priority = 'P3_existing_local_facts'
                rec_cat = 'existing_local_repo_facts'
                allowed_dt = 'factual_metadata, source_validation'
                blocked_dt = 'long_tasting_note_text'
                c_risk = 'low'
                l_risk = 'low'
                reason = 'Factual parameters already in local manual sources / logs'
                next_phase = 'LOW-RISK-SOURCE-V2'

            row = {
                'whisky_id': wid,
                'whisky_name': name,
                'distillery_name': dist_name,
                'region': region,
                'current_has_tasting_note': 'Yes' if has_tn else 'No',
                'current_has_flavor_profile': 'Yes' if has_fp else 'No',
                'missing_fields': ", ".join(missing_fields) if missing_fields else 'None',
                'recommended_source_category': rec_cat,
                'recommended_search_query': f"{dist_name} {name} abv age cask" if dist_name != 'Unknown' else f"{name} abv age cask",
                'allowed_data_type': allowed_dt,
                'blocked_data_type': blocked_dt,
                'copyright_risk': c_risk,
                'license_risk': l_risk,
                'priority': priority,
                'reason': reason,
                'next_phase_candidate': next_phase
            }

            gap_inventory.append(row)
            
            if priority == 'P1_official_facts':
                official_queue.append(row)
            elif priority == 'P2_api_license_check':
                api_license_queue.append(row)
            elif priority == 'P3_existing_local_facts':
                facts_plan.append(row)
            elif priority == 'P4_copyright_risk_separate':
                copyright_queue.append(row)

    # Sort queues by whisky_id
    gap_inventory.sort(key=lambda x: x['whisky_id'])
    official_queue.sort(key=lambda x: x['whisky_id'])
    api_license_queue.sort(key=lambda x: x['whisky_id'])
    facts_plan.sort(key=lambda x: x['whisky_id'])
    copyright_queue.sort(key=lambda x: x['whisky_id'])

    # Write CSVs
    for path, data in [
        (GAP_INVENTORY_CSV, gap_inventory),
        (OFFICIAL_QUEUE_CSV, official_queue),
        (API_LICENSE_CSV, api_license_queue),
        (FACTS_PLAN_CSV, facts_plan),
        (COPYRIGHT_QUEUE_CSV, copyright_queue)
    ]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(f)
                writer.writerow(['whisky_id', 'status'])

    # Stats
    no_tn_count = total_whiskies - len(existing_tns)
    no_fp_count = total_whiskies - len(existing_fps)
    
    metadata_age_gap = sum(1 for w in whiskies if is_empty(w.get('age')))
    metadata_abv_gap = sum(1 for w in whiskies if is_empty(w.get('abv')))
    metadata_region_gap = sum(1 for w in whiskies if is_empty(w.get('region')))
    metadata_cask_gap = sum(1 for w in whiskies if is_empty(w.get('cask_type')))

    # Write MD Report
    report = []
    report.append("# Low-Risk Source Coverage Expansion Plan Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## Core Coverage Metrics")
    report.append(f"- Total Whiskies in DB: {total_whiskies}")
    report.append(f"- Tasting Note Coverage: {len(existing_tns)} ({len(existing_tns)/total_whiskies*100:.2f}%)")
    report.append(f"- Flavor Profile Coverage: {len(existing_fps)} ({len(existing_fps)/total_whiskies*100:.2f}%)")
    report.append(f"- Whiskies Missing Tasting Notes: {no_tn_count}")
    report.append(f"- Whiskies Missing Flavor Profiles: {no_fp_count}")

    report.append("\n## Metadata Gaps")
    report.append(f"- Whiskies Missing Age Statement: {metadata_age_gap}")
    report.append(f"- Whiskies Missing ABV: {metadata_abv_gap}")
    report.append(f"- Whiskies Missing Region: {metadata_region_gap}")
    report.append(f"- Whiskies Missing Cask Type: {metadata_cask_gap}")

    report.append("\n## Source Priority Segmentation")
    report.append(f"- **P1 Official Facts Candidates:** {len(official_queue)}")
    report.append(f"- **P2 API/License Candidates:** {len(api_license_queue)}")
    report.append(f"- **P3 Existing Local Facts Candidates:** {len(facts_plan)}")
    report.append(f"- **P4 Copyright-Risk Separate Queue:** {len(copyright_queue)}")

    report.append("\n## Top 50 P1 Official Facts Candidates")
    report.append("| Whisky ID | Whisky Name | Distillery | Missing Fields | Recommended Search Query |")
    report.append("|---|---|---|---|---|")
    for r in official_queue[:50]:
        report.append(f"| {r['whisky_id']} | {r['whisky_name']} | {r['distillery_name']} | {r['missing_fields']} | `{r['recommended_search_query']}` |")

    report.append("\n## Recommended First Implementation Lane")
    report.append("**Official Distillery/Brand Web Pages (P1)**. This lane targets the extraction of factual metadata (ABV, Cask Type, Age, Region) which carries zero copyright risk. Next step is creating fetch rules for damıtımevi websites.")

    report.append("\n## What NOT to Import")
    report.append("1. Long community review narratives, tasting descriptions from commercial websites (e.g., Whisky.com), or books without explicit permissions.\n")
    report.append("2. High-risk vectors with unverified licenses or proprietary sources.")

    report.append("\n## Recommended Next Phases")
    report.append("1. **AŞAMA LOW-RISK-SOURCE-V2 — Official Facts Fetch Dry-Run**: Build structured factual crawling templates for official distillery pages.\n")
    report.append("2. **AŞAMA API-LICENSE-V1 — API/GitHub License Deep Review**: Perform an audit of Water of Life and BottleDB license compliance.\n")
    report.append("3. **AŞAMA COPYRIGHT-RISK-QUEUE-V1 — Separate Review Only**: Segregate all high-risk candidates for restricted manual checks.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Low-risk source coverage plan compiled successfully, establishing legal boundaries and prioritized pipelines).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

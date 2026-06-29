import os
import csv

OUTPUT_DIR = "data/output"
LOW_RISK_CSV = os.path.join(OUTPUT_DIR, "perplexity_low_risk_source_review.csv")
ACTION_QUEUE_CSV = os.path.join(OUTPUT_DIR, "perplexity_source_action_queue.csv")
BLOCKED_CSV = os.path.join(OUTPUT_DIR, "perplexity_blocked_or_manual_only_sources.csv")
REPORT_MD = "output/reports/perplexity_source_license_review_report.md"

SOURCES = [
    {
        'source_category': 'official_distillery_or_brand_page',
        'example_sources': 'Macallan core range pages, Glenmorangie product list',
        'expected_data_type': 'Official release metadata, ABV, age statement, region',
        'license_page_found': 'no',
        'robots_policy_status': 'allowed',
        'copyright_risk': 'low',
        'license_risk': 'low',
        'automation_risk': 'medium',
        'data_import_allowed': 'metadata_only',
        'allowed_action': 'metadata_only',
        'recommended_priority': 'P1_low_risk',
        'reason': 'Facts (ABV, Age, Cask Type) are not copyrightable. Marketing descriptions are protected.',
        'next_script_candidate': 'discover_official_whisky_pages.py'
    },
    {
        'source_category': 'whisky_com',
        'example_sources': 'whisky.com bottle catalog',
        'expected_data_type': 'User reviews, flavor spider charts, community scores',
        'license_page_found': 'yes',
        'robots_policy_status': 'blocked',
        'copyright_risk': 'high',
        'license_risk': 'high',
        'automation_risk': 'high',
        'data_import_allowed': 'no',
        'allowed_action': 'no_scrape_without_explicit_permission',
        'recommended_priority': 'P4_block',
        'reason': 'Commercial proprietary dataset with strict anti-scraping Terms of Service and Cloudflare protection.',
        'next_script_candidate': 'N/A'
    },
    {
        'source_category': 'bottledb_or_api_dataset',
        'example_sources': 'BottleDB API, Water of Life developer endpoint',
        'expected_data_type': 'Structured specifications, barcodes, community averages',
        'license_page_found': 'yes',
        'robots_policy_status': 'allowed',
        'copyright_risk': 'low',
        'license_risk': 'medium',
        'automation_risk': 'low',
        'data_import_allowed': 'yes',
        'allowed_action': 'API_only_if_terms_allow',
        'recommended_priority': 'P1_low_risk',
        'reason': 'Endpoints designed for developer consumption, but license terms must be validated per API instance.',
        'next_script_candidate': 'extract_bottledb_api.py'
    },
    {
        'source_category': 'github_dataset',
        'example_sources': 'whisky-datasets, single-malt-database repos',
        'expected_data_type': 'Flat CSV files, JSON mappings, flavor indices',
        'license_page_found': 'yes',
        'robots_policy_status': 'allowed',
        'copyright_risk': 'low',
        'license_risk': 'medium',
        'automation_risk': 'low',
        'data_import_allowed': 'yes',
        'allowed_action': 'candidate_generation_only',
        'recommended_priority': 'P2_license_check',
        'reason': 'Public repositories under permissive licenses are safe but require attribution and verification.',
        'next_script_candidate': 'audit_github_license.py'
    },
    {
        'source_category': 'community_review_site',
        'example_sources': 'reddit.com/r/scotch, dramming blogs',
        'expected_data_type': 'Full-text user reviews, individual tasting notes',
        'license_page_found': 'yes',
        'robots_policy_status': 'manual_check',
        'copyright_risk': 'high',
        'license_risk': 'high',
        'automation_risk': 'high',
        'data_import_allowed': 'manual_only',
        'allowed_action': 'manual_review_only',
        'recommended_priority': 'P3_manual_only',
        'reason': 'User-generated content belongs to individuals. Bulk scraping tasting notes violates copyrights.',
        'next_script_candidate': 'discover_community_threads.py'
    },
    {
        'source_category': 'ml_embedding_dataset',
        'example_sources': 'Kaggle whiskey flavor profiling dataset',
        'expected_data_type': 'Numerical vector embeddings, flavor categories',
        'license_page_found': 'yes',
        'robots_policy_status': 'allowed',
        'copyright_risk': 'medium',
        'license_risk': 'medium',
        'automation_risk': 'low',
        'data_import_allowed': 'metadata_only',
        'allowed_action': 'candidate_generation_only',
        'recommended_priority': 'P2_license_check',
        'reason': 'Mathematical abstractions of profiles are safe, but backing data must be checked for permissions.',
        'next_script_candidate': 'import_kaggle_embeddings.py'
    },
    {
        'source_category': 'unknown_or_high_risk',
        'example_sources': 'unverified third-party scrapers, retail sites',
        'expected_data_type': 'Raw HTML product catalogs',
        'license_page_found': 'no',
        'robots_policy_status': 'blocked',
        'copyright_risk': 'high',
        'license_risk': 'high',
        'automation_risk': 'high',
        'data_import_allowed': 'no',
        'allowed_action': 'no_scrape_without_explicit_permission',
        'recommended_priority': 'P4_block',
        'reason': 'Blocked by robots.txt, lacks clear ownership, or commercial intent creates legal risks.',
        'next_script_candidate': 'N/A'
    }
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    # 1. Low risk source review (P1 & P2)
    low_risk_sources = [s for s in SOURCES if s['recommended_priority'] in ['P1_low_risk', 'P2_license_check']]
    # 2. Action queue (Immediate P1)
    action_queue = [s for s in SOURCES if s['recommended_priority'] == 'P1_low_risk']
    # 3. Blocked / Manual (P3 & P4)
    blocked_sources = [s for s in SOURCES if s['recommended_priority'] in ['P3_manual_only', 'P4_block']]

    # Write CSVs
    for path, data in [(LOW_RISK_CSV, low_risk_sources), (ACTION_QUEUE_CSV, action_queue), (BLOCKED_CSV, blocked_sources)]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    p1_count = len([s for s in SOURCES if s['recommended_priority'] == 'P1_low_risk'])
    p2_count = len([s for s in SOURCES if s['recommended_priority'] == 'P2_license_check'])
    p3_count = len([s for s in SOURCES if s['recommended_priority'] == 'P3_manual_only'])
    p4_count = len([s for s in SOURCES if s['recommended_priority'] == 'P4_block'])

    # Write MD Report
    report = []
    report.append("# Perplexity Low-Risk Source License & Robots Review Report\n")
    report.append(f"- **Total Source Categories Reviewed:** {len(SOURCES)}")
    report.append(f"- **P1 Low-Risk Count:** {p1_count}")
    report.append(f"- **P2 License-Check Count:** {p2_count}")
    report.append(f"- **P3 Manual-Only Count:** {p3_count}")
    report.append(f"- **P4 Blocked Count:** {p4_count}")
    
    report.append("\n## First Recommended External Lane")
    report.append("**Official Distillery & Brand Pages (P1)**. Harvesting factual specifications like ABV, Age Statements, and Cask Types carries negligible legal risk because facts cannot be copyrighted. Automation must conform to robots.txt delay rules.")

    report.append("\n## What NOT to Scrape")
    report.append("1. **Proprietary Commercial Databases** (like Whisky.com): Protected by complex terms, login interfaces, and active anti-bot systems.\n")
    report.append("2. **Community Review text** (like Reddit r/scotch or personal blogs): Full-text tasting notes are copyrighted by their respective authors. Scraping them for production use violates intellectual property rights without explicit user agreement.")

    report.append("\n## Perplexity Source License Matrix")
    report.append("| Category | Robots Policy | Copyright Risk | Allowed Action | Recommended Priority |")
    report.append("|---|---|---|---|---|")
    for s in SOURCES:
        report.append(f"| {s['source_category']} | {s['robots_policy_status']} | {s['copyright_risk']} | {s['allowed_action']} | {s['recommended_priority']} |")

    report.append("\n## Next Suggested Phases")
    report.append("1. **AŞAMA PERP-2 — Official Source Discovery Pack**: Generate a listing of candidate product urls for whiskies in our coverage gap.\n")
    report.append("2. **AŞAMA PERP-3 — API/GitHub License Deep Review**: Perform an audit of specific Git repositories (like single-malt-db) for valid open-source licensing.\n")
    report.append("3. **AŞAMA PERP-4 — External Candidate Builder Dry Run**: Build candidate profile vectors based on extracted factual parameters.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Perplexity license matrix compiled successfully, blocking high-risk channels and establishing safe lanes).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

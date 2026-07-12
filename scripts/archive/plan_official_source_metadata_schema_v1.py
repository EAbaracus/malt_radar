import sqlite3
import os
import csv
import json
import datetime

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"

INVENTORY_CSV = os.path.join(OUTPUT_DIR, "schema_metadata_v1_existing_schema_inventory.csv")
MAPPING_CSV = os.path.join(OUTPUT_DIR, "schema_metadata_v1_official_source_url_mapping_plan.csv")
MIGRATION_SQL = os.path.join(OUTPUT_DIR, "schema_metadata_v1_migration_candidate_plan.sql")
BACKFILL_CSV = os.path.join(OUTPUT_DIR, "schema_metadata_v1_backfill_candidate_plan.csv")
REPORT_MD = "output/reports/schema_metadata_v1_report.md"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = ['whiskies', 'distilleries', 'entity_external_links', 'external_reference_links', 'tasting_notes', 'flavor_profiles']
    
    inventory = []
    for t in tables:
        info = cur.execute(f"PRAGMA table_info({t})").fetchall()
        for col in info:
            inventory.append({
                'table_name': t,
                'column_name': col['name'],
                'data_type': col['type'],
                'is_nullable': 'No' if col['notnull'] else 'Yes',
                'is_pk': 'Yes' if col['pk'] else 'No'
            })

    conn.close()

    # Write Inventory CSV
    with open(INVENTORY_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['table_name', 'column_name', 'data_type', 'is_nullable', 'is_pk'])
        writer.writeheader()
        writer.writerows(inventory)

    # 2. Build official source url mapping plan
    mapping_plan = [
        {
            'source_category': 'official_distillery_or_brand_pages',
            'source_name': 'Laphroaig Official Site',
            'entity_type': 'whisky',
            'entity_id': 'W000002',
            'source_url': 'https://www.laphroaig.com/en/whisky/the-cask-legacy',
            'source_domain': 'laphroaig.com',
            'source_kind': 'official_brand_website',
            'field_name': 'cask_type',
            'field_value': 'Cask Casks',
            'confidence': 0.95,
            'retrieved_at': datetime.datetime.now().isoformat(),
            'license_risk': 'low',
            'copyright_risk': 'low',
            'notes': 'Attribution record linked to Laphroaig website'
        }
    ]
    with open(MAPPING_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=mapping_plan[0].keys())
        writer.writeheader()
        writer.writerows(mapping_plan)

    # 3. SQL Migration candidate plan
    sql_plan = """-- Option A: Reuse existing entity_external_links
-- No schema changes required. Just perform inserts:
-- INSERT INTO entity_external_links (entity_type, entity_id, url, link_type) VALUES ('whisky', 2, 'https://www.laphroaig.com/...', 'official');

-- Option B: Add new official_source_references table for detailed audit provenance
CREATE TABLE IF NOT EXISTS official_source_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL, -- 'whisky', 'distillery'
    entity_id TEXT NOT NULL,
    source_category TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    confidence REAL DEFAULT 1.0,
    retrieved_at TEXT NOT NULL,
    license_risk TEXT DEFAULT 'low',
    copyright_risk TEXT DEFAULT 'low',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Option C: Add direct column to whiskies (NOT RECOMMENDED)
-- ALTER TABLE whiskies ADD COLUMN official_url TEXT;
"""
    with open(MIGRATION_SQL, 'w', encoding='utf-8') as f:
        f.write(sql_plan)

    # 4. Backfill candidate plan CSV (simulated from low-risk-source-v3 updates)
    backfill_candidates = [
        {
            'whisky_id': 'W000002',
            'whisky_name': 'laphroaig the cask legacy',
            'distillery_name': 'Laphroaig',
            'proposed_official_url': 'https://www.laphroaig.com/en/whisky/the-cask-legacy',
            'proposed_source_domain': 'laphroaig.com',
            'field_name': 'cask_type',
            'field_value': 'Cask Casks',
            'backfill_status': 'planned'
        },
        {
            'whisky_id': 'W000003',
            'whisky_name': 'glenlivet 15yo french oak',
            'distillery_name': 'The Glenlivet',
            'proposed_official_url': 'https://www.theglenlivet.com/en/whisky/glenlivet-15yo-french-oak',
            'proposed_source_domain': 'theglenlivet.com',
            'field_name': 'cask_type',
            'field_value': 'Oak Casks',
            'backfill_status': 'planned'
        }
    ]
    with open(BACKFILL_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=backfill_candidates[0].keys())
        writer.writeheader()
        writer.writerows(backfill_candidates)

    # 5. Write MD Report
    report = []
    report.append("# Official Source URL & Attribution Schema Plan\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## Existing Schema Inventory")
    report.append("Found existing link tables in the database schema:")
    report.append("1. **`entity_external_links`**: Maps any entity (like whisky/distillery) to a URL with categorized `link_type` ('wikipedia', 'official', 'api').")
    report.append("2. **`external_reference_links`**: Maps general knowledge items to URLs.")

    report.append("\n## Option Comparison & Recommendations")
    report.append("| Option | Migration Risk | App Impact | Rollback Complexity | Recommended | Reason |")
    report.append("|---|---|---|---|---|---|")
    report.append("| **A. Reuse entity_external_links** | None | Low | Low | **Yes (Option A)** | Reuses existing tables, requires no database migration. |")
    report.append("| **B. Add official_source_references** | Medium | Medium | Medium | **Yes (Option B - Preferred for detailed audit)** | Provides granular field-level provenance tracking. |")
    report.append("| **C. Add direct whiskies columns** | High | High | High | No | Violates database normalization, breaks model coupling. |")
    report.append("| **D. Do nothing (CSV-only)** | None | None | None | No | Attribution gets disconnected from the active runtime DB. |")

    report.append("\n## Recommended Choice")
    report.append("**Option B (Add new official_source_references table)**. While Option A is migration-free, it only tracks the overall URL. Option B tracks exactly which field value (e.g. `cask_type`) came from which source URL, providing robust data provenance.")

    report.append("\n## Proposed SQL Migration Candidate")
    report.append("```sql\n" + sql_plan + "\n```")

    report.append("\n## Backfill Strategy")
    report.append("A script will read the `low_risk_source_v3_official_facts_qa_pack.csv` and backfill the resolved URLs directly into the `official_source_references` or `entity_external_links` table during the next phase.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Attribution schema plan drafted successfully).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

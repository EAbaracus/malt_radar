import os
import sqlite3
from datetime import datetime

DB_PATH = "output/import/production.db"
DRY_RUN_CSV = "data/manual_sources/books/review_csv/book_profile_staging_dry_run_preview.csv"
REPORT_FILE = "output/reports/12za_notebooklm_flavor_profile_staging_schema_plan.md"
GATE_FILE = "output/reports/12za_notebooklm_flavor_profile_staging_schema_gate.txt"
SQL_FILE = "output/sql/12za_create_staging_book_flavor_profiles_preview.sql"

def main():
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(SQL_FILE), exist_ok=True)
    
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    # 1. Fetch flavor_profiles schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='flavor_profiles'")
    res = cursor.fetchone()
    flavor_profiles_schema = res[0] if res else "NOT FOUND"
    
    # 2. SQL Creation
    sql_content = """-- Preview SQL for staging_book_flavor_profiles
CREATE TABLE staging_book_flavor_profiles (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whisky_id TEXT NOT NULL,
    whisky_name TEXT,
    production_bottle_name TEXT,
    match_score INTEGER,
    match_method TEXT,
    flavor_vector TEXT,
    flavor_profile TEXT,
    flavor_tags TEXT,
    flavor_source TEXT,
    flavor_data_confidence TEXT,
    production_region TEXT,
    notes_for_review TEXT,
    
    -- Staging/Review metadata
    source_system TEXT,
    source_book TEXT,
    source_page_or_section TEXT,
    distillery_name TEXT,
    age_statement TEXT,
    cask_or_maturation TEXT,
    abv REAL,
    nose_summary TEXT,
    palate_summary TEXT,
    finish_summary TEXT,
    overall_style_summary TEXT,
    match_strategy TEXT,
    decision_reason TEXT,
    conflict_existing_profile INTEGER DEFAULT 0,
    radar_conflict INTEGER DEFAULT 0,
    approval_status TEXT DEFAULT 'staging_pending_review',
    reviewer_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Radar Raw Columns
    smoky INTEGER,
    peaty INTEGER,
    sherry INTEGER,
    fruity INTEGER,
    floral INTEGER,
    spicy INTEGER,
    sweet INTEGER,
    oak INTEGER,
    maritime INTEGER,
    winey INTEGER,
    malty INTEGER,
    nutty INTEGER,
    herbal INTEGER,
    waxy INTEGER,
    oily INTEGER,
    light_body INTEGER,
    rich_body INTEGER
);

CREATE INDEX idx_staging_book_flavor_profiles_whisky_id ON staging_book_flavor_profiles(whisky_id);
CREATE INDEX idx_staging_book_flavor_profiles_approval_status ON staging_book_flavor_profiles(approval_status);
CREATE INDEX idx_staging_book_flavor_profiles_source_system ON staging_book_flavor_profiles(source_system);
"""
    with open(SQL_FILE, 'w', encoding='utf-8') as f:
        f.write(sql_content)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    # 3. Report Generation
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# NotebookLM Flavor Profile Staging Schema Plan\n\n")
        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- has_flavor_profiles_table: {'Yes' if flavor_profiles_schema != 'NOT FOUND' else 'No'}\n\n")
        f.write("## Existing flavor_profiles Schema\n")
        f.write("```sql\n" + flavor_profiles_schema + "\n```\n\n")
        f.write("## Proposed staging_book_flavor_profiles Schema\n")
        f.write("```sql\n" + sql_content + "\n```\n")
        
    # 4. Gate Logic
    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        f.write("NEEDS_STAGING_SCHEMA\n")
        f.write("GO_FOR_SCHEMA_REVIEW\n")
        f.write("PRODUCTION_IMPORT_NO-GO\n")

if __name__ == '__main__':
    main()

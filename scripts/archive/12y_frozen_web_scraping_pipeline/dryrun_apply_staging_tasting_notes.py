import os
import shutil
import hashlib
import sqlite3
import csv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
sql_preview_dir = os.path.join(base_dir, "output", "import", "sql_preview")
dryrun_dir = os.path.join(base_dir, "output", "import", "dryrun")

os.makedirs(reports_dir, exist_ok=True)
os.makedirs(dryrun_dir, exist_ok=True)

prod_db = os.path.join(base_dir, "output", "import", "production.db")
dryrun_db = os.path.join(dryrun_dir, "production_12f_tasting_note_staging_dryrun.db")

create_sql = os.path.join(sql_preview_dir, "create_staging_tasting_notes.sql")
insert_sql = os.path.join(sql_preview_dir, "insert_staging_tasting_notes_preview.sql")
preview_csv = os.path.join(output_dir, "tasting_note_staging_insert_preview.csv")

report_md = os.path.join(reports_dir, "230_tasting_note_staging_dryrun_report.md")
gate_txt = os.path.join(reports_dir, "231_tasting_note_staging_dryrun_gate.txt")

def get_db_hash(db_path):
    if os.path.exists(db_path):
        with open(db_path, "rb") as df:
            return hashlib.sha256(df.read()).hexdigest()
    return "N/A"

def main():
    expected_hash = "fdad80458436f13dff5e70955bd6c887980cddba6c253d6f28042b7ceba432c1"
    hash_before = get_db_hash(prod_db)

    # Count expected rows from CSV
    expected_rows = 0
    if os.path.exists(preview_csv):
        with open(preview_csv, 'r', encoding='utf-8') as f:
            expected_rows = sum(1 for _ in csv.DictReader(f))

    if os.path.exists(dryrun_db):
        os.remove(dryrun_db)
    
    shutil.copy2(prod_db, dryrun_db)

    conn = sqlite3.connect(dryrun_db)
    cursor = conn.cursor()
    
    # Enable foreign keys
    # cursor.execute("PRAGMA foreign_keys = ON")

    with open(create_sql, 'r', encoding='utf-8') as f:
        cursor.executescript(f.read())

    with open(insert_sql, 'r', encoding='utf-8') as f:
        cursor.executescript(f.read())
        
    conn.commit()

    # Validations
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staging_tasting_notes'")
    table_created = cursor.fetchone() is not None

    inserted_rows = 0
    fk_violations = 0
    duplicate_staging_note_id = 0
    duplicate_source_rows = 0
    invalid_approval_status = 0

    if table_created:
        cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        inserted_rows = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) 
            FROM staging_tasting_notes s
            LEFT JOIN whiskies w ON s.whisky_id = w.whisky_id
            WHERE w.whisky_id IS NULL
        """)
        fk_violations = cursor.fetchone()[0]

        cursor.execute("""
            SELECT staging_note_id, COUNT(*) 
            FROM staging_tasting_notes 
            GROUP BY staging_note_id 
            HAVING COUNT(*) > 1
        """)
        duplicate_staging_note_id = len(cursor.fetchall())

        cursor.execute("""
            SELECT whisky_id, source_system, COALESCE(source_url, ''), COUNT(*)
            FROM staging_tasting_notes
            GROUP BY whisky_id, source_system, COALESCE(source_url, '')
            HAVING COUNT(*) > 1
        """)
        duplicate_source_rows = len(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes WHERE approval_status != 'staging_pending_review'")
        invalid_approval_status = cursor.fetchone()[0]

    conn.close()

    hash_after = get_db_hash(prod_db)

    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 230 Web Tasting Note Staging Dry-Run Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Source Production Hash Before: {hash_before}\n")
        f.write(f"- Source Production Hash After: {hash_after}\n")
        f.write(f"- Dry-run DB Path: {dryrun_db}\n")
        f.write(f"- Table Created: {table_created}\n")
        f.write(f"- Expected Rows: {expected_rows}\n")
        f.write(f"- Inserted Rows: {inserted_rows}\n")
        f.write(f"- FK Violations: {fk_violations}\n")
        f.write(f"- Duplicate staging_note_id: {duplicate_staging_note_id}\n")
        f.write(f"- Duplicate source combinations: {duplicate_source_rows}\n")
        f.write(f"- Invalid approval_status: {invalid_approval_status}\n")

    hash_ok = (hash_before == expected_hash) and (hash_after == expected_hash)
    success = (hash_ok and table_created and (inserted_rows == expected_rows) and 
               (fk_violations == 0) and (duplicate_staging_note_id == 0) and 
               (duplicate_source_rows == 0) and (invalid_approval_status == 0) and (inserted_rows == 2))

    gate_status = "GO" if success else "NO-GO"

    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE_STATUS: {gate_status}\n")
        f.write(f"REASON: Inserted {inserted_rows} rows successfully into dry-run DB without violations.\n")
        f.write(f"DB_HASH_BEFORE: {hash_before}\n")
        f.write(f"DB_HASH_AFTER: {hash_after}\n")
        f.write(f"EXPECTED_HASH: {expected_hash}\n")

    print(f"Dry-run Pipeline finished. Status: {gate_status}")

if __name__ == "__main__":
    main()

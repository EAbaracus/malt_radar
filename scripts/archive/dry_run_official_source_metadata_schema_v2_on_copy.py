import sqlite3
import os
import shutil
import hashlib
import csv
import json
import datetime

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/schema_metadata_v2_dry_run.db"

MIGRATION_SQL_PATH = "data/output/schema_metadata_v1_migration_candidate_plan.sql"
BACKFILL_PLAN_CSV = "data/output/schema_metadata_v1_backfill_candidate_plan.csv"
UPDATE_PLAN_CSV = "data/output/low_risk_source_v3_official_facts_update_plan.csv"

RESULTS_CSV = "data/output/schema_metadata_v2_dry_run_backfill_results.csv"
VALIDATION_CSV = "data/output/schema_metadata_v2_table_validation.csv"
REPORT_MD = "output/reports/schema_metadata_v2_dry_run_report.md"

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

def main():
    os.makedirs(os.path.dirname(DRY_RUN_DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)

    # 1. Copy DB
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created Dry-Run DB: {DRY_RUN_DB_PATH}")

    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    migration_executed = "No"
    table_exists = "No"
    columns = []

    # 2. Run CREATE TABLE official_source_references
    create_sql = """CREATE TABLE IF NOT EXISTS official_source_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
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
);"""
    
    try:
        cur.execute(create_sql)
        migration_executed = "Yes"
        
        # Verify table exists
        verify = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='official_source_references'").fetchone()
        if verify:
            table_exists = "Yes"
            info = cur.execute("PRAGMA table_info(official_source_references)").fetchall()
            columns = [col['name'] for col in info]
    except Exception as e:
        print(f"Migration error: {e}")

    # 3. Read backfill candidates and run inserts
    candidates = []
    
    # Read from backfill plan csv if exists
    if os.path.exists(BACKFILL_PLAN_CSV):
        with open(BACKFILL_PLAN_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidates.append({
                    'whisky_id': row.get('whisky_id'),
                    'whisky_name': row.get('whisky_name'),
                    'distillery_name': row.get('distillery_name'),
                    'proposed_official_url': row.get('proposed_official_url'),
                    'proposed_source_domain': row.get('proposed_source_domain'),
                    'field_name': row.get('field_name'),
                    'field_value': row.get('field_value')
                })

    # Read from updates plan csv if exists
    if os.path.exists(UPDATE_PLAN_CSV):
        with open(UPDATE_PLAN_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                updates = json.loads(row.get('updates_to_apply', '{}'))
                for field, val in updates.items():
                    candidates.append({
                        'whisky_id': row.get('whisky_id'),
                        'whisky_name': row.get('whisky_name'),
                        'distillery_name': row.get('distillery_name'),
                        'proposed_official_url': row.get('proposed_official_url'),
                        'proposed_source_domain': row.get('proposed_source_domain'),
                        'field_name': field,
                        'field_value': str(val)
                    })

    backfill_results = []
    inserted_count = 0
    duplicate_skipped = 0
    invalid_skipped = 0

    inserted_fingerprints = set()

    for c in candidates:
        wid = c['whisky_id']
        url = c['proposed_official_url']
        domain = c['proposed_source_domain']
        field = c['field_name']
        val = c['field_value']
        dist = c['distillery_name']

        if not wid or not url or url == 'N/A' or not field:
            invalid_skipped += 1
            continue

        fingerprint = f"{wid}|{url}|{field}|{val}"
        if fingerprint in inserted_fingerprints:
            duplicate_skipped += 1
            continue

        # Insert reference
        try:
            cur.execute("""
                INSERT INTO official_source_references (
                    entity_type, entity_id, source_category, source_name,
                    source_url, source_domain, field_name, field_value,
                    confidence, retrieved_at, license_risk, copyright_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'whisky',
                wid,
                'official_facts',
                f"{dist} Official Brand Website",
                url,
                domain if domain else 'N/A',
                field,
                val,
                0.95,
                datetime.datetime.now().isoformat(),
                'low',
                'low'
            ))
            inserted_count += 1
            inserted_fingerprints.add(fingerprint)
            
            res_row = dict(c)
            res_row['status'] = 'inserted'
            backfill_results.append(res_row)
        except Exception as e:
            print(f"Insert error: {e}")
            invalid_skipped += 1

    # PRAGMA integrity check
    integrity = cur.execute("PRAGMA integrity_check").fetchone()
    integrity_status = integrity[0] if integrity else "Failed"

    conn.commit()
    conn.close()

    # Write Results CSV
    if backfill_results:
        with open(RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=backfill_results[0].keys())
            writer.writeheader()
            writer.writerows(backfill_results)

    # Write Validation CSV
    validation = [
        {'step': 'migration_executed', 'value': migration_executed},
        {'step': 'official_source_references_exists', 'value': table_exists},
        {'step': 'columns_detected', 'value': ", ".join(columns)},
        {'step': 'integrity_check', 'value': integrity_status}
    ]
    with open(VALIDATION_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['step', 'value'])
        writer.writeheader()
        writer.writerows(validation)

    hash_after = get_file_hash(DB_PATH)

    # Count by field name and source domain
    field_counts = {}
    domain_counts = {}
    for c in backfill_results:
        f = c['field_name']
        d = c['proposed_source_domain']
        field_counts[f] = field_counts.get(f, 0) + 1
        domain_counts[d] = domain_counts.get(d, 0) + 1

    # Write MD Report
    report = []
    report.append("# SCHEMA-METADATA-V2: Dry-Run Migration Report\n")
    report.append(f"- **Dry-Run Executed on Copy:** {migration_executed}")
    report.append(f"- **Table official_source_references Exists:** {table_exists}")
    report.append(f"- **Columns Detected:** {', '.join(columns) if columns else 'None'}")
    
    report.append("\n## Backfill Metrics")
    report.append(f"- Backfill Input Count: {len(candidates)}")
    report.append(f"- Inserted Reference Count: {inserted_count}")
    report.append(f"- Duplicate Skipped Count: {duplicate_skipped}")
    report.append(f"- Invalid/Skipped Count: {invalid_skipped}")

    report.append("\n## References by Field Name")
    for f, cnt in field_counts.items():
        report.append(f"- `{f}`: {cnt} references")

    report.append("\n## References by Source Domain")
    for d, cnt in domain_counts.items():
        report.append(f"- `{d}`: {cnt} references")

    report.append(f"\n- **PRAGMA integrity_check:** {integrity_status}")
    report.append(f"- **Original DB Hash Before:** `{hash_before}`")
    report.append(f"- **Original DB Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_before == hash_after else 'NO (DB MUTATION DETECTED!)'}")

    report.append("\n## Final GO/NO-GO")
    if table_exists == 'Yes' and integrity_status.lower() == 'ok' and hash_before == hash_after:
        report.append("**GO** (Schema dry-run migration and backfill simulation successfully verified).")
    else:
        report.append("**NO-GO** (Dry-run failed or database integrity is corrupted).")

    report.append("\n## Next Phase Suggestion")
    report.append("- **AŞAMA SCHEMA-METADATA-V3 — Guarded Migration Apply Script**: Create the actual migration and backfill script with transaction protection for production DB.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

import sqlite3
import os
import shutil
import hashlib
import csv
import json
import argparse
import datetime

DB_PATH = "output/import/production.db"
UPDATE_PLAN_CSV = "data/output/low_risk_source_v3_official_facts_update_plan.csv"
BACKFILL_RESULTS_CSV = "data/output/schema_metadata_v2_dry_run_backfill_results.csv"
REPORT_MD_PATH = "output/reports/schema_metadata_v3_apply_report.md"

EXPECTED_INSERTED = 18
EXPECTED_DUPLICATE_SKIPPED = 0

CREATE_TABLE_SQL = """CREATE TABLE IF NOT EXISTS official_source_references (
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

def build_candidates():
    """Build reference candidates from update plan."""
    candidates = []
    if not os.path.exists(UPDATE_PLAN_CSV):
        return candidates

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
    return candidates

def main():
    parser = argparse.ArgumentParser(description="Guarded apply script for official source metadata schema.")
    parser.add_argument('--apply', action='store_true', help='Execute database mutations')
    parser.add_argument('--confirm', type=str, help='Verification confirmation phrase')
    args = parser.parse_args()

    is_dry_run = not args.apply
    confirm_phrase = args.confirm
    expected_phrase = "WRITE GO: apply official source metadata schema to production.db"

    if not is_dry_run:
        if confirm_phrase != expected_phrase:
            print("Error: Invalid or missing confirmation phrase.")
            print(f'Use: --confirm "{expected_phrase}"')
            return

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"output/import/production_before_official_source_metadata_schema_v3_{timestamp}.db"

    # Choose target DB
    if is_dry_run:
        target_db = "output/tmp/schema_metadata_v3_dry_run_temp.db"
        os.makedirs(os.path.dirname(target_db), exist_ok=True)
        shutil.copy2(DB_PATH, target_db)
    else:
        target_db = DB_PATH
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup created at: {backup_path}")

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    execution_status = "Success"
    table_created = "No"
    table_already_existed = "No"
    integrity_status = "Skipped"
    inserted_count = 0
    duplicate_skipped = 0
    invalid_skipped = 0
    field_counts = {}
    domain_counts = {}

    candidates = build_candidates()

    try:
        cur.execute("BEGIN TRANSACTION;")

        # Check if table already exists
        existing = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='official_source_references'"
        ).fetchone()

        if existing:
            table_already_existed = "Yes"
        else:
            table_already_existed = "No"

        # 4. Create table (idempotent via CREATE TABLE IF NOT EXISTS)
        cur.execute(CREATE_TABLE_SQL)
        verify = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='official_source_references'"
        ).fetchone()
        if verify:
            table_created = "Yes" if table_already_existed == "No" else "Already Existed"

        # 5. Build de-dupe set from existing rows
        existing_rows = cur.execute(
            "SELECT entity_id, source_url, field_name, field_value FROM official_source_references"
        ).fetchall()
        existing_fps = {
            f"{r['entity_id']}|{r['source_url']}|{r['field_name']}|{r['field_value']}"
            for r in existing_rows
        }

        inserted_fingerprints = set(existing_fps)

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

            field_counts[field] = field_counts.get(field, 0) + 1
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # 8. Validation against expected counts
        if inserted_count != EXPECTED_INSERTED:
            raise Exception(
                f"Insert count mismatch: expected {EXPECTED_INSERTED}, got {inserted_count}."
            )
        if duplicate_skipped != EXPECTED_DUPLICATE_SKIPPED:
            raise Exception(
                f"Duplicate-skipped count mismatch: expected {EXPECTED_DUPLICATE_SKIPPED}, got {duplicate_skipped}."
            )

        # 9. Integrity check
        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"
        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed.")

        cur.execute("COMMIT;")
        print(f"Transaction committed. Mode: {'APPLY' if not is_dry_run else 'DRY-RUN'}")

    except Exception as e:
        cur.execute("ROLLBACK;")
        execution_status = f"Failed (Rollback): {e}"
        print(f"Error (Rolled Back): {e}")
        inserted_count = 0
        duplicate_skipped = 0

    conn.close()

    if is_dry_run and os.path.exists(target_db):
        os.remove(target_db)

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)

    # Write Report
    report = []
    report.append("# SCHEMA-METADATA-V3: Guarded Migration Apply Report\n")
    report.append(f"- **Execution Mode:** {'APPLY' if not is_dry_run else 'DRY-RUN (Simülasyon)'}")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Execution Status:** {execution_status}")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (DB MUTATED)'}")
    if not is_dry_run and execution_status.startswith("Success"):
        report.append(f"- **Backup DB:** `{backup_path}`")

    report.append("\n## Migration Metrics")
    report.append(f"- Table Created: {table_created}")
    report.append(f"- Table Already Existed: {table_already_existed}")
    report.append(f"- Planned Reference Count: {len(candidates)}")
    report.append(f"- Inserted Reference Count: {inserted_count}")
    report.append(f"- Duplicate Skipped Count: {duplicate_skipped}")
    report.append(f"- Invalid/Skipped Count: {invalid_skipped}")

    report.append("\n## References by Field Name")
    for f, cnt in field_counts.items():
        report.append(f"- `{f}`: {cnt}")

    report.append("\n## References by Source Domain")
    for d, cnt in domain_counts.items():
        report.append(f"- `{d}`: {cnt}")

    report.append(f"\n- **PRAGMA integrity_check:** {integrity_status}")

    report.append("\n## Final GO/NO-GO")
    if execution_status.startswith("Success") and integrity_status.lower() == 'ok':
        report.append("**GO** (Guarded apply execution verified successfully).")
    else:
        report.append("**NO-GO** (Apply validation failed or integrity check failed).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

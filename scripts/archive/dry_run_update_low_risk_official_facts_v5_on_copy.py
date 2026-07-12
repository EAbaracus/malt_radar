import sqlite3
import os
import shutil
import hashlib
import csv
import json
import datetime

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/low_risk_source_v5_official_facts_dry_run.db"
UPDATE_PLAN_CSV = "data/output/low_risk_source_v5_official_facts_update_plan.csv"
SOURCE_REFS_PLAN_CSV = "data/output/low_risk_source_v5_official_source_references_plan.csv"
DRY_RUN_REPORT_MD = "output/reports/low_risk_source_v5_official_facts_dry_run_report.md"

CREATE_REFS_TABLE_SQL = """CREATE TABLE IF NOT EXISTS official_source_references (
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

def is_empty(val):
    if val is None:
        return True
    return str(val).strip().lower() in ['', 'null', 'n/a', 'none', 'unknown']

def main():
    os.makedirs(os.path.dirname(DRY_RUN_DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DRY_RUN_REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(UPDATE_PLAN_CSV):
        print(f"Error: Update plan CSV not found at {UPDATE_PLAN_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created Dry-Run DB Copy: {DRY_RUN_DB_PATH}")

    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ensure official_source_references exists on copy
    cur.execute(CREATE_REFS_TABLE_SQL)

    def count_missing():
        rows = cur.execute("SELECT age, abv, region, cask_type FROM whiskies").fetchall()
        m = {'age': 0, 'abv': 0, 'region': 0, 'cask_type': 0}
        for r in rows:
            if is_empty(r['age']): m['age'] += 1
            if is_empty(r['abv']): m['abv'] += 1
            if is_empty(r['region']): m['region'] += 1
            if is_empty(r['cask_type']): m['cask_type'] += 1
        return m

    missing_before = count_missing()

    update_candidates = []
    with open(UPDATE_PLAN_CSV, 'r', encoding='utf-8') as f:
        update_candidates = list(csv.DictReader(f))

    source_refs = []
    if os.path.exists(SOURCE_REFS_PLAN_CSV):
        with open(SOURCE_REFS_PLAN_CSV, 'r', encoding='utf-8') as f:
            source_refs = list(csv.DictReader(f))

    updated_rows = 0
    updated_fields = {'age': 0, 'abv': 0, 'region': 0, 'cask_type': 0}
    inserted_refs = 0
    duplicate_refs_skipped = 0

    execution_status = "Success"
    integrity_status = "Skipped"

    try:
        cur.execute("BEGIN TRANSACTION;")

        # Step 1: Update whiskies metadata
        for c in update_candidates:
            wid = str(c.get('whisky_id'))
            updates_str = c.get('updates_to_apply', '{}')
            updates = json.loads(updates_str)

            if updates:
                set_clauses = []
                params = []
                for field, val in updates.items():
                    # Guard: only update if currently empty
                    current = cur.execute(f"SELECT {field} FROM whiskies WHERE whisky_id = ?", (wid,)).fetchone()
                    if current and is_empty(current[0]):
                        set_clauses.append(f"{field} = ?")
                        params.append(val)
                        updated_fields[field] = updated_fields.get(field, 0) + 1

                if set_clauses:
                    params.append(wid)
                    cur.execute(f"UPDATE whiskies SET {', '.join(set_clauses)} WHERE whisky_id = ?", params)
                    updated_rows += 1

        # Step 2: Insert source references
        existing_fps = set()
        for r in cur.execute("SELECT entity_id, source_url, field_name, field_value FROM official_source_references").fetchall():
            existing_fps.add(f"{r['entity_id']}|{r['source_url']}|{r['field_name']}|{r['field_value']}")

        for ref in source_refs:
            wid = ref.get('whisky_id')
            url = ref.get('proposed_official_url', 'N/A')
            domain = ref.get('proposed_source_domain', 'N/A')
            field = ref.get('field_name')
            val = ref.get('field_value')

            if not wid or not url or url == 'N/A':
                continue

            fp = f"{wid}|{url}|{field}|{val}"
            if fp in existing_fps:
                duplicate_refs_skipped += 1
                continue

            cur.execute("""
                INSERT INTO official_source_references (
                    entity_type, entity_id, source_category, source_name,
                    source_url, source_domain, field_name, field_value,
                    confidence, retrieved_at, license_risk, copyright_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'whisky', wid, 'official_facts', f"{ref.get('proposed_source_domain', '')} Official Site",
                url, domain, field, val,
                float(ref.get('confidence', 0.92)),
                datetime.datetime.now().isoformat(),
                'low', 'low'
            ))
            inserted_refs += 1
            existing_fps.add(fp)

        missing_after = count_missing()

        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed.")

        cur.execute("COMMIT;")
        print("Dry-run database updates completed successfully.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        execution_status = f"Failed (Rollback): {e}"
        print(f"Error (Rolled Back): {e}")
        missing_after = missing_before

    conn.close()

    hash_after = get_file_hash(DB_PATH)

    # Write Report
    report = []
    report.append("# Low-Risk Official Facts Batch V5 Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run Copy:** `{DRY_RUN_DB_PATH}`")
    report.append(f"- **Execution Status:** {execution_status}")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_before == hash_after else 'NO (MUTATION)'}")

    report.append("\n## Dry-Run Metrics (on Copy DB)")
    report.append(f"- Updated Whisky Rows: {updated_rows}")
    report.append(f"- Updated Age Statements: {updated_fields.get('age', 0)}")
    report.append(f"- Updated ABV Values: {updated_fields.get('abv', 0)}")
    report.append(f"- Updated Regions: {updated_fields.get('region', 0)}")
    report.append(f"- Updated Cask Types: {updated_fields.get('cask_type', 0)}")
    report.append(f"- Inserted Source References: {inserted_refs}")
    report.append(f"- Duplicate Source Refs Skipped: {duplicate_refs_skipped}")

    report.append("\n## Missing Fields Progression (Before -> After)")
    report.append(f"- Missing Age: {missing_before['age']} -> {missing_after['age']} (Gain: +{missing_before['age'] - missing_after['age']})")
    report.append(f"- Missing ABV: {missing_before['abv']} -> {missing_after['abv']} (Gain: +{missing_before['abv'] - missing_after['abv']})")
    report.append(f"- Missing Region: {missing_before['region']} -> {missing_after['region']} (Gain: +{missing_before['region'] - missing_after['region']})")
    report.append(f"- Missing Cask Type: {missing_before['cask_type']} -> {missing_after['cask_type']} (Gain: +{missing_before['cask_type'] - missing_after['cask_type']})")

    report.append(f"\n- **PRAGMA integrity_check:** {integrity_status}")

    report.append("\n## Final GO/NO-GO")
    if execution_status.startswith("Success") and integrity_status.lower() == 'ok' and hash_before == hash_after:
        report.append("**GO** (V5 dry-run simulation successfully verified on DB copy).")
    else:
        report.append("**NO-GO** (Dry-run failed or hash mismatch detected).")

    with open(DRY_RUN_REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {DRY_RUN_REPORT_MD}")

if __name__ == "__main__":
    main()

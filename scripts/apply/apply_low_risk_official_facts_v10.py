import sqlite3
import os
import shutil
import hashlib
import csv
import json
import argparse
import datetime

DB_PATH = "output/import/production.db"
UPDATE_PLAN_CSV = "data/output/low_risk_source_v9_official_facts_update_plan.csv"
SOURCE_REFS_PLAN_CSV = "data/output/low_risk_source_v9_official_source_references_plan.csv"
REPORT_MD_PATH = "output/reports/low_risk_source_v10_official_facts_apply_report.md"

# Expected from V9 dry-run
EXPECTED_UPDATED_ROWS = 7
EXPECTED_REGION_UPDATES = 3
EXPECTED_CASK_UPDATES = 6
EXPECTED_SOURCE_REFS = 9

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

def count_missing(cur, field):
    return cur.execute(
        f"SELECT count(*) FROM whiskies WHERE {field} IS NULL OR trim({field}) IN ('', 'NULL', 'N/A', 'none', 'unknown')"
    ).fetchone()[0]

def main():
    parser = argparse.ArgumentParser(description="Guarded apply for official facts batch 4.")
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm', type=str, default='')
    args = parser.parse_args()

    is_dry_run = not args.apply
    expected_phrase = "WRITE GO: apply low risk official facts batch 4 to production.db"

    if not is_dry_run and args.confirm != expected_phrase:
        print("Error: Invalid or missing confirmation phrase.")
        print(f'Use: --confirm "{expected_phrase}"')
        return

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return
    if not os.path.exists(UPDATE_PLAN_CSV):
        print(f"Error: Update plan not found at {UPDATE_PLAN_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"output/import/production_before_low_risk_official_facts_v10_{timestamp}.db"

    if is_dry_run:
        target_db = "output/tmp/low_risk_source_v10_dry_run_temp.db"
        os.makedirs(os.path.dirname(target_db), exist_ok=True)
        shutil.copy2(DB_PATH, target_db)
    else:
        target_db = DB_PATH
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(CREATE_REFS_TABLE_SQL)

    missing_region_before = count_missing(cur, 'region')
    missing_cask_before   = count_missing(cur, 'cask_type')

    update_candidates = []
    with open(UPDATE_PLAN_CSV, 'r', encoding='utf-8') as f:
        update_candidates = list(csv.DictReader(f))

    source_refs = []
    if os.path.exists(SOURCE_REFS_PLAN_CSV):
        with open(SOURCE_REFS_PLAN_CSV, 'r', encoding='utf-8') as f:
            source_refs = list(csv.DictReader(f))

    applied_rows = 0
    applied_region = 0
    applied_cask = 0
    skipped_present = 0
    inserted_refs = 0
    duplicate_refs_skipped = 0
    execution_status = "Success"
    integrity_status = "Skipped"

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in update_candidates:
            wid = str(c.get('whisky_id'))
            updates = json.loads(c.get('updates_to_apply', '{}'))

            set_clauses = []
            params = []
            for field, val in updates.items():
                if field not in ('region', 'cask_type'):
                    continue
                current = cur.execute(f"SELECT {field} FROM whiskies WHERE whisky_id = ?", (wid,)).fetchone()
                if current and is_empty(current[0]):
                    set_clauses.append(f"{field} = ?")
                    params.append(val)
                    if field == 'region':
                        applied_region += 1
                    elif field == 'cask_type':
                        applied_cask += 1
                else:
                    skipped_present += 1

            if set_clauses:
                params.append(wid)
                cur.execute(f"UPDATE whiskies SET {', '.join(set_clauses)} WHERE whisky_id = ?", params)
                applied_rows += 1

        existing_fps = set()
        for r in cur.execute("SELECT entity_id, source_url, field_name, field_value FROM official_source_references").fetchall():
            existing_fps.add(f"{r['entity_id']}|{r['source_url']}|{r['field_name']}|{r['field_value']}")

        inserted_fps = set(existing_fps)
        for ref in source_refs:
            wid = ref.get('whisky_id')
            url = ref.get('proposed_official_url', 'N/A')
            domain = ref.get('proposed_source_domain', 'N/A')
            field = ref.get('field_name')
            val = ref.get('field_value')

            if not wid or not url or url == 'N/A':
                continue

            fp = f"{wid}|{url}|{field}|{val}"
            if fp in inserted_fps:
                duplicate_refs_skipped += 1
                continue

            cur.execute("""
                INSERT INTO official_source_references (
                    entity_type, entity_id, source_category, source_name,
                    source_url, source_domain, field_name, field_value,
                    confidence, retrieved_at, license_risk, copyright_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'whisky', wid, 'official_facts',
                f"{domain} Official Site",
                url, domain, field, val,
                float(ref.get('confidence', 0.92)),
                datetime.datetime.now().isoformat(),
                'low', 'low'
            ))
            inserted_refs += 1
            inserted_fps.add(fp)

        missing_region_after = count_missing(cur, 'region')
        missing_cask_after   = count_missing(cur, 'cask_type')

        if applied_rows != EXPECTED_UPDATED_ROWS:
            raise Exception(f"Row count mismatch: expected {EXPECTED_UPDATED_ROWS}, got {applied_rows}.")
        if applied_region != EXPECTED_REGION_UPDATES:
            raise Exception(f"Region update mismatch: expected {EXPECTED_REGION_UPDATES}, got {applied_region}.")
        if applied_cask != EXPECTED_CASK_UPDATES:
            raise Exception(f"Cask update mismatch: expected {EXPECTED_CASK_UPDATES}, got {applied_cask}.")
        if inserted_refs != EXPECTED_SOURCE_REFS:
            raise Exception(f"Source ref mismatch: expected {EXPECTED_SOURCE_REFS}, got {inserted_refs}.")

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
        applied_rows = 0
        applied_region = 0
        applied_cask = 0
        inserted_refs = 0
        missing_region_after = missing_region_before
        missing_cask_after   = missing_cask_before

    conn.close()

    if is_dry_run and os.path.exists(target_db):
        os.remove(target_db)

    hash_after = get_file_hash(DB_PATH)

    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    report = []
    report.append("# Low-Risk Official Facts Batch 4 Guarded Apply Report\n")
    report.append(f"- **Execution Mode:** {'APPLY' if not is_dry_run else 'DRY-RUN (Simulasyon)'}")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Execution Status:** {execution_status}")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_before == hash_after else 'NO (DB MUTATED)'}")
    if not is_dry_run and execution_status.startswith("Success"):
        report.append(f"- **Backup DB:** `{backup_path}`")

    report.append("\n## Apply Metrics")
    report.append(f"- Planned Update Rows: {len(update_candidates)}")
    report.append(f"- Applied Whisky Rows: {applied_rows}")
    report.append(f"- Applied Region Updates: {applied_region}")
    report.append(f"- Applied Cask Type Updates: {applied_cask}")
    report.append(f"- Skipped (Current Present / No-Overwrite): {skipped_present}")
    report.append(f"- Inserted Source References: {inserted_refs}")
    report.append(f"- Duplicate Source Refs Skipped: {duplicate_refs_skipped}")

    report.append("\n## Missing Fields Progression")
    report.append(f"- Missing Region: {missing_region_before} -> {missing_region_after} (Gain: +{missing_region_before - missing_region_after})")
    report.append(f"- Missing Cask Type: {missing_cask_before} -> {missing_cask_after} (Gain: +{missing_cask_before - missing_cask_after})")

    report.append(f"\n- **PRAGMA integrity_check:** {integrity_status}")

    if not is_dry_run and execution_status.startswith("Success"):
        report.append("\n## Confirm Phrase\n*(Already applied)*")
    else:
        report.append("\n## Required Confirm Phrase (for Real Apply)")
        report.append(f'`python scripts/apply/apply_low_risk_official_facts_v10.py --apply --confirm "{expected_phrase}"`')

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

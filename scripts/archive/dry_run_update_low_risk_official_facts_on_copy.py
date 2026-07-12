import sqlite3
import os
import shutil
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/low_risk_source_v3_official_facts_dry_run.db"
UPDATE_PLAN_CSV = "data/output/low_risk_source_v3_official_facts_update_plan.csv"
REPORT_MD_PATH = "output/reports/low_risk_source_v3_official_facts_dry_run_report.md"

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
    val_str = str(val).strip().lower()
    return val_str in ['', 'null', 'n/a', 'none', 'unknown']

def main():
    os.makedirs(os.path.dirname(DRY_RUN_DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(UPDATE_PLAN_CSV):
        print(f"Error: Update plan CSV not found at {UPDATE_PLAN_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    # Copy to output/tmp
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created Dry-Run DB Copy: {DRY_RUN_DB_PATH}")

    # Read update candidates
    candidates = []
    with open(UPDATE_PLAN_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append(row)

    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pre-calculated missing fields metrics on copy DB
    def count_missing():
        rows = cur.execute("SELECT age, abv, region, cask_type FROM whiskies").fetchall()
        missing = {'age': 0, 'abv': 0, 'region': 0, 'cask_type': 0}
        for r in rows:
            if is_empty(r['age']): missing['age'] += 1
            if is_empty(r['abv']): missing['abv'] += 1
            if is_empty(r['region']): missing['region'] += 1
            if is_empty(r['cask_type']): missing['cask_type'] += 1
        return missing

    missing_before = count_missing()

    updated_rows = 0
    updated_fields = {'age': 0, 'abv': 0, 'region': 0, 'cask_type': 0}

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            updates_str = c.get('updates_to_apply', '{}')
            updates = json.loads(updates_str)

            if updates:
                set_clauses = []
                params = []
                for field, val in updates.items():
                    set_clauses.append(f"{field} = ?")
                    params.append(val)
                    updated_fields[field] += 1
                
                params.append(wid)
                query = f"UPDATE whiskies SET {', '.join(set_clauses)} WHERE whisky_id = ?"
                cur.execute(query, params)
                updated_rows += 1

        missing_after = count_missing()
        
        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed after updates.")

        cur.execute("COMMIT;")
        print("Dry run database updates completed successfully.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during dry-run simulation: {e}")
        updated_rows = 0
        updated_fields = {'age': 0, 'abv': 0, 'region': 0, 'cask_type': 0}
        missing_after = missing_before
        integrity_status = "Failed (Rollback)"
        
    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)

    # Write Report
    report = []
    report.append("# Low-Risk Official Facts Dry-Run Simulation Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Copy Path:** `{DRY_RUN_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION DETECTED!)'}")

    report.append("\n## Dry-Run Metrics (on Copy DB)")
    report.append(f"- Updated Whisky Rows: {updated_rows}")
    report.append(f"- Updated Age Statements: {updated_fields['age']}")
    report.append(f"- Updated ABV Values: {updated_fields['abv']}")
    report.append(f"- Updated Regions: {updated_fields['region']}")
    report.append(f"- Updated Cask Types: {updated_fields['cask_type']}")

    report.append("\n## Missing Fields Progression (Before -> After)")
    report.append(f"- Missing Age: {missing_before['age']} -> {missing_after['age']} (Gain: +{missing_before['age'] - missing_after['age']})")
    report.append(f"- Missing ABV: {missing_before['abv']} -> {missing_after['abv']} (Gain: +{missing_before['abv'] - missing_after['abv']})")
    report.append(f"- Missing Region: {missing_before['region']} -> {missing_after['region']} (Gain: +{missing_before['region'] - missing_after['region']})")
    report.append(f"- Missing Cask Type: {missing_before['cask_type']} -> {missing_after['cask_type']} (Gain: +{missing_before['cask_type'] - missing_after['cask_type']})")
    
    report.append(f"\n- PRAGMA integrity_check: {integrity_status}")

    report.append("\n## Final GO/NO-GO")
    if updated_rows == 0 or not hash_unchanged or integrity_status.lower() != 'ok':
        report.append("**NO-GO** (Simulation validation failed or DB mutation detected).")
    else:
        report.append("**GO** (SQL dry-run updates successfully executed on backup copy).")

    report.append("\n## Next Phase Suggestion")
    report.append("- **AŞAMA LOW-RISK-SOURCE-V4 — Official Facts Guarded Apply**: Implement the actual apply script with safety parameters.")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

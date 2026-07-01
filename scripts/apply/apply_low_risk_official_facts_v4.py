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
REPORT_MD_PATH = "output/reports/low_risk_source_v4_official_facts_apply_report.md"

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
    parser = argparse.ArgumentParser(description="Guarded apply script for official cask facts.")
    parser.add_argument('--apply', action='store_true', help='Execute database mutations')
    parser.add_argument('--confirm', type=str, help='Verification confirmation phrase')
    args = parser.parse_args()

    is_dry_run = not args.apply
    confirm_phrase = args.confirm

    expected_phrase = "WRITE GO: apply low risk official cask facts to production.db"

    if not is_dry_run:
        if confirm_phrase != expected_phrase:
            print("Error: Invalid or missing confirmation phrase.")
            print(f"Use: --confirm \"{expected_phrase}\"")
            return

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(UPDATE_PLAN_CSV):
        print(f"Error: Update plan CSV not found at {UPDATE_PLAN_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"output/import/production_before_low_risk_official_facts_v4_{timestamp}.db"

    # Read plan
    candidates = []
    with open(UPDATE_PLAN_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append(row)

    # We connect to database (or copied database for dry run)
    target_db = DB_PATH
    if is_dry_run:
        # Dry-run copies to tmp first
        target_db = "output/tmp/low_risk_source_v4_dry_run_temp.db"
        os.makedirs(os.path.dirname(target_db), exist_ok=True)
        shutil.copy2(DB_PATH, target_db)
    else:
        # Make a real backup first
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup created at: {backup_path}")

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pre-calculated missing fields metrics on DB
    def count_missing_cask():
        return cur.execute("SELECT count(*) FROM whiskies WHERE cask_type IS NULL OR trim(cask_type) IN ('', 'NULL', 'N/A', 'none', 'unknown')").fetchone()[0]

    missing_before = count_missing_cask()

    applied_count = 0
    skipped_present = 0
    skipped_url = 0

    execution_status = "Success"
    integrity_status = "Skipped"

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            updates_str = c.get('updates_to_apply', '{}')
            updates = json.loads(updates_str)

            # Get current DB values
            w_db = cur.execute("SELECT cask_type FROM whiskies WHERE whisky_id = ?", (wid,)).fetchone()
            if not w_db:
                continue

            cask_update = updates.get('cask_type')
            if cask_update:
                if is_empty(w_db['cask_type']):
                    cur.execute("UPDATE whiskies SET cask_type = ? WHERE whisky_id = ?", (cask_update, wid))
                    applied_count += 1
                else:
                    skipped_present += 1

            if 'official_url' in c.get('missing_fields', ''):
                skipped_url += 1

        missing_after = count_missing_cask()

        # Validation checks
        expected_apply = len(candidates) # All candidates should be update_candidates for cask_type in this batch
        if applied_count != expected_apply:
            raise Exception(f"Expected to apply {expected_apply} updates, but actually applied {applied_count}.")

        # Integrity check
        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed.")

        cur.execute("COMMIT;")
        print(f"Transaction committed. Mode: {'APPLY' if not is_dry_run else 'DRY-RUN'}")

    except Exception as e:
        cur.execute("ROLLBACK;")
        execution_status = f"Failed (Rollback): {e}"
        print(f"Error during execution (Rolled Back): {e}")
        applied_count = 0
        missing_after = missing_before

    conn.close()

    if is_dry_run:
        # Clean up temp file
        if os.path.exists(target_db):
            os.remove(target_db)

    hash_after = get_file_hash(DB_PATH)

    # Write report
    report = []
    report.append("# Low-Risk Official Facts Guarded Apply Report\n")
    report.append(f"- **Execution Mode:** {'APPLY' if not is_dry_run else 'DRY-RUN (Simülasyon)'}")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_before == hash_after else 'NO (DB MUTATED)'}")
    if not is_dry_run and execution_status.startswith("Success"):
        report.append(f"- **Backup DB Created:** `{backup_path}`")

    report.append("\n## Apply Metrics")
    report.append(f"- Execution Status: {execution_status}")
    report.append(f"- Planned Cask Type Updates: {len(candidates)}")
    report.append(f"- Applied Cask Type Updates: {applied_count}")
    report.append(f"- Skipped (Current Cask Type Present): {skipped_present}")
    report.append(f"- Skipped (Schema Missing Official URL): {skipped_url}")

    report.append("\n## Missing Cask Type Fields Progression")
    report.append(f"- Missing Cask Types (Before): {missing_before}")
    report.append(f"- Missing Cask Types (After): {missing_after}")
    report.append(f"- Gain: +{missing_before - missing_after} fields filled")

    report.append(f"\n- **PRAGMA integrity_check:** {integrity_status}")

    report.append("\n## Final GO/NO-GO")
    if execution_status.startswith("Success") and integrity_status.lower() == 'ok':
        report.append("**GO** (Guarded apply execution verified successfully).")
    else:
        report.append("**NO-GO** (Apply validation failed or database integrity is corrupted).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

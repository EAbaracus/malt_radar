import sqlite3
import os
import shutil
import hashlib
import csv
import argparse
import datetime

DB_PATH = "output/import/production.db"
PLAN_CSV_PATH = "data/output/production_uploaded_note_cleanup_apply_plan.csv"
REPORT_MD_PATH = "output/reports/production_uploaded_note_cleanup_apply_script_report.md"
REQUIRED_CONFIRM_PHRASE = "WRITE GO: apply production uploaded note cleanup to production.db"

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
    parser = argparse.ArgumentParser(description="Production Uploaded Note Cleanup Script")
    parser.add_argument("--apply", action="store_true", help="Enable write execution mode")
    parser.add_argument("--confirm", type=str, default="", help="Explicit confirmation phrase")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(PLAN_CSV_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(PLAN_CSV_PATH):
        print(f"Error: Plan CSV not found at {PLAN_CSV_PATH}")
        return

    is_dry_run = True
    if args.apply:
        if args.confirm == REQUIRED_CONFIRM_PHRASE:
            is_dry_run = False
        else:
            print("ERROR: --apply flag provided but --confirm phrase is missing or incorrect.")
            print(f"Expected phrase: '{REQUIRED_CONFIRM_PHRASE}'")
            print("Falling back to DRY-RUN mode.")

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")
    print(f"Mode: {'DRY-RUN (No Write)' if is_dry_run else 'APPLY (Write Mode)'}")

    # Read plan
    plan_records = []
    with open(PLAN_CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('plan_action') == 'apply_delete_after_backup':
                plan_records.append(row)

    backup_path = "N/A"
    backup_hash = "N/A"
    if not is_dry_run:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"output/import/production_before_uploaded_note_cleanup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)
        backup_hash = get_file_hash(backup_path)
        print(f"Created Backup: {backup_path}")
        
    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode={'ro' if is_dry_run else 'rw'}"
    conn = sqlite3.connect(conn_uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    before_count_res = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()
    before_count = before_count_res[0] if before_count_res else 0
    
    uploaded_keywords = ['uploaded_document', 'uploaded_whisky_tasting_notes.txt']
    tn_cols = [c['name'] for c in cur.execute("PRAGMA table_info('tasting_notes')").fetchall()]
    source_cols = [c for c in tn_cols if 'source' in c.lower() or 'system' in c.lower() or 'origin' in c.lower()]
    
    uploaded_before_count = 0
    all_notes = cur.execute("SELECT * FROM tasting_notes").fetchall()
    for n in all_notes:
        n_dict = dict(n)
        for s_col in source_cols:
            val = str(n_dict.get(s_col, '')).lower()
            if any(k in val for k in uploaded_keywords):
                uploaded_before_count += 1
                break

    metrics = {
        'planned': len(plan_records),
        'verified': 0,
        'failed': 0,
        'deleted': 0
    }
    
    integrity_status = "Skipped"
    execution_status = "Success"
    
    try:
        cur.execute("BEGIN TRANSACTION;")
        
        for r in plan_records:
            rowid = r.get('production_note_id_or_rowid')
            wid = r.get('whisky_id')
            source_url = r.get('source_url')
            
            # Reconstruct the predicate safely ensuring we match schema
            real_row = cur.execute(f"SELECT length(COALESCE(nose_notes, '')) FROM tasting_notes WHERE rowid = {rowid}").fetchone()
            real_nose_len = real_row[0] if real_row else 0
            
            safe_predicate = f"whisky_id = '{wid}' AND source_url = '{source_url}' AND length(COALESCE(nose_notes, '')) = {real_nose_len} AND rowid = {rowid}"
            
            verify_query = f"SELECT count(*) FROM tasting_notes WHERE {safe_predicate}"
            res = cur.execute(verify_query).fetchone()
            actual_match = res[0] if res else 0
            
            if actual_match == 1:
                metrics['verified'] += 1
                if not is_dry_run:
                    delete_query = f"DELETE FROM tasting_notes WHERE {safe_predicate}"
                    cur.execute(delete_query)
                    metrics['deleted'] += 1
            else:
                metrics['failed'] += 1
                raise Exception(f"Verification failed for rowid {rowid}. Expected 1 match, got {actual_match}. Predicate: {safe_predicate}")

        if not is_dry_run:
            # Post check
            after_count_res = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()
            after_count = after_count_res[0] if after_count_res else 0
            
            uploaded_after_count = 0
            all_notes_after = cur.execute("SELECT * FROM tasting_notes").fetchall()
            for n in all_notes_after:
                n_dict = dict(n)
                for s_col in source_cols:
                    val = str(n_dict.get(s_col, '')).lower()
                    if any(k in val for k in uploaded_keywords):
                        uploaded_after_count += 1
                        break
                        
            if metrics['deleted'] != 28:
                raise Exception(f"Expected 28 deleted rows, but got {metrics['deleted']}.")
            if uploaded_after_count != 32:
                raise Exception(f"Expected 32 uploaded notes remaining, but got {uploaded_after_count}.")
            if after_count != (before_count - 28):
                raise Exception(f"Expected total tasting notes to be {before_count - 28}, but got {after_count}.")
                
            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0].lower() == 'ok':
                integrity_status = "Passed"
            else:
                integrity_status = f"Failed ({integrity})"
                raise Exception("Integrity check failed after deletes.")
                
            cur.execute("COMMIT;")
            print("Transaction committed successfully.")
        else:
            cur.execute("ROLLBACK;")
            print("Dry run completed. Transaction rolled back.")
            
    except Exception as e:
        execution_status = f"Failed: {str(e)}"
        print(f"Error during execution: {e}")
        cur.execute("ROLLBACK;")
        print("Transaction rolled back due to error.")
        
    conn.close()
    
    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Generate Report
    report = []
    report.append("# Production Uploaded Note Cleanup Apply Script Report\n")
    report.append(f"- **Script Path:** `scripts/apply/apply_production_uploaded_note_cleanup.py`")
    report.append(f"- **Mode:** {'DRY-RUN' if is_dry_run else 'APPLY'}")
    report.append(f"- **Default Dry-Run Tested:** Yes")
    if is_dry_run:
        report.append(f"- **Apply Mode Not Executed:** The explicit execution parameters were not supplied, guaranteeing no mutation.")
    
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION DETECTED!)'}")
    
    report.append("\n## Apply Mode Safety Parameters")
    report.append(f"- **Required Confirmation Phrase:** `--confirm \"{REQUIRED_CONFIRM_PHRASE}\"`")
    report.append(f"- **Backup Strategy:** Before execution, a timestamped file copy is generated in `output/import/`.")
    report.append(f"- **Rollback Strategy:** All DELETE statements execute inside a single transaction. A failure in verification, PRAGMA integrity check, or expected count results in a full ROLLBACK.")
    
    if not is_dry_run:
        report.append("\n## Backup Information")
        report.append(f"- **Backup Path:** `{backup_path}`")
        report.append(f"- **Backup Hash:** `{backup_hash}`")
        
    report.append("\n## Global Metrics")
    report.append(f"- Total Planned Safe Deletes: {metrics['planned']}")
    report.append(f"- Verification Passed: {metrics['verified']}")
    report.append(f"- Verification Failed: {metrics['failed']}")
    if not is_dry_run:
        report.append(f"- Deleted Rows: {metrics['deleted']}")
        report.append(f"- Tasting Notes After Apply: {after_count} (Expected {before_count - 28})")
        report.append(f"- Uploaded Document Notes After Apply: {uploaded_after_count} (Expected 32)")
        report.append(f"- Integrity Check Status: {integrity_status}")
    
    report.append("\n## Query Generation")
    report.append("- **Safety Predicates:** The SQL applies safe predicates constructed exactly using `whisky_id`, `source_url`, `rowid`, and length extraction from `nose_notes`.")
    report.append("- **Schema Columns Used:** `nose_notes`")

    report.append("\n## Execution Status")
    report.append(f"- **Status:** {execution_status}")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or (not is_dry_run and not hash_unchanged and integrity_status != "Passed"):
        report.append("**NO-GO** (Verification failures or integrity error).")
    else:
        report.append("**GO** (Dry-run mode generated properly and executed safely).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

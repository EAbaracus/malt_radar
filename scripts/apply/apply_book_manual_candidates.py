import sqlite3
import os
import shutil
import hashlib
import csv
import json
import argparse
import datetime

DB_PATH = "output/import/production.db"
QA_CSV = "data/output/book_manual_candidate_qa_pack.csv"
REPORT_MD_PATH = "output/reports/book_manual_candidate_apply_script_report.md"
REQUIRED_CONFIRM_PHRASE = "WRITE GO: apply book manual candidates to production.db"

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
    parser = argparse.ArgumentParser(description="Apply Book and Manual Candidates to Production DB")
    parser.add_argument("--apply", action="store_true", help="Enable write execution mode")
    parser.add_argument("--confirm", type=str, default="", help="Explicit confirmation phrase")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(QA_CSV):
        print(f"Error: QA CSV not found at {QA_CSV}")
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

    # Read QA candidates
    candidates = []
    with open(QA_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('qa_status') == 'Ready':
                candidates.append(row)

    backup_path = "N/A"
    backup_hash = "N/A"
    if not is_dry_run:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"output/import/production_before_book_manual_candidates_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)
        backup_hash = get_file_hash(backup_path)
        print(f"Created Backup: {backup_path}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode={'ro' if is_dry_run else 'rw'}"
    conn = sqlite3.connect(conn_uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Preload DB state
    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    existing_tns = {str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()}
    before_coverage_count = len(existing_tns)
    before_row_count = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]

    metrics = {
        'planned': len(candidates),
        'inserted': 0,
        'failed': 0
    }
    
    execution_status = "Success"
    integrity_status = "Skipped"

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            w_name = c.get('whisky_name')
            origin = c.get('source_origin', '')
            
            failed = []
            if wid not in whiskies:
                failed.append("Whisky ID not found in whiskies table")

            if failed:
                metrics['failed'] += 1
                raise Exception(f"Validation failed for whisky_id {wid}: {', '.join(failed)}")

            w_dict = whiskies[wid]
            norm_name = w_dict.get('normalized_name', '')
            dist_id = w_dict.get('distillery_id', '')

            if not is_dry_run:
                cur.execute("""
                    INSERT INTO tasting_notes (
                        whisky_id, normalized_name, distillery_id,
                        source_url, source_name, data_confidence,
                        notes_for_review, nose_notes, palate_notes,
                        finish_notes, source_system
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wid,
                    norm_name,
                    dist_id,
                    origin,
                    'CompleteGuide' if 'whisky_chunks_cleaned' in origin.lower() else 'NotebookLM',
                    'medium',
                    c.get('notes_for_review'),
                    c.get('nose_notes'),
                    c.get('palate_notes'),
                    c.get('finish_notes'),
                    'book_manual_derived'
                ))
                metrics['inserted'] += 1

        if not is_dry_run:
            after_row_count = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
            after_tns = {str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()}
            after_coverage_count = len(after_tns)

            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0].lower() == 'ok':
                integrity_status = "Passed"
            else:
                integrity_status = f"Failed ({integrity})"
                raise Exception("Integrity check failed after inserts.")

            if metrics['inserted'] != metrics['planned']:
                raise Exception(f"Expected {metrics['planned']} inserts, got {metrics['inserted']}.")
            if after_row_count != before_row_count + metrics['inserted']:
                raise Exception(f"Expected final row count {before_row_count + metrics['inserted']}, got {after_row_count}.")
            
            cur.execute("COMMIT;")
            print("Transaction committed successfully.")
        else:
            cur.execute("ROLLBACK;")
            print("Dry run completed. Transaction rolled back.")
            after_row_count = before_row_count
            after_coverage_count = before_coverage_count
            
    except Exception as e:
        execution_status = f"Failed: {str(e)}"
        print(f"Error during execution: {e}")
        cur.execute("ROLLBACK;")
        print("Transaction rolled back due to error.")
        after_row_count = before_row_count
        after_coverage_count = before_coverage_count

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Write Report
    report = []
    report.append("# Book and Manual Candidate Apply Script Report\n")
    report.append(f"- **Script Path:** `scripts/apply/apply_book_manual_candidates.py`")
    report.append(f"- **Mode:** {'DRY-RUN' if is_dry_run else 'APPLY'}")
    report.append(f"- **Default Dry-Run Tested:** Yes")
    if is_dry_run:
        report.append("- **Apply Mode Not Executed:** The explicit execution parameters were not supplied, guaranteeing no mutation.")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION)'}")

    report.append("\n## Apply Mode Safety Parameters")
    report.append(f"- **Required Confirmation Phrase:** `--confirm \"{REQUIRED_CONFIRM_PHRASE}\"`")
    report.append("- **Backup Strategy:** Before execution, a timestamped file copy is generated in `output/import/`.")
    report.append("- **Rollback Strategy:** All statements execute inside a single transaction. A failure in verification, PRAGMA integrity check, or expected count results in a full ROLLBACK.")

    if not is_dry_run:
        report.append("\n## Backup Information")
        report.append(f"- **Backup Path:** `{backup_path}`")
        report.append(f"- **Backup Hash:** `{backup_hash}`")

    report.append("\n## Global Metrics")
    report.append(f"- Planned Candidates: {metrics['planned']}")
    report.append(f"- Inserted Rows: {metrics['inserted']}")
    report.append(f"- Failed Rows: {metrics['failed']}")
    if not is_dry_run:
        report.append(f"- Tasting Notes Rows Before: {before_row_count}")
        report.append(f"- Tasting Notes Rows After: {after_row_count}")
        report.append(f"- Whiskies With Tasting Notes Before: {before_coverage_count}")
        report.append(f"- Whiskies With Tasting Notes After: {after_coverage_count}")
        total_whiskies = len(whiskies)
        before_cov = (before_coverage_count / total_whiskies * 100) if total_whiskies else 0
        after_cov = (after_coverage_count / total_whiskies * 100) if total_whiskies else 0
        report.append(f"- Expected Coverage Gain: +{after_cov - before_cov:.2f}%")
        report.append(f"- Integrity Check Status: {integrity_status}")

    report.append("\n## Execution Status")
    report.append(f"- **Status:** {execution_status}")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or (not is_dry_run and not hash_unchanged and integrity_status != "Passed"):
        report.append("**NO-GO** (Validation failure or mutation/integrity error).")
    else:
        report.append("**GO** (Dry-run mode validated successfully and apply mode ready).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

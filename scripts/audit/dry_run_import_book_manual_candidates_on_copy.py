import sqlite3
import os
import shutil
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/book_manual_candidate_import_dry_run.db"
QA_CSV = "data/output/book_manual_candidate_qa_pack.csv"
DRY_RUN_CSV = "data/output/book_manual_candidate_import_dry_run.csv"
REPORT_MD_PATH = "output/reports/book_manual_candidate_import_dry_run_report.md"

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
    os.makedirs(os.path.dirname(DRY_RUN_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(QA_CSV):
        print(f"Error: QA CSV not found at {QA_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    # Copy to output/tmp
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created Dry-Run DB Copy: {DRY_RUN_DB_PATH}")

    # Read QA candidates
    candidates = []
    with open(QA_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('qa_status') == 'Ready':
                candidates.append(row)

    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Preload DB state
    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    existing_tns = {str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()}
    before_tn_count = len(existing_tns)

    dry_run_results = []
    metrics = {
        'planned': len(candidates),
        'inserted': 0,
        'failed': 0
    }

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            w_name = c.get('whisky_name')
            dist_name = c.get('distillery_name')
            origin = c.get('source_origin', '')
            
            failed = []
            if wid not in whiskies:
                failed.append("Whisky ID not found in whiskies table")
                
            if failed:
                metrics['failed'] += 1
                dry_run_results.append({
                    'whisky_id': wid,
                    'whisky_name': w_name,
                    'distillery_name': dist_name,
                    'qa_status': 'Ready',
                    'import_action': 'Failed',
                    'reason': ", ".join(failed)
                })
                continue

            # Fetch details from whiskies table
            w_dict = whiskies[wid]
            norm_name = w_dict.get('normalized_name', '')
            dist_id = w_dict.get('distillery_id', '')

            # Insert into copy
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

            dry_run_results.append({
                'whisky_id': wid,
                'whisky_name': w_name,
                'distillery_name': dist_name,
                'qa_status': 'Ready',
                'import_action': 'Inserted',
                'reason': 'Success'
            })

        after_tn_count = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        # Verification checks on copy
        if metrics['inserted'] != metrics['planned']:
            raise Exception(f"Expected {metrics['planned']} inserts, got {metrics['inserted']}.")
        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed after inserts.")

        cur.execute("COMMIT;")
        print("Dry run database transaction completed successfully.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during dry-run simulation: {e}")
        metrics['inserted'] = 0
        after_tn_count = before_tn_count
        integrity_status = "Failed (Rollback)"
        
    conn.close()

    # Write CSV
    if dry_run_results:
        with open(DRY_RUN_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dry_run_results[0].keys())
            writer.writeheader()
            writer.writerows(dry_run_results)

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")
    print(f"Original DB Hash Unchanged: {hash_unchanged}")

    # Write Report
    report = []
    report.append("# Book and Manual Candidate Import Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Copy Path:** `{DRY_RUN_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION DETECTED!)'}")

    report.append("\n## Global Metrics (on Copy DB)")
    report.append(f"- Planned Candidates: {metrics['planned']}")
    report.append(f"- Inserted on Copy: {metrics['inserted']}")
    report.append(f"- Failed on Copy: {metrics['failed']}")
    report.append(f"- Tasting Notes Before: {before_tn_count}")
    report.append(f"- Tasting Notes After: {after_tn_count}")
    
    total_whiskies = len(whiskies)
    before_cov = (before_tn_count / total_whiskies * 100) if total_whiskies else 0
    after_cov = (after_tn_count / total_whiskies * 100) if total_whiskies else 0
    report.append(f"- Coverage Before: {before_cov:.2f}%")
    report.append(f"- Coverage After: {after_cov:.2f}%")
    report.append(f"- Expected Coverage Gain: +{after_cov - before_cov:.2f}%")
    report.append(f"- PRAGMA integrity_check: {integrity_status}")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or not hash_unchanged or integrity_status.lower() != 'ok' or metrics['inserted'] != metrics['planned']:
        report.append("**NO-GO** (Verification failures or DB mutation detected).")
    else:
        report.append("**GO** (SQL dry-run execution on backup copy successfully completed).")

    report.append("\n## Next Phase")
    report.append("- **AŞAMA BP4 — Book Manual Real Apply**")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

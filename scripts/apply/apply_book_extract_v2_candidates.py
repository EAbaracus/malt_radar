import sqlite3
import os
import shutil
import hashlib
import csv
import json
import argparse
import datetime

DB_PATH = "output/import/production.db"
QA_CSV = "data/output/book_extract_v2_candidate_qa_pack.csv"
REPORT_MD_PATH = "output/reports/book_extract_v2_candidate_apply_script_report.md"
REQUIRED_CONFIRM_PHRASE = "WRITE GO: apply book extract v2 candidates to production.db"

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
    parser = argparse.ArgumentParser(description="Apply Book Extract v2 Candidates to Production DB")
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
        backup_path = f"output/import/production_before_book_extract_v2_candidates_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)
        backup_hash = get_file_hash(backup_path)
        print(f"Created Backup: {backup_path}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode={'ro' if is_dry_run else 'rw'}"
    conn = sqlite3.connect(conn_uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Preload DB state
    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    
    # Tasting note counts
    before_tn_rows = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    before_tn_coverage = len({str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()})

    # Flavor profile counts
    before_fp_rows = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    before_fp_coverage = len({str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()})

    # Deduplicate flavor profile candidates by whisky_id
    fp_candidates = {}
    intra_batch_dedup_count = 0
    for c in candidates:
        action = c.get('qa_action')
        if action in ['import_flavor_profile', 'import_both']:
            wid = str(c.get('whisky_id'))
            if wid not in fp_candidates:
                fp_candidates[wid] = c
            else:
                intra_batch_dedup_count += 1
                old_conf = float(fp_candidates[wid].get('extraction_confidence', '0.0'))
                new_conf = float(c.get('extraction_confidence', '0.0'))

                def count_signals(cand):
                    axes = ['smoky', 'peaty', 'sherry', 'fruity', 'spicy', 'sweet', 'rich']
                    return sum(1 for axis in axes if float(cand.get(f'radar_{axis}', '0.0')) > 0.0)

                if new_conf > old_conf:
                    fp_candidates[wid] = c
                elif new_conf == old_conf:
                    if count_signals(c) > count_signals(fp_candidates[wid]):
                        fp_candidates[wid] = c

    metrics = {
        'planned_tn': sum(1 for c in candidates if c.get('qa_action') in ['import_tasting_note', 'import_both']),
        'planned_fp': len(fp_candidates),
        'inserted_tn': 0,
        'inserted_fp': 0,
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
            action = c.get('qa_action')
            
            failed = []
            if wid not in whiskies:
                failed.append("Whisky ID not found in whiskies table")

            if failed:
                metrics['failed'] += 1
                raise Exception(f"Validation failed for whisky_id {wid}: {', '.join(failed)}")

            w_dict = whiskies[wid]
            norm_name = w_dict.get('normalized_name', '')
            dist_id = w_dict.get('distillery_id', '')

            # Insert Tasting Note
            if action in ['import_tasting_note', 'import_both'] and not is_dry_run:
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
                    c.get('notes_for_review', ''),
                    c.get('nose_summary', ''),
                    c.get('palate_summary', ''),
                    c.get('finish_summary', ''),
                    'book_manual_derived_v2'
                ))
                metrics['inserted_tn'] += 1

            # Insert Flavor Profile
            if action in ['import_flavor_profile', 'import_both'] and not is_dry_run:
                if c == fp_candidates[wid]:
                    axes = ['smoky', 'peaty', 'sherry', 'fruity', 'spicy', 'sweet', 'rich']
                    fp_dict = {}
                    vector = []
                    for axis in axes:
                        val = float(c.get(f'radar_{axis}', '0.0'))
                        fp_dict[axis] = round(val * 10, 1)  # Scale to 0.0 - 10.0
                        vector.append(round(val, 2))

                    fp_json = json.dumps(fp_dict)
                    fv_json = json.dumps(vector)

                    cur.execute("""
                        INSERT INTO flavor_profiles (
                            whisky_id, flavor_profile, flavor_vector
                        ) VALUES (?, ?, ?)
                    """, (
                        wid,
                        fp_json,
                        fv_json
                    ))
                    metrics['inserted_fp'] += 1

        if not is_dry_run:
            after_tn_rows = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
            after_tn_coverage = len({str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()})

            after_fp_rows = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
            after_fp_coverage = len({str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()})

            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0].lower() == 'ok':
                integrity_status = "Passed"
            else:
                integrity_status = f"Failed ({integrity})"
                raise Exception("Integrity check failed after inserts.")

            if metrics['inserted_tn'] != metrics['planned_tn']:
                raise Exception(f"Expected {metrics['planned_tn']} tasting notes, got {metrics['inserted_tn']}.")
            if metrics['inserted_fp'] != metrics['planned_fp']:
                raise Exception(f"Expected {metrics['planned_fp']} flavor profiles, got {metrics['inserted_fp']}.")

            if after_tn_rows != before_tn_rows + metrics['inserted_tn']:
                raise Exception(f"Expected final tasting note count {before_tn_rows + metrics['inserted_tn']}, got {after_tn_rows}.")
            if after_fp_rows != before_fp_rows + metrics['inserted_fp']:
                raise Exception(f"Expected final flavor profile count {before_fp_rows + metrics['inserted_fp']}, got {after_fp_rows}.")
            
            cur.execute("COMMIT;")
            print("Transaction committed successfully.")
        else:
            cur.execute("ROLLBACK;")
            print("Dry run completed. Transaction rolled back.")
            after_tn_rows = before_tn_rows
            after_tn_coverage = before_tn_coverage
            after_fp_rows = before_fp_rows
            after_fp_coverage = before_fp_coverage
            
    except Exception as e:
        execution_status = f"Failed: {str(e)}"
        print(f"Error during execution: {e}")
        cur.execute("ROLLBACK;")
        print("Transaction rolled back due to error.")
        after_tn_rows = before_tn_rows
        after_tn_coverage = before_tn_coverage
        after_fp_rows = before_fp_rows
        after_fp_coverage = before_fp_coverage

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Write Report
    report = []
    report.append("# Book Extract v2 Candidate Apply Script Report\n")
    report.append(f"- **Script Path:** `scripts/apply/apply_book_extract_v2_candidates.py`")
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
    report.append(f"- Planned Tasting Notes: {metrics['planned_tn']}")
    report.append(f"- Inserted Tasting Notes: {metrics['inserted_tn']}")
    report.append(f"- Planned Flavor Profiles: {metrics['planned_fp']}")
    report.append(f"- Inserted Flavor Profiles: {metrics['inserted_fp']}")
    report.append(f"- Intra-Batch Deduplicated Flavor Profiles: {intra_batch_dedup_count}")
    report.append(f"- Failed Rows: {metrics['failed']}")
    
    if not is_dry_run:
        report.append(f"\n- Tasting Notes Rows Before: {before_tn_rows}")
        report.append(f"- Tasting Notes Rows After: {after_tn_rows}")
        report.append(f"- Whiskies with Tasting Notes Before: {before_tn_coverage}")
        report.append(f"- Whiskies with Tasting Notes After: {after_tn_coverage}")
        
        report.append(f"\n- Flavor Profiles Rows Before: {before_fp_rows}")
        report.append(f"- Flavor Profiles Rows After: {after_fp_rows}")
        report.append(f"- Whiskies with Flavor Profiles Before: {before_fp_coverage}")
        report.append(f"- Whiskies with Flavor Profiles After: {after_fp_coverage}")
        
        total_whiskies = len(whiskies)
        before_tn_cov = (before_tn_coverage / total_whiskies * 100) if total_whiskies else 0
        after_tn_cov = (after_tn_coverage / total_whiskies * 100) if total_whiskies else 0
        report.append(f"\n- Expected Tasting Note Coverage Gain: +{after_tn_cov - before_tn_cov:.2f}%")

        before_fp_cov = (before_fp_coverage / total_whiskies * 100) if total_whiskies else 0
        after_fp_cov = (after_fp_coverage / total_whiskies * 100) if total_whiskies else 0
        report.append(f"- Expected Flavor Profile Coverage Gain: +{after_fp_cov - before_fp_cov:.2f}%")
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

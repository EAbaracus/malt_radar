import sqlite3
import os
import shutil
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/book_extract_v2_candidate_import_dry_run.db"
QA_CSV = "data/output/book_extract_v2_candidate_qa_pack.csv"
DRY_RUN_CSV = "data/output/book_extract_v2_candidate_import_dry_run.csv"
REPORT_MD_PATH = "output/reports/book_extract_v2_candidate_import_dry_run_report.md"

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
    
    # Tasting note counts
    before_tn_rows = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    before_tn_coverage = len({str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()})

    # Flavor profile counts
    before_fp_rows = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    before_fp_coverage = len({str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()})

    dry_run_results = []
    metrics = {
        'planned_tn': 0,
        'planned_fp': 0,
        'inserted_tn': 0,
        'inserted_fp': 0,
        'failed': 0
    }

    # Count planned
    for c in candidates:
        action = c.get('qa_action')
        if action in ['import_tasting_note', 'import_both']:
            metrics['planned_tn'] += 1
        if action in ['import_flavor_profile', 'import_both']:
            metrics['planned_fp'] += 1

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            w_name = c.get('whisky_name')
            dist_name = c.get('distillery_name')
            origin = c.get('source_origin', '')
            action = c.get('qa_action')
            
            failed = []
            if wid not in whiskies:
                failed.append("Whisky ID not found in whiskies table")
                
            if failed:
                metrics['failed'] += 1
                dry_run_results.append({
                    'whisky_id': wid,
                    'whisky_name': w_name,
                    'distillery_name': dist_name,
                    'import_action': 'Failed',
                    'reason': ", ".join(failed)
                })
                continue

            w_dict = whiskies[wid]
            norm_name = w_dict.get('normalized_name', '')
            dist_id = w_dict.get('distillery_id', '')

            # Insert Tasting Note
            inserted_tn_flag = False
            if action in ['import_tasting_note', 'import_both']:
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
                inserted_tn_flag = True

            # Insert Flavor Profile
            inserted_fp_flag = False
            if action in ['import_flavor_profile', 'import_both']:
                # Compile JSON and Vector
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
                inserted_fp_flag = True

            dry_run_results.append({
                'whisky_id': wid,
                'whisky_name': w_name,
                'distillery_name': dist_name,
                'import_action': f"Inserted (TN:{inserted_tn_flag}, FP:{inserted_fp_flag})",
                'reason': 'Success'
            })

        after_tn_rows = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
        after_tn_coverage = len({str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()})

        after_fp_rows = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
        after_fp_coverage = len({str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()})

        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        # Verification checks on copy
        if metrics['inserted_tn'] != metrics['planned_tn']:
            raise Exception(f"Expected {metrics['planned_tn']} tasting notes, got {metrics['inserted_tn']}.")
        if metrics['inserted_fp'] != metrics['planned_fp']:
            raise Exception(f"Expected {metrics['planned_fp']} flavor profiles, got {metrics['inserted_fp']}.")
        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed after inserts.")

        cur.execute("COMMIT;")
        print("Dry run database transaction completed successfully.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during dry-run simulation: {e}")
        metrics['inserted_tn'] = 0
        metrics['inserted_fp'] = 0
        after_tn_rows = before_tn_rows
        after_tn_coverage = before_tn_coverage
        after_fp_rows = before_fp_rows
        after_fp_coverage = before_fp_coverage
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

    # Write Report
    report = []
    report.append("# Book Extract v2 Candidate Import Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Copy Path:** `{DRY_RUN_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION)'}")

    report.append("\n## Global Metrics (on Copy DB)")
    report.append(f"- Planned Tasting Notes: {metrics['planned_tn']}")
    report.append(f"- Inserted Tasting Notes: {metrics['inserted_tn']}")
    report.append(f"- Planned Flavor Profiles: {metrics['planned_fp']}")
    report.append(f"- Inserted Flavor Profiles: {metrics['inserted_fp']}")
    report.append(f"- Failed Rows: {metrics['failed']}")
    
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
    report.append(f"\n- Tasting Note Coverage Before: {before_tn_cov:.2f}%")
    report.append(f"- Tasting Note Coverage After: {after_tn_cov:.2f}%")
    report.append(f"- Tasting Note Coverage Gain: +{after_tn_cov - before_tn_cov:.2f}%")

    before_fp_cov = (before_fp_coverage / total_whiskies * 100) if total_whiskies else 0
    after_fp_cov = (after_fp_coverage / total_whiskies * 100) if total_whiskies else 0
    report.append(f"- Flavor Profile Coverage Before: {before_fp_cov:.2f}%")
    report.append(f"- Flavor Profile Coverage After: {after_fp_cov:.2f}%")
    report.append(f"- Flavor Profile Coverage Gain: +{after_fp_cov - before_fp_cov:.2f}%")

    report.append(f"\n- PRAGMA integrity_check: {integrity_status}")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or not hash_unchanged or integrity_status.lower() != 'ok':
        report.append("**NO-GO** (Simulation validation failed or original DB mutated).")
    else:
        report.append("**GO** (SQL dry-run execution on backup copy successfully completed).")

    report.append("\n## Next Phase")
    report.append("- **AŞAMA BOOK-APPLY-V2 — Real Apply**")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

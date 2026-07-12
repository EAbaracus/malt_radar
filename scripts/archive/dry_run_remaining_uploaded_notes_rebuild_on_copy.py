import sqlite3
import os
import shutil
import hashlib
import csv

DB_PATH = "output/import/production.db"
TMP_DB_PATH = "output/tmp/remaining_uploaded_notes_rebuild_dry_run.db"
PLAN_CSV_PATH = "data/output/remaining_uploaded_notes_rebuild_plan.csv"
OUTPUT_CSV_PATH = "data/output/remaining_uploaded_notes_rebuild_dry_run.csv"
REPORT_MD_PATH = "output/reports/remaining_uploaded_notes_rebuild_dry_run_report.md"

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
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(TMP_DB_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(PLAN_CSV_PATH):
        print(f"Error: Plan CSV not found at {PLAN_CSV_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    # Read plan
    plan_records = []
    with open(PLAN_CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('recommended_action') == 'replace_with_staging_after_backup' and row.get('apply_candidate') == 'yes':
                plan_records.append(row)

    # Create Temp DB and Execute Dry Run
    if os.path.exists(TMP_DB_PATH):
        os.remove(TMP_DB_PATH)
    shutil.copy2(DB_PATH, TMP_DB_PATH)
    
    tmp_conn = sqlite3.connect(TMP_DB_PATH)
    tmp_conn.row_factory = sqlite3.Row
    tmp_cur = tmp_conn.cursor()
    
    before_count_res = tmp_cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()
    before_count = before_count_res[0] if before_count_res else 0
    
    uploaded_keywords = ['uploaded_document', 'uploaded_whisky_tasting_notes.txt']
    tn_cols = [c['name'] for c in tmp_cur.execute("PRAGMA table_info('tasting_notes')").fetchall()]
    source_cols = [c for c in tn_cols if 'source' in c.lower() or 'system' in c.lower() or 'origin' in c.lower()]
    
    uploaded_before_count = 0
    source_distribution_before = {}
    all_notes = tmp_cur.execute("SELECT * FROM tasting_notes").fetchall()
    for n in all_notes:
        n_dict = dict(n)
        sys_val = str(n_dict.get('source_system', ''))
        source_distribution_before[sys_val] = source_distribution_before.get(sys_val, 0) + 1
        
        for s_col in source_cols:
            val = str(n_dict.get(s_col, '')).lower()
            if any(k in val for k in uploaded_keywords):
                uploaded_before_count += 1
                break

    output_rows = []
    
    metrics = {
        'planned': len(plan_records),
        'verified': 0,
        'failed': 0,
        'replaced': 0
    }
    
    tmp_cur.execute("BEGIN TRANSACTION;")

    for r in plan_records:
        rowid = r.get('production_note_id_or_rowid')
        staging_id = r.get('staging_candidate_id')
        wid = r.get('whisky_id')
        
        verification_status = ""
        # Verification
        prod_row = tmp_cur.execute(f"SELECT * FROM tasting_notes WHERE rowid = {rowid}").fetchone()
        
        # Find staging candidate by matching whisky_id and fingerprint from plan
        staging_row = None
        s_fp = r.get('staging_content_fingerprint')
        for s_cand in tmp_cur.execute(f"SELECT * FROM staging_tasting_notes WHERE whisky_id = ?", (wid,)).fetchall():
            c_dict = dict(s_cand)
            fp_str = f"{str(c_dict.get('nose', ''))}|{str(c_dict.get('palate', ''))}|{str(c_dict.get('finish', ''))}|{str(c_dict.get('body', ''))}"
            if hashlib.md5(fp_str.encode('utf-8')).hexdigest() == s_fp:
                staging_row = c_dict
                break
        
        failed = []
        if not prod_row:
            failed.append("Production note not found")
        elif str(prod_row['whisky_id']) != wid:
            failed.append("Whisky ID mismatch in prod")
            
        if not staging_row:
            failed.append("Staging candidate not found")
        elif str(staging_row['whisky_id']) != wid:
            failed.append("Whisky ID mismatch in staging")
            
        if staging_row and not staging_row['source_url']:
            failed.append("Staging candidate has empty source_url")
            
        if failed:
            metrics['failed'] += 1
            verification_status = f"Failed: {', '.join(failed)}"
            action_status = "Blocked"
        else:
            verification_status = "Passed"
            metrics['verified'] += 1
            
            # Execute Replace (DELETE + INSERT)
            try:
                # Get fields from prod to keep
                p_dict = dict(prod_row)
                norm_name = p_dict.get('normalized_name', '')
                dist_id = p_dict.get('distillery_id', '')
                
                # Get fields from staging to use
                s_dict = dict(staging_row) if staging_row else {}
                s_url = s_dict.get('source_url', '')
                s_name = s_dict.get('source_name', '')
                s_sys = s_dict.get('source_system', s_dict.get('flavor_source', ''))
                nose = s_dict.get('nose', '')
                palate = s_dict.get('palate', '')
                finish = s_dict.get('finish', '')
                body = s_dict.get('body', '')
                
                tmp_cur.execute(f"DELETE FROM tasting_notes WHERE rowid = {rowid}")
                
                insert_query = """
                    INSERT INTO tasting_notes (
                        whisky_id, normalized_name, distillery_id, 
                        source_url, source_name, source_system,
                        nose_notes, palate_notes, finish_notes, notes_for_review
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                tmp_cur.execute(insert_query, (wid, norm_name, dist_id, s_url, s_name, s_sys, nose, palate, finish, body))
                
                metrics['replaced'] += 1
                action_status = "Replaced (DELETE+INSERT)"
            except Exception as e:
                metrics['failed'] += 1
                verification_status = f"Execution Error: {e}"
                action_status = "Blocked"
                
        output_rows.append({
            "dry_run_rank": 0,
            "whisky_id": wid,
            "production_note_rowid": rowid,
            "staging_candidate_id": staging_id,
            "verification_status": verification_status,
            "action_status": action_status,
            "reviewer_decision": "",
            "reviewer_notes": ""
        })

    integrity_res = tmp_cur.execute("PRAGMA integrity_check").fetchone()
    integrity_status = integrity_res[0] if integrity_res else "Failed"
    
    tmp_conn.commit()
    
    # Post-execution metrics
    after_count_res = tmp_cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()
    after_count = after_count_res[0] if after_count_res else 0
    
    uploaded_after_count = 0
    source_distribution_after = {}
    all_notes_after = tmp_cur.execute("SELECT * FROM tasting_notes").fetchall()
    for n in all_notes_after:
        n_dict = dict(n)
        sys_val = str(n_dict.get('source_system', ''))
        source_distribution_after[sys_val] = source_distribution_after.get(sys_val, 0) + 1
        
        for s_col in source_cols:
            val = str(n_dict.get(s_col, '')).lower()
            if any(k in val for k in uploaded_keywords):
                uploaded_after_count += 1
                break

    tmp_conn.close()

    # Finalize Output
    for idx, row in enumerate(output_rows):
        row['dry_run_rank'] = idx + 1
        
    if output_rows:
        keys = output_rows[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(output_rows)

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Generate Report
    report = []
    report.append("# Remaining Uploaded Notes Rebuild Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Copy Path:** `{TMP_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original DB Changed:** {'NO' if hash_unchanged else 'YES (MUTATION DETECTED!)'}")
    
    report.append("\n## Global Metrics (on Copy)")
    report.append(f"- **Planned Replaces:** {metrics['planned']}")
    report.append(f"- **Verification Passed:** {metrics['verified']}")
    report.append(f"- **Verification Failed:** {metrics['failed']}")
    report.append(f"- **Replaced on Copy:** {metrics['replaced']}")
    report.append(f"- **Tasting Notes Before:** {before_count}")
    report.append(f"- **Tasting Notes After:** {after_count}")
    report.append(f"- **Uploaded Document Notes Before:** {uploaded_before_count}")
    report.append(f"- **Uploaded Document Notes After:** {uploaded_after_count}")
    report.append(f"- **PRAGMA integrity_check:** {integrity_status}")

    report.append("\n## Source System Distribution Changes")
    report.append("### Before")
    for k, v in source_distribution_before.items():
        report.append(f"- {k}: {v}")
    report.append("### After")
    for k, v in source_distribution_after.items():
        report.append(f"- {k}: {v}")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or not hash_unchanged or integrity_status.lower() != "ok":
        report.append("**NO-GO** (Verification failures or DB mutation detected).")
    else:
        report.append("**GO** (SQL dry-run execution on backup copy successfully completed).")
        report.append("\n## Recommended Next Stage")
        report.append("**AŞAMA U — Remaining Uploaded Notes Rebuild Real Apply**: Generate the final execution script that will perform the actual backup of production.db and apply the verified rebuild replacements to the live database.")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

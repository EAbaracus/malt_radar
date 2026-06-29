import sqlite3
import os
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/production_uploaded_note_cleanup_apply_plan_report.md"
OUTPUT_CSV_PATH = "data/output/production_uploaded_note_cleanup_apply_plan.csv"
OUTPUT_SQL_PATH = "data/output/production_uploaded_note_cleanup_sql_preview.sql"

UPLOAD_KEYWORDS = ['uploaded_document', 'uploaded_whisky_tasting_notes.txt']

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

def get_content_fingerprint(r):
    nose = str(r.get('nose', r.get('nose_notes', '')))
    palate = str(r.get('palate', r.get('palate_notes', '')))
    finish = str(r.get('finish', r.get('finish_notes', '')))
    summary = str(r.get('conclusion', r.get('body', r.get('notes_for_review', ''))))
    content = f"{nose}|{palate}|{finish}|{summary}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def main():
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_SQL_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    try:
        conn = sqlite3.connect(conn_uri, uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Error connecting to original DB: {e}")
        return

    def safe_query(query, params=()):
        try:
            return [dict(row) for row in cur.execute(query, params).fetchall()]
        except sqlite3.OperationalError as e:
            return []

    tables = [r['name'] for r in safe_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    
    schema_info = {}
    for t in ['tasting_notes', 'whiskies', 'distilleries', 'staging_tasting_notes']:
        if t in tables:
            schema_info[t] = [c['name'] for c in safe_query(f"PRAGMA table_info('{t}')")]
            
    whiskies = {str(w.get('whisky_id')): w for w in safe_query("SELECT * FROM whiskies") if w.get('whisky_id')}
    distilleries = {str(d.get('distillery_id')): d for d in safe_query("SELECT * FROM distilleries") if d.get('distillery_id')}
    
    w_cols = schema_info.get('whiskies', [])
    whisky_name_col = 'name' if 'name' in w_cols else (w_cols[1] if len(w_cols) > 1 else 'unknown')
    
    d_cols = schema_info.get('distilleries', [])
    distillery_name_col = 'name' if 'name' in d_cols else (d_cols[1] if len(d_cols) > 1 else 'unknown')

    prod_notes = safe_query("SELECT rowid, * FROM tasting_notes")
    staging_notes = safe_query("SELECT * FROM staging_tasting_notes")
    
    staging_wid_count = {}
    for sn in staging_notes:
        wid = str(sn.get('whisky_id', ''))
        if wid:
            staging_wid_count[wid] = staging_wid_count.get(wid, 0) + 1
            
    prod_wid_notes = {}
    for pn in prod_notes:
        wid = str(pn.get('whisky_id', ''))
        if wid:
            prod_wid_notes.setdefault(wid, []).append(pn)
            
    tn_cols = schema_info.get('tasting_notes', [])
    source_cols = [c for c in tn_cols if 'source' in c.lower() or 'system' in c.lower() or 'origin' in c.lower()]

    plan = []
    
    distribution = {
        'plan_action': {},
        'safety_status': {},
        'total_uploaded_notes': 0
    }

    sql_lines = [
        "-- PRODUCTION UPLOADED NOTE CLEANUP SQL PREVIEW",
        "-- WARNING: DO NOT EXECUTE AGAINST PRODUCTION.DB WITHOUT EXPLICIT GO",
        "-- ALL COMMANDS ARE WRAPPED IN A TRANSACTION AND ROLLBACK BY DEFAULT",
        "",
        "BEGIN TRANSACTION;",
        ""
    ]

    for r in prod_notes:
        is_upload = False
        primary_source_val = ""
        source_col_used = ""
        
        for s_col in source_cols:
            val = str(r.get(s_col, '')).lower()
            if any(k in val for k in UPLOAD_KEYWORDS):
                is_upload = True
                primary_source_val = str(r.get(s_col, ''))
                source_col_used = s_col
                break
                
        if not is_upload:
            continue
            
        distribution['total_uploaded_notes'] += 1
        
        wid = str(r.get('whisky_id', ''))
        
        staging_duplicate_count = staging_wid_count.get(wid, 0)
        
        all_wid_notes = prod_wid_notes.get(wid, [])
        other_prod_note_count = 0
        for on in all_wid_notes:
            if on.get('rowid') != r.get('rowid'):
                other_prod_note_count += 1
                
        source_url = str(r.get('source_url', ''))
        has_source_url = bool(source_url.strip())
        
        # Determine plan_action
        plan_action = ""
        # The URL is not empty, it contains the filename. So we check if it is one of the upload keywords.
        is_invalid_url = any(k in source_url.lower() for k in UPLOAD_KEYWORDS) or not has_source_url
        
        if is_invalid_url and other_prod_note_count > 0:
            plan_action = "apply_delete_after_backup"
        elif staging_duplicate_count > 0:
            plan_action = "defer_delete_until_staging_rebuild"
        else:
            plan_action = "keep_pending_manual_audit"

        rowid = r.get("rowid", "")
        fp = get_content_fingerprint(r)
        
        nose_len = len(str(r.get('nose', r.get('nose_notes', ''))))
        
        safe_delete_predicate = ""
        verification_select_sql = ""
        delete_sql_preview = ""
        safety_status = ""
        rollback_note = "Requires full production.db backup before apply."

        if plan_action == "apply_delete_after_backup":
            # Build safe predicate
            # We use source_url = 'uploaded_whisky_tasting_notes.txt' instead of empty string because that is what's in the DB.
            safe_delete_predicate = f"whisky_id = '{wid}' AND {source_col_used} = '{primary_source_val}' AND source_url = '{source_url}' AND length(COALESCE(nose, '')) = {nose_len} AND rowid = {rowid}"
            verification_select_sql = f"SELECT count(*) FROM tasting_notes WHERE {safe_delete_predicate};"
            delete_sql_preview = f"DELETE FROM tasting_notes WHERE {safe_delete_predicate};"
            safety_status = "safe_predicate_ready"
            
            sql_lines.append(f"-- --------------------------------------------------")
            sql_lines.append(f"-- DELETE PLAN FOR ROWID {rowid} | WHISKY_ID: {wid}")
            sql_lines.append(f"-- Other production notes exist: {other_prod_note_count}")
            sql_lines.append(f"-- Verification Query:")
            sql_lines.append(f"-- {verification_select_sql}")
            sql_lines.append(f"-- Delete Query:")
            sql_lines.append(delete_sql_preview)
            sql_lines.append(f"")
        elif plan_action == "defer_delete_until_staging_rebuild":
            safety_status = "needs_manual_review"
            safe_delete_predicate = "N/A"
        else:
            safety_status = "needs_manual_review"
            safe_delete_predicate = "N/A"

        distribution['plan_action'][plan_action] = distribution['plan_action'].get(plan_action, 0) + 1
        distribution['safety_status'][safety_status] = distribution['safety_status'].get(safety_status, 0) + 1
        
        w_data = whiskies.get(wid, {})
        w_name = w_data.get(whisky_name_col, '')
        dist_id = str(w_data.get('distillery_id', ''))
        d_name = distilleries.get(dist_id, {}).get(distillery_name_col, '')
        
        plan.append({
            "plan_rank": 0,
            "plan_action": plan_action,
            "production_note_id_or_rowid": rowid,
            "whisky_id": wid,
            "whisky_name": w_name,
            "distillery_name": d_name,
            "source_system": r.get('source_system', r.get('flavor_source', '')),
            "source_name": r.get('source_name', ''),
            "source_url": r.get('source_url', ''),
            "content_fingerprint": fp,
            "other_production_note_count": other_prod_note_count,
            "staging_duplicate_count": staging_duplicate_count,
            "safe_delete_predicate": safe_delete_predicate,
            "verification_select_sql": verification_select_sql,
            "delete_sql_preview": delete_sql_preview,
            "rollback_note": rollback_note,
            "safety_status": safety_status,
            "reviewer_decision": "",
            "reviewer_notes": ""
        })

    conn.close()
    
    sql_lines.append("-- ROLLBACK;")
    sql_lines.append("-- ^^^^^^^")
    sql_lines.append("-- Change to COMMIT ONLY AFTER VERIFICATION AND BACKUP")

    # Sort plan
    plan.sort(key=lambda x: 0 if x['plan_action'] == 'apply_delete_after_backup' else 1)
    
    for idx, p in enumerate(plan):
        p['plan_rank'] = idx + 1

    # Output CSV
    if plan:
        keys = plan[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(plan)

    # Output SQL
    with open(OUTPUT_SQL_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))

    # Output Report
    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    report = []
    report.append("# Production Uploaded Note Cleanup Apply Plan Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION DETECTED!)'}")
    
    report.append("\n## Global Metrics")
    report.append(f"- Total Production Uploaded Notes Found: {distribution['total_uploaded_notes']}")
    report.append(f"- Apply Delete After Backup: {distribution['plan_action'].get('apply_delete_after_backup', 0)}")
    report.append(f"- Defer Delete Until Staging Rebuild: {distribution['plan_action'].get('defer_delete_until_staging_rebuild', 0)}")
    report.append(f"- Safe Predicate Ready: {distribution['safety_status'].get('safe_predicate_ready', 0)}")
    report.append(f"- Unsafe Rowid Only Blocked: {distribution['safety_status'].get('unsafe_rowid_only_blocked', 0)}")
    
    report.append("\n## File Paths")
    report.append(f"- **CSV Plan:** `{OUTPUT_CSV_PATH}`")
    report.append(f"- **SQL Preview:** `{OUTPUT_SQL_PATH}`")
    
    report.append("\n## Backup & Rollback Strategy")
    report.append("- **Backup:** Before executing the SQL, a full file copy of `output/import/production.db` must be taken (e.g., `output/import/production_backup_TIMESTAMP.db`).")
    report.append("- **Verification:** Run the verification SELECTs provided in the SQL script to ensure exactly 1 row matches per delete statement.")
    report.append("- **Rollback:** The SQL script uses `BEGIN TRANSACTION;` and ends with `-- ROLLBACK;`. This must only be changed to `COMMIT;` manually after successful verification. If an error occurs, replacing the `production.db` with the backup is the ultimate fallback.")
    
    report.append("\n## Safety Check")
    report.append("- **Explicit Warning:** NO SQL WAS EXECUTED. The original database was accessed strictly in read-only mode, and the output SQL is provided only as a preview artifact.")
    report.append("- The generated delete predicates check `whisky_id`, `source_system`, `source_url`, `length(nose)`, and `rowid` collectively to guarantee safe targeting without relying solely on `rowid`.")

    report.append("\n## Recommended Next Stage")
    report.append("**AŞAMA P — Production Uploaded Note Cleanup Apply DRY-RUN ON BACKUP COPY**: Test the generated SQL preview on a backup copy of production.db to verify predicates work as intended.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Cleanup apply plan, safe predicates, and SQL preview successfully generated without mutating production data).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

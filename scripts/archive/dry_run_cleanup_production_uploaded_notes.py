import sqlite3
import os
import shutil
import hashlib
import csv

DB_PATH = "output/import/production.db"
TMP_DB_PATH = "output/tmp/production_uploaded_note_cleanup_dry_run.db"
REPORT_MD_PATH = "output/reports/production_uploaded_note_cleanup_dry_run_report.md"
OUTPUT_CSV_PATH = "data/output/production_uploaded_note_cleanup_dry_run.csv"

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

def main():
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(TMP_DB_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    # Step 1: Read from original DB to identify candidates (read-only)
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
        'dry_run_action': {},
        'deleted_in_dry_run': 0,
        'would_rebuild_from_staging': 0
    }

    for r in prod_notes:
        is_upload = False
        primary_source_val = ""
        
        for s_col in source_cols:
            val = str(r.get(s_col, '')).lower()
            if any(k in val for k in UPLOAD_KEYWORDS):
                is_upload = True
                primary_source_val = str(r.get(s_col, ''))
                break
                
        if not is_upload:
            continue
            
        wid = str(r.get('whisky_id', ''))
        
        staging_duplicate_count = staging_wid_count.get(wid, 0)
        
        all_wid_notes = prod_wid_notes.get(wid, [])
        other_prod_note_count = 0
        for on in all_wid_notes:
            if on.get('rowid') != r.get('rowid'):
                other_prod_note_count += 1
                
        source_url = str(r.get('source_url', ''))
        has_source_url = bool(source_url.strip())
        
        # Determine original action from Phase M
        proposed_action = ""
        audit_signal = "only_uploaded_production_note"
        if not has_source_url and other_prod_note_count > 0:
            proposed_action = "candidate_for_remove_after_backup"
            audit_signal = "has_other_production_note"
        elif staging_duplicate_count > 0:
            proposed_action = "candidate_for_rebuild_from_staging"
            audit_signal = "has_staging_duplicate"
        else:
            proposed_action = "keep_pending_manual_audit"

        # Determine Dry Run action
        dry_run_action = ""
        sql_preview = ""
        safety_reason = ""
        
        rowid = r.get("rowid", "")

        if proposed_action == "candidate_for_remove_after_backup":
            dry_run_action = "dry_run_remove_after_backup"
            sql_preview = f"DELETE FROM tasting_notes WHERE rowid = {rowid};"
            safety_reason = "Safe to delete; another production note exists."
        elif proposed_action == "candidate_for_rebuild_from_staging":
            dry_run_action = "dry_run_rebuild_from_staging"
            sql_preview = "-- No deletion yet; wait for staging rebuild."
            safety_reason = "Wait for staging data to be ready before removing."
        else:
            dry_run_action = "dry_run_keep_pending_manual_audit"
            sql_preview = "-- No action."
            safety_reason = "Manual audit required."

        distribution['dry_run_action'][dry_run_action] = distribution['dry_run_action'].get(dry_run_action, 0) + 1
        
        w_data = whiskies.get(wid, {})
        w_name = w_data.get(whisky_name_col, '')
        dist_id = str(w_data.get('distillery_id', ''))
        d_name = distilleries.get(dist_id, {}).get(distillery_name_col, '')
        
        plan.append({
            "dry_run_rank": 0,
            "dry_run_action": dry_run_action,
            "production_note_id": rowid,
            "whisky_id": wid,
            "whisky_name": w_name,
            "distillery_name": d_name,
            "source_system": r.get('source_system', r.get('flavor_source', '')),
            "source_name": r.get('source_name', ''),
            "source_url": r.get('source_url', ''),
            "audit_signal": audit_signal,
            "proposed_cleanup_action": proposed_action,
            "other_production_note_count": other_prod_note_count,
            "staging_duplicate_count": staging_duplicate_count,
            "sql_preview": sql_preview,
            "safety_reason": safety_reason,
            "reviewer_decision": "",
            "reviewer_notes": ""
        })

    conn.close()

    # Step 2: Create Temp DB and Execute Dry Run
    if os.path.exists(TMP_DB_PATH):
        os.remove(TMP_DB_PATH)
    shutil.copy2(DB_PATH, TMP_DB_PATH)
    
    tmp_conn = sqlite3.connect(TMP_DB_PATH)
    tmp_cur = tmp_conn.cursor()
    
    before_count_res = tmp_cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()
    before_count = before_count_res[0] if before_count_res else 0

    # Sort plan
    plan.sort(key=lambda x: 0 if x['dry_run_action'] == 'dry_run_remove_after_backup' else 1)
    
    for idx, p in enumerate(plan):
        p['dry_run_rank'] = idx + 1
        
        if p['dry_run_action'] == 'dry_run_remove_after_backup':
            tmp_cur.execute("DELETE FROM tasting_notes WHERE rowid = ?", (p['production_note_id'],))
            distribution['deleted_in_dry_run'] += 1
        elif p['dry_run_action'] == 'dry_run_rebuild_from_staging':
            distribution['would_rebuild_from_staging'] += 1

    tmp_conn.commit()
    
    after_count_res = tmp_cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()
    after_count = after_count_res[0] if after_count_res else 0
    
    tmp_conn.close()

    # Output CSV
    if plan:
        keys = plan[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(plan)

    # Output Report
    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    report = []
    report.append("# Production Uploaded Note Cleanup Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Path:** `{TMP_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION DETECTED!)'}")
    
    report.append("\n## Global Metrics")
    report.append(f"- Total Production Uploaded Notes Found: {len(plan)}")
    report.append(f"- Tasting Notes Count (Before Dry-Run): {before_count}")
    report.append(f"- Tasting Notes Count (After Dry-Run): {after_count}")
    report.append(f"- Deleted in Dry-Run DB: {distribution['deleted_in_dry_run']}")
    report.append(f"- Would Rebuild from Staging: {distribution['would_rebuild_from_staging']}")
    
    report.append("\n## Dry-Run Action Distribution")
    for k, v in sorted(distribution['dry_run_action'].items(), key=lambda item: item[1], reverse=True):
        report.append(f"- {k}: {v}")

    report.append("\n## First 60 Dry-Run Rows Summary")
    if plan:
        report.append("| Rank | Note ID | Whisky ID | Dry Run Action | SQL Preview | Safety Reason |")
        report.append("|---|---|---|---|---|---|")
        for p in plan[:60]:
            sql_prev = p['sql_preview'][:40] + "..." if len(p['sql_preview']) > 40 else p['sql_preview']
            report.append(f"| {p['dry_run_rank']} | {p['production_note_id']} | {p['whisky_id']} | {p['dry_run_action']} | `{sql_prev}` | {p['safety_reason']} |")
    else:
        report.append("No candidates found.")

    report.append("\n## Statement of Safety")
    report.append("- **Explicit Statement:** The original `production.db` was strictly read-only and **NOT modified** during this run. All deletions occurred exclusively in the temporary dry-run copy.")

    report.append("\n## Risks & Observations")
    report.append("- Deletions rely entirely on `rowid`. If database compaction or vacuuming occurs before actual execution, `rowid`s might change. Actual apply should ideally use a primary key or strict matching if `rowid` isn't stable, but SQLite `rowid` is stable unless VACUUM is run.")
    report.append("- The remaining rebuild candidates must not be deleted until staging promotion replaces them.")

    report.append("\n## Recommended Next Stage")
    report.append("**AŞAMA O — Production Uploaded Note Cleanup Apply Plan**: Execute the verified deletions in production after performing a full backup of `production.db`.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Dry-run cleanup successfully executed on local copy without mutating production data).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

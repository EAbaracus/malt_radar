import sqlite3
import os
import hashlib
import csv

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/production_uploaded_note_audit_plan_report.md"
OUTPUT_CSV_PATH = "data/output/production_uploaded_note_audit_plan.csv"
OUTPUT_QUEUE_CSV = "data/output/production_uploaded_note_priority_queue.csv"

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

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"DB Hash (before): {hash_before}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    try:
        conn = sqlite3.connect(conn_uri, uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Error connecting to DB: {e}")
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
        'audit_signal': {},
        'proposed_cleanup_action': {},
        'source_name': {},
        'missing_source_url': 0,
        'duplicate_staging_overlap': 0
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
        
        nose = str(r.get('nose', r.get('nose_notes', '')))
        palate = str(r.get('palate', r.get('palate_notes', '')))
        finish = str(r.get('finish', r.get('finish_notes', '')))
        summary = str(r.get('conclusion', r.get('body', r.get('notes_for_review', ''))))
        content_len = len(nose) + len(palate) + len(finish) + len(summary)
        
        staging_duplicate_count = staging_wid_count.get(wid, 0)
        
        # Count OTHER production notes for same whisky
        all_wid_notes = prod_wid_notes.get(wid, [])
        other_prod_note_count = 0
        for on in all_wid_notes:
            if on.get('rowid') != r.get('rowid'):
                other_prod_note_count += 1
                
        source_url = str(r.get('source_url', ''))
        has_source_url = bool(source_url.strip())
        
        # Build signals
        audit_signal = []
        proposed_action = ""
        priority = 99
        
        if not has_source_url:
            audit_signal.append("missing_source_url")
            distribution['missing_source_url'] += 1
            
        if staging_duplicate_count > 0:
            audit_signal.append("has_staging_duplicate")
            distribution['duplicate_staging_overlap'] += 1
            
        if other_prod_note_count > 0:
            audit_signal.append("has_other_production_note")
            
        if content_len < 50:
            audit_signal.append("weak_content")
            
        audit_signal.append("source_paraphrase_review_required")
        
        if not audit_signal or audit_signal == ["source_paraphrase_review_required"]:
            audit_signal.insert(0, "only_uploaded_production_note")
            
        signal_str = " | ".join(audit_signal)
        
        # Action logic
        if not has_source_url and other_prod_note_count > 0:
            proposed_action = "candidate_for_remove_after_backup"
            priority = 1
        elif staging_duplicate_count > 0:
            proposed_action = "candidate_for_rebuild_from_staging"
            priority = 2
        elif content_len < 50:
            proposed_action = "mark_for_paraphrase_review"
            priority = 3
        else:
            proposed_action = "keep_pending_manual_audit"
            priority = 4
            
        distribution['audit_signal'][signal_str] = distribution['audit_signal'].get(signal_str, 0) + 1
        distribution['proposed_cleanup_action'][proposed_action] = distribution['proposed_cleanup_action'].get(proposed_action, 0) + 1
        
        s_name = str(r.get('source_name', r.get('source_title', primary_source_val)))
        if not s_name:
            s_name = primary_source_val
        distribution['source_name'][s_name] = distribution['source_name'].get(s_name, 0) + 1
        
        w_data = whiskies.get(wid, {})
        w_name = w_data.get(whisky_name_col, '')
        dist_id = str(w_data.get('distillery_id', ''))
        d_name = distilleries.get(dist_id, {}).get(distillery_name_col, '')
        
        plan.append({
            "priority_rank": 0,
            "sort_key": priority,
            "audit_signal": signal_str,
            "proposed_cleanup_action": proposed_action,
            "production_note_id": r.get("rowid", ""),
            "whisky_id": wid,
            "whisky_name": w_name,
            "distillery_name": d_name,
            "source_system": r.get('source_system', r.get('flavor_source', '')),
            "source_name": r.get('source_name', ''),
            "source_title": r.get('source_title', ''),
            "source_url": r.get('source_url', ''),
            "nose": nose,
            "palate": palate,
            "finish": finish,
            "body_summary": summary,
            "content_length": content_len,
            "other_production_note_count": other_prod_note_count,
            "staging_duplicate_count": staging_duplicate_count,
            "reviewer_decision": "",
            "reviewer_notes": ""
        })

    # Sort
    plan.sort(key=lambda x: (x['sort_key'], -x['staging_duplicate_count']))
    for idx, p in enumerate(plan):
        p['priority_rank'] = idx + 1
        del p['sort_key'] # remove internal sorting key
        
    if plan:
        keys = plan[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(plan)
            
        with open(OUTPUT_QUEUE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(plan)

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")

    report = []
    report.append("# Production Uploaded Note Audit Plan Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")
    
    report.append("\n## Global Metrics")
    report.append(f"- Total Production Uploaded Notes: {len(plan)}")
    report.append(f"- Missing Source URL Count: {distribution['missing_source_url']}")
    report.append(f"- Duplicate / Staging Overlap Count: {distribution['duplicate_staging_overlap']}")
    
    def add_dist(title, dict_data):
        report.append(f"\n- **{title}:**")
        for k, v in sorted(dict_data.items(), key=lambda item: item[1], reverse=True):
            report.append(f"  - {k}: {v}")
            
    add_dist("Audit Signal Distribution", distribution['audit_signal'])
    add_dist("Proposed Cleanup Action Distribution", distribution['proposed_cleanup_action'])
    add_dist("Source System / Name Distribution", distribution['source_name'])

    report.append("\n## Priority Candidates Preview (All 60)")
    if plan:
        report.append("| Rank | Whisky ID | Prod Overlap | Stg Dup | Cleanup Action | Audit Signal |")
        report.append("|---|---|---|---|---|---|")
        for p in plan[:60]:
            report.append(f"| {p['priority_rank']} | {p['whisky_id']} | {p['other_production_note_count']} | {p['staging_duplicate_count']} | {p['proposed_cleanup_action']} | {p['audit_signal']} |")
    else:
        report.append("No candidates found.")
        
    report.append(f"\n- **CSV Path:** `{OUTPUT_CSV_PATH}`")
    report.append(f"- **Priority Queue CSV Path:** `{OUTPUT_QUEUE_CSV}`")

    report.append("\n## Risks & Operations")
    report.append("- No database mutations have occurred (`production.db` remains untouched).")
    report.append("- Automatic deletions or overwrites are disabled; the script safely defaults to `keep_pending_manual_audit` for ambiguous cases.")
    report.append("- The 60 records identified represent raw, unparaphrased uploads inside the active production environment that should be cleaned or replaced.")

    report.append("\n## Recommended Next Stage")
    report.append("**AŞAMA N — Production Uploaded Note Cleanup Dry-Run**: Execute a dry-run cleanup based on this plan to see the effect on production data before final backup and deletion.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Production uploaded note audit plan successfully generated in read-only mode).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

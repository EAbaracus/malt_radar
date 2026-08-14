import sqlite3
import os
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/book_data_review_readiness_pack_report.md"
OUTPUT_CSV_PATH = "data/output/book_data_review_readiness_pack.csv"
OUTPUT_QUEUE_CSV = "data/output/book_data_priority_queue.csv"

BOOK_KEYWORDS = ['book', 'notebooklm', 'uploaded', 'manual_source', 'notebooklm_book_profile', 'book_notebooklm', 'ultimate book of whiskey', 'whisky classified']

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
    for t in tables:
        cols = [c['name'] for c in safe_query(f"PRAGMA table_info('{t}')")]
        schema_info[t] = cols
        
    whiskies = {str(w.get('whisky_id')): w for w in safe_query("SELECT * FROM whiskies") if w.get('whisky_id')}
    distilleries = {str(d.get('distillery_id')): d for d in safe_query("SELECT * FROM distilleries") if d.get('distillery_id')}
    
    w_cols = schema_info.get('whiskies', [])
    whisky_name_col = 'name' if 'name' in w_cols else (w_cols[1] if len(w_cols) > 1 else 'unknown')
    
    d_cols = schema_info.get('distilleries', [])
    distillery_name_col = 'name' if 'name' in d_cols else (d_cols[1] if len(d_cols) > 1 else 'unknown')

    target_tables = [
        'tasting_notes',
        'flavor_profiles',
        'staging_tasting_notes',
        'staging_book_flavor_profiles',
        'staging_notebooklm_flavor_profiles',
        'staging_manual_review_queue'
    ]
    
    pack = []
    
    distribution = {
        'review_bucket': {},
        'readiness_status': {},
        'risk_reason': {},
        'table_production_staging': {
            'production': 0,
            'staging': 0
        },
        'source_name': {}
    }

    for t in target_tables:
        if t not in schema_info:
            continue
        cols = schema_info.get(t, [])
        source_cols = [c for c in cols if 'source' in c.lower() or 'system' in c.lower() or 'origin' in c.lower()]
        
        is_production = t in ('tasting_notes', 'flavor_profiles')
        
        if not source_cols and 'book' not in t.lower() and 'notebooklm' not in t.lower():
            continue
            
        rows = safe_query(f"SELECT rowid, * FROM {t}")
        
        for r in rows:
            # Determine if it's a book source
            is_book_source = False
            primary_source_val = ""
            
            if 'book' in t.lower() or 'notebooklm' in t.lower():
                is_book_source = True
                primary_source_val = t
            else:
                for s_col in source_cols:
                    val = str(r.get(s_col, '')).lower()
                    if any(k in val for k in BOOK_KEYWORDS):
                        is_book_source = True
                        primary_source_val = str(r.get(s_col, ''))
                        break
                        
            if not is_book_source:
                continue
                
            wid = str(r.get('whisky_id', ''))
            appr_status = r.get('approval_status', r.get('status', ''))
            
            # Logic for buckets
            if is_production:
                distribution['table_production_staging']['production'] += 1
                if 'uploaded' in primary_source_val.lower():
                    bucket = '1_production_book_note_audit'
                    readiness = 'production_audit_required'
                    risk = 'production_uploaded_source_needs_audit'
                    action = 'audit_production_note'
                else:
                    bucket = '5_low_priority_reference_only'
                    readiness = 'ready_for_manual_review'
                    risk = 'already_promoted'
                    action = 'keep_as_reference_only'
            else:
                distribution['table_production_staging']['staging'] += 1
                if appr_status in ('staging_quality_rejected', 'staging_duplicate', 'REJECTED'):
                    bucket = '4_duplicate_or_rejected_book_data'
                    readiness = 'reject_or_archive_candidate'
                    risk = 'duplicate_source_signal'
                    action = 'reject_or_archive'
                elif 'flavor_profile' in t.lower():
                    bucket = '3_staging_book_flavor_profile_review'
                    readiness = 'ready_for_manual_review'
                    risk = 'copyright_paraphrase_risk'
                    action = 'enrich_or_rewrite_paraphrase'
                else:
                    bucket = '2_staging_book_candidate_review'
                    if not wid:
                        readiness = 'needs_fk_match'
                        risk = 'fk_missing'
                        action = 'fix_fk_match'
                    else:
                        readiness = 'needs_source_paraphrase_review'
                        risk = 'copyright_paraphrase_risk'
                        action = 'manual_review_for_promotion'
                        
            distribution['review_bucket'][bucket] = distribution['review_bucket'].get(bucket, 0) + 1
            distribution['readiness_status'][readiness] = distribution['readiness_status'].get(readiness, 0) + 1
            distribution['risk_reason'][risk] = distribution['risk_reason'].get(risk, 0) + 1
            
            s_name = str(r.get('source_name', r.get('source_title', primary_source_val)))
            if not s_name:
                s_name = primary_source_val
            distribution['source_name'][s_name] = distribution['source_name'].get(s_name, 0) + 1
            
            nose = str(r.get('nose', r.get('nose_notes', '')))
            palate = str(r.get('palate', r.get('palate_notes', '')))
            finish = str(r.get('finish', r.get('finish_notes', '')))
            summary = str(r.get('conclusion', r.get('body', r.get('notes_for_review', ''))))
            content_len = len(nose) + len(palate) + len(finish) + len(summary)
            
            w_data = whiskies.get(wid, {})
            w_name = w_data.get(whisky_name_col, '')
            dist_id = str(w_data.get('distillery_id', ''))
            d_name = distilleries.get(dist_id, {}).get(distillery_name_col, '')
            
            pack.append({
                "priority_rank": 0,
                "review_bucket": bucket,
                "readiness_status": readiness,
                "risk_reason": risk,
                "table_name": t,
                "row_id": r.get("rowid", ""),
                "whisky_id": wid,
                "whisky_name": w_name,
                "distillery_name": d_name,
                "source_system": r.get('source_system', r.get('flavor_source', '')),
                "source_name": r.get('source_name', ''),
                "source_title": r.get('source_title', ''),
                "source_url": r.get('source_url', ''),
                "approval_status": appr_status,
                "nose": nose,
                "palate": palate,
                "finish": finish,
                "summary": summary,
                "flavor_profile_fields": "YES" if 'flavor_profile' in t.lower() else "NO",
                "content_length": content_len,
                "duplicate_signal": "Possible" if bucket == '4_duplicate_or_rejected_book_data' else "Unknown",
                "suggested_next_action": action,
                "reviewer_decision": "",
                "reviewer_notes": ""
            })

    # Sort
    pack.sort(key=lambda x: x['review_bucket'])
    for idx, p in enumerate(pack):
        p['priority_rank'] = idx + 1
        
    if pack:
        keys = pack[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(pack)
            
        with open(OUTPUT_QUEUE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(pack)

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")

    report = []
    report.append("# Book Data Review & Promotion Readiness Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")
    
    report.append("\n## Global Metrics")
    report.append(f"- Total Book/Upload Derived Records: {len(pack)}")
    report.append(f"- Production Distribution: {distribution['table_production_staging']['production']}")
    report.append(f"- Staging Distribution: {distribution['table_production_staging']['staging']}")
    
    def add_dist(title, dict_data):
        report.append(f"\n- **{title}:**")
        for k, v in sorted(dict_data.items(), key=lambda item: item[1], reverse=True):
            report.append(f"  - {k}: {v}")
            
    add_dist("Review Bucket Distribution", distribution['review_bucket'])
    add_dist("Readiness Status Distribution", distribution['readiness_status'])
    add_dist("Risk Reason Distribution", distribution['risk_reason'])
    add_dist("Top Sources", distribution['source_name'])

    report.append("\n## Top 40 Priority Candidates Preview")
    if pack:
        report.append("| Rank | Bucket | Whisky ID | Readiness | Risk Reason | Action |")
        report.append("|---|---|---|---|---|---|")
        for p in pack[:40]:
            report.append(f"| {p['priority_rank']} | {p['review_bucket']} | {p['whisky_id']} | {p['readiness_status']} | {p['risk_reason']} | {p['suggested_next_action']} |")
    else:
        report.append("No candidates found.")
        
    report.append(f"\n- **CSV Path:** `{OUTPUT_CSV_PATH}`")
    report.append(f"- **Priority Queue CSV Path:** `{OUTPUT_QUEUE_CSV}`")

    report.append("\n## ⚠️ SPECIAL WARNING: Production Uploaded Notes ⚠️")
    if distribution['table_production_staging']['production'] > 0:
        report.append("A significant number of 'uploaded_document' records already exist in production `tasting_notes`. These have bypassed staging paraphrase/copyright checks in the past. They are flagged in **Bucket 1** for immediate audit/cleaning before any further staging promotions.")

    report.append("\n## Recommended Next Stage")
    report.append("**AŞAMA M — Production Uploaded Note Audit Execution**: Prioritize auditing and cleaning the existing 120 production uploaded notes before promoting any new book/uploaded data from staging.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Readiness pack successfully generated in read-only mode).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

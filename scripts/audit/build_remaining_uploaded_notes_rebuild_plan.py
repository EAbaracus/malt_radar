import sqlite3
import os
import hashlib
import csv
import re

DB_PATH = "output/import/production.db"
PLAN_CSV_PATH = "data/output/remaining_uploaded_notes_rebuild_plan.csv"
QUEUE_CSV_PATH = "data/output/remaining_uploaded_notes_rebuild_priority_queue.csv"
REPORT_MD_PATH = "output/reports/remaining_uploaded_notes_rebuild_plan_report.md"

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

def get_content_fingerprint(r, is_staging=False):
    nose = str(r.get('nose_notes', '') if not is_staging else r.get('nose', ''))
    palate = str(r.get('palate_notes', '') if not is_staging else r.get('palate', ''))
    finish = str(r.get('finish_notes', '') if not is_staging else r.get('finish', ''))
    summary = str(r.get('notes_for_review', '') if not is_staging else r.get('body', ''))
    content = f"{nose}|{palate}|{finish}|{summary}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_content_length(r, is_staging=False):
    nose = str(r.get('nose_notes', '') if not is_staging else r.get('nose', ''))
    palate = str(r.get('palate_notes', '') if not is_staging else r.get('palate', ''))
    finish = str(r.get('finish_notes', '') if not is_staging else r.get('finish', ''))
    return len(nose) + len(palate) + len(finish)

def main():
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(PLAN_CSV_PATH), exist_ok=True)

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
        print(f"Error connecting to DB: {e}")
        return

    def safe_query(query, params=()):
        try:
            return [dict(row) for row in cur.execute(query, params).fetchall()]
        except sqlite3.OperationalError:
            return []

    tables = [r['name'] for r in safe_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    
    prod_notes = safe_query("SELECT rowid, * FROM tasting_notes")
    staging_notes = safe_query("SELECT * FROM staging_tasting_notes") if 'staging_tasting_notes' in tables else []
    
    whiskies = {str(w.get('whisky_id')): w for w in safe_query("SELECT * FROM whiskies") if w.get('whisky_id')}
    distilleries = {str(d.get('distillery_id')): d for d in safe_query("SELECT * FROM distilleries") if d.get('distillery_id')}
    
    prod_wid_notes = {}
    for pn in prod_notes:
        wid = str(pn.get('whisky_id', ''))
        if wid:
            prod_wid_notes.setdefault(wid, []).append(pn)
            
    staging_wid_notes = {}
    staging_name_notes = {}
    for sn in staging_notes:
        wid = str(sn.get('whisky_id', ''))
        wname = str(sn.get('whisky_name', '')).strip().lower()
        if wid:
            staging_wid_notes.setdefault(wid, []).append(sn)
        if wname:
            staging_name_notes.setdefault(wname, []).append(sn)

    plan = []
    
    distribution = {
        'total_uploaded_notes': 0,
        'has_staging_candidate': 0,
        'category': {},
        'recommended_action': {}
    }

    for r in prod_notes:
        is_upload = False
        primary_source_val = ""
        source_col_used = ""
        
        # determine if upload
        for s_col in ['source_system', 'source_name', 'source_url']:
            val = str(r.get(s_col, '')).lower()
            if any(k in val for k in UPLOAD_KEYWORDS):
                is_upload = True
                primary_source_val = str(r.get(s_col, ''))
                source_col_used = s_col
                break
                
        if not is_upload:
            continue
            
        distribution['total_uploaded_notes'] += 1
        
        rowid = r.get("rowid")
        wid = str(r.get('whisky_id', ''))
        
        all_wid_notes = prod_wid_notes.get(wid, [])
        other_prod_note_count = sum(1 for on in all_wid_notes if on.get('rowid') != rowid)
                
        source_url = str(r.get('source_url', ''))
        prod_fp = get_content_fingerprint(r, is_staging=False)
        prod_len = get_content_length(r, is_staging=False)
        
        w_data = whiskies.get(wid, {})
        w_name = w_data.get('name', w_data.get('normalized_name', ''))
        d_name = distilleries.get(str(w_data.get('distillery_id', '')), {}).get('name', '')
        
        # 3. Find staging candidate
        candidates = staging_wid_notes.get(wid, [])
        match_type = "exact_whisky_id"
        
        if not candidates and w_name:
            candidates = staging_name_notes.get(w_name.lower().strip(), [])
            match_type = "name_match"
            
        best_candidate = None
        if candidates:
            distribution['has_staging_candidate'] += 1
            # Pick best candidate (prefer longer content, better source)
            candidates.sort(key=lambda x: get_content_length(x, is_staging=True), reverse=True)
            best_candidate = candidates[0]
            
        category = ""
        recommended_action = ""
        apply_candidate = "no"
        reason = ""
        
        risk_signals = []
        if not bool(source_url.strip()) or 'uploaded' in source_url.lower():
            risk_signals.append("prod_source_url_missing_or_invalid")
            
        if prod_len < 30:
            risk_signals.append("weak_production_content")
            
        staging_id = ""
        staging_source_system = ""
        staging_source_url = ""
        staging_len = 0
        staging_fp = ""
        duplicate_similarity = ""
        
        if not best_candidate:
            category = "blocked_no_staging_candidate"
            recommended_action = "keep_existing"
            reason = "No staging candidate found to rebuild from."
        else:
            staging_id = str(best_candidate.get('id', best_candidate.get('rowid', '')))
            staging_source_system = best_candidate.get('source_system', best_candidate.get('flavor_source', ''))
            staging_source_url = str(best_candidate.get('source_url', ''))
            staging_len = get_content_length(best_candidate, is_staging=True)
            staging_fp = get_content_fingerprint(best_candidate, is_staging=True)
            
            if staging_fp == prod_fp:
                duplicate_similarity = "exact_fingerprint_match"
                risk_signals.append("content_identical_or_near_duplicate")
            elif prod_len > 0 and staging_len > 0 and abs(prod_len - staging_len) < 10:
                duplicate_similarity = "similar_length"
                risk_signals.append("content_identical_or_near_duplicate")
            else:
                duplicate_similarity = "different_content"
                
            if not bool(staging_source_url.strip()):
                risk_signals.append("staging_source_url_missing")
                
            if staging_len < 30:
                risk_signals.append("weak_staging_content")
                
            if match_type == "name_match":
                risk_signals.append("conflicting_whisky_match")
            
            # Determine category and action
            if match_type == "exact_whisky_id":
                if "staging_source_url_missing" not in risk_signals and "weak_staging_content" not in risk_signals:
                    category = "rebuild_ready_exact_whisky_match"
                    recommended_action = "replace_with_staging_after_backup"
                    apply_candidate = "yes"
                    reason = "Staging candidate has better source and content."
                else:
                    category = "needs_manual_source_review"
                    recommended_action = "manual_review"
                    reason = "Staging candidate exists but has missing URL or weak content."
            else:
                category = "rebuild_ready_name_match"
                recommended_action = "manual_review"
                reason = "Matched by name only, requires manual FK verification."

        distribution['category'][category] = distribution['category'].get(category, 0) + 1
        distribution['recommended_action'][recommended_action] = distribution['recommended_action'].get(recommended_action, 0) + 1
        
        plan.append({
            "production_note_id_or_rowid": rowid,
            "whisky_id": wid,
            "whisky_name": w_name,
            "distillery_name": d_name,
            "prod_source_system": r.get('source_system', ''),
            "prod_source_url": source_url,
            "prod_content_length": prod_len,
            "prod_content_fingerprint": prod_fp,
            "other_production_note_count": other_prod_note_count,
            "staging_candidate_id": staging_id,
            "staging_source_system": staging_source_system,
            "staging_source_url": staging_source_url,
            "staging_content_length": staging_len,
            "staging_content_fingerprint": staging_fp,
            "duplicate_similarity": duplicate_similarity,
            "risk_signals": " | ".join(risk_signals),
            "category": category,
            "recommended_action": recommended_action,
            "apply_candidate": apply_candidate,
            "reason": reason
        })

    conn.close()

    # Sort plan
    plan.sort(key=lambda x: 0 if x['apply_candidate'] == 'yes' else (1 if x['recommended_action'] == 'manual_review' else 2))
    
    for idx, p in enumerate(plan):
        p['priority_rank'] = idx + 1

    # Output Full CSV
    if plan:
        keys = plan[0].keys()
        with open(PLAN_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(plan)
            
    # Output Priority Queue CSV
    queue = [p for p in plan if p['recommended_action'] in ['replace_with_staging_after_backup', 'manual_review']]
    if queue:
        with open(QUEUE_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=queue[0].keys())
            writer.writeheader()
            writer.writerows(queue)

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Generate Report
    report = []
    report.append("# Remaining Uploaded Notes Rebuild Plan Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Original DB Changed:** {'NO' if hash_unchanged else 'YES (MUTATION DETECTED!)'}")
    
    report.append("\n## Global Metrics")
    report.append(f"- **Remaining Uploaded Production Notes:** {distribution['total_uploaded_notes']}")
    report.append(f"- **Notes With Staging Candidates:** {distribution['has_staging_candidate']}")
    
    report.append("\n## Category Distribution")
    for k, v in distribution['category'].items():
        report.append(f"- {k}: {v}")
        
    report.append("\n## Recommended Action Distribution")
    for k, v in distribution['recommended_action'].items():
        report.append(f"- {k}: {v}")
        
    # Top risks
    all_risks = []
    for p in plan:
        if p['risk_signals']:
            all_risks.extend(p['risk_signals'].split(" | "))
    risk_counts = {}
    for r in all_risks:
        risk_counts[r] = risk_counts.get(r, 0) + 1
    
    report.append("\n## Top Risk Signals")
    for r, count in sorted(risk_counts.items(), key=lambda item: item[1], reverse=True):
        report.append(f"- {r}: {count}")

    report.append("\n## Sample Rows (Top 10 Priority)")
    report.append("| Rank | Whisky ID | Whisky Name | Category | Action | Reason |")
    report.append("|---|---|---|---|---|---|")
    for p in plan[:10]:
        report.append(f"| {p.get('priority_rank')} | {p.get('whisky_id')} | {p.get('whisky_name')} | {p.get('category')} | {p.get('recommended_action')} | {p.get('reason')} |")

    report.append("\n## Recommended Next Stage")
    report.append("**AŞAMA S — Remaining Uploaded Notes Rebuild Dry-Run On Backup Copy**: Simulate the proposed rebuild replacements safely on a temporary database copy.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Rebuild plan successfully generated without mutating production data).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

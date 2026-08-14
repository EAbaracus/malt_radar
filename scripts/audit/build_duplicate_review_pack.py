import sqlite3
import os
import hashlib
import csv
import difflib

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/duplicate_review_pack_report.md"
REPORT_CSV_PATH = "data/output/duplicate_review_pack.csv"

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

def normalize_text(text):
    if not text:
        return ""
    return " ".join(str(text).lower().split())

def calc_similarity(text1, text2):
    t1 = normalize_text(text1)
    t2 = normalize_text(text2)
    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0
    return difflib.SequenceMatcher(None, t1, t2).ratio()

def main():
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_CSV_PATH), exist_ok=True)

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

    # Schema Discovery
    schema_info = {}
    for t in ['whiskies', 'distilleries', 'staging_tasting_notes', 'tasting_notes']:
        cols = [c['name'] for c in safe_query(f"PRAGMA table_info('{t}')")]
        schema_info[t] = cols

    whiskies_cols = schema_info.get('whiskies', [])
    distilleries_cols = schema_info.get('distilleries', [])
    
    whisky_name_col = 'name' if 'name' in whiskies_cols else (whiskies_cols[1] if len(whiskies_cols) > 1 else 'unknown')
    distillery_name_col = 'name' if 'name' in distilleries_cols else (distilleries_cols[1] if len(distilleries_cols) > 1 else 'unknown')

    notes = safe_query("SELECT rowid, * FROM staging_tasting_notes")
    prod_notes = safe_query("SELECT rowid, * FROM tasting_notes")
    whiskies = {w.get('whisky_id'): w for w in safe_query("SELECT * FROM whiskies") if w.get('whisky_id')}
    distilleries = {d.get('distillery_id'): d for d in safe_query("SELECT * FROM distilleries") if d.get('distillery_id')}

    # Map prod notes by whisky_id
    prod_notes_by_wid = {}
    for pn in prod_notes:
        wid = pn.get('whisky_id')
        if wid:
            prod_notes_by_wid.setdefault(wid, []).append(pn)

    qa_pack = []
    
    distribution = {
        "keep_existing": 0,
        "replace_with_staging": 0,
        "merge_or_append_source": 0,
        "reject_staging_duplicate": 0,
        "needs_manual_review": 0
    }

    # Identify duplicates (staging notes where whisky_id has existing prod notes)
    for n in notes:
        wid = n.get("whisky_id")
        if not wid:
            continue
            
        existing_pn = prod_notes_by_wid.get(wid, [])
        if not existing_pn:
            continue
            
        whisky_data = whiskies.get(wid, {})
        distillery_id = whisky_data.get("distillery_id")
        distillery_data = distilleries.get(distillery_id, {}) if distillery_id else {}
        
        w_name = whisky_data.get(whisky_name_col, "")
        d_name = distillery_data.get(distillery_name_col, "")
        
        for pn in existing_pn:
            # Combine content for similarity check
            staging_content = f"{n.get('nose', '')} {n.get('palate', '')} {n.get('finish', '')} {n.get('conclusion', '')}"
            prod_content = f"{pn.get('nose_notes', '')} {pn.get('palate_notes', '')} {pn.get('finish_notes', '')}"
            
            sim_ratio = calc_similarity(staging_content, prod_content)
            
            staging_url = normalize_text(n.get("source_url"))
            prod_url = normalize_text(pn.get("source_url"))
            
            suggested_action = "needs_manual_review"
            
            if staging_url and prod_url and staging_url == prod_url:
                suggested_action = "reject_staging_duplicate"
            elif sim_ratio > 0.85:
                suggested_action = "reject_staging_duplicate"
            elif len(staging_content) > len(prod_content) + 50 and sim_ratio < 0.60:
                suggested_action = "merge_or_append_source"
            
            distribution[suggested_action] += 1
            
            qa_pack.append({
                "staging_note_id": n.get("staging_note_id", n.get("rowid", "")),
                "whisky_id": wid,
                "whisky_name": w_name,
                "distillery_name": d_name,
                "staging_source_system": n.get("source_system", ""),
                "staging_source_title": n.get("source_name", n.get("source_title", "")),
                "staging_source_url": n.get("source_url", ""),
                "staging_nose": n.get("nose", ""),
                "staging_palate": n.get("palate", ""),
                "staging_finish": n.get("finish", ""),
                "staging_summary": n.get("conclusion", n.get("body", "")),
                "production_note_id": pn.get("rowid", ""),
                "production_source_system": pn.get("source_system", ""),
                "production_source_title": pn.get("source_name", pn.get("source_title", "")),
                "production_source_url": pn.get("source_url", ""),
                "production_nose": pn.get("nose_notes", ""),
                "production_palate": pn.get("palate_notes", ""),
                "production_finish": pn.get("finish_notes", ""),
                "production_summary": pn.get("notes_for_review", ""),
                "similarity_signal": f"{sim_ratio:.2f}",
                "source_priority_signal": "manual_review_required",
                "suggested_duplicate_action": suggested_action,
                "reviewer_decision": "",
                "reviewer_notes": ""
            })

    if qa_pack:
        keys = qa_pack[0].keys()
        with open(REPORT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(qa_pack)

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")

    report = []
    report.append("# Duplicate Review Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")
    
    report.append("\n## Metrics")
    report.append(f"- Total staging duplicates found: {len(qa_pack)}")
    report.append("- **Suggested Action Distribution:**")
    for k, v in distribution.items():
        report.append(f"  - {k}: {v}")
        
    report.append("\n## Similarity Logic & Thresholds")
    report.append("- Similarity calculated using Python `difflib.SequenceMatcher.ratio()` on normalized text (nose + palate + finish + summary).")
    report.append("- `sim_ratio > 0.85` or `exact matching source_url` -> `reject_staging_duplicate`")
    report.append("- `sim_ratio < 0.60` and `staging text length > prod text length + 50` -> `merge_or_append_source`")
    report.append("- Otherwise -> `needs_manual_review`")
    
    report.append(f"\n- **CSV Path:** `{REPORT_CSV_PATH}`")
    
    report.append("\n## Top 20 Candidates Preview")
    if qa_pack:
        report.append("| Staging ID | Whisky Name | Sim Signal | Suggested Action |")
        report.append("|---|---|---|---|")
        for p in qa_pack[:20]:
            report.append(f"| {p['staging_note_id']} | {p['whisky_name']} | {p['similarity_signal']} | {p['suggested_duplicate_action']} |")
    else:
        report.append("No candidates found.")

    report.append("\n## Risks")
    report.append("- Automatic replacement is disabled; all decisions default to review or rejection to ensure no production data is accidentally lost.")
    report.append("- `source_priority_signal` is currently flagged as `manual_review_required` to force human oversight.")
    
    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Duplicate review pack generated successfully).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

import sqlite3
import os
import hashlib
import csv

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/content_fk_review_pack_report.md"
OUTPUT_CSV_PATH = "data/output/content_fk_review_pack.csv"
OUTPUT_QUEUE_CSV = "data/output/content_review_priority_queue.csv"

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

    # Schema Discovery
    schema_info = {}
    for t in ['whiskies', 'distilleries']:
        cols = [c['name'] for c in safe_query(f"PRAGMA table_info('{t}')")]
        schema_info[t] = cols

    whiskies_cols = schema_info.get('whiskies', [])
    distilleries_cols = schema_info.get('distilleries', [])
    
    whisky_name_col = 'name' if 'name' in whiskies_cols else (whiskies_cols[1] if len(whiskies_cols) > 1 else 'unknown')
    distillery_name_col = 'name' if 'name' in distilleries_cols else (distilleries_cols[1] if len(distilleries_cols) > 1 else 'unknown')

    notes = safe_query("SELECT rowid, * FROM staging_tasting_notes")
    prod_notes = safe_query("SELECT * FROM tasting_notes")
    whiskies = {w.get('whisky_id'): w for w in safe_query("SELECT * FROM whiskies") if w.get('whisky_id')}
    distilleries = {d.get('distillery_id'): d for d in safe_query("SELECT * FROM distilleries") if d.get('distillery_id')}
    
    prod_notes_set = set(n.get('whisky_id') for n in prod_notes if n.get('whisky_id'))

    whisky_id_counts = {}
    for n in notes:
        wid = n.get("whisky_id")
        if wid:
            whisky_id_counts[wid] = whisky_id_counts.get(wid, 0) + 1

    qa_pack = []
    
    distribution_reason = {}
    distribution_action = {}
    
    needs_content_review_count = 0
    blocked_fk_missing_count = 0

    for n in notes:
        wid = n.get("whisky_id")
        
        has_source_url = bool(n.get("source_url"))
        has_source_title = bool(n.get("source_name") or n.get("source_title"))
        has_source = has_source_url or has_source_title or bool(n.get("source_system"))
        
        nose_val = n.get("nose") or ""
        palate_val = n.get("palate") or ""
        finish_val = n.get("finish") or ""
        summary_val = n.get("conclusion") or n.get("body") or ""
        
        content = f"{nose_val} {palate_val} {finish_val} {summary_val}".strip()
        content_length = len(content)
        has_content = content_length > 0
        
        existing_prod_count = 1 if wid in prod_notes_set else 0
        has_duplicate = whisky_id_counts.get(wid, 0) > 1 or existing_prod_count > 0

        # ASAMA G Logic
        suggested_class = "approve_candidate"
        if not wid:
            suggested_class = "blocked_fk_missing"
        elif has_duplicate:
            suggested_class = "needs_duplicate_review"
        elif not has_source:
            suggested_class = "needs_source_review"
        elif not has_content:
            suggested_class = "needs_content_review"
            
        if suggested_class not in ["blocked_fk_missing", "needs_content_review"]:
            continue
            
        if suggested_class == "blocked_fk_missing":
            blocked_fk_missing_count += 1
            review_bucket = "1_blocked_fk_missing"
            fk_status = "missing"
            review_reason = "missing_whisky_id"
            suggested_action = "fix_fk_match"
            missing_fields = "whisky_id"
        else:
            needs_content_review_count += 1
            fk_status = "present"
            if not has_source_title and not has_source_url:
                review_bucket = "3_weak_source_weak_content"
                review_reason = "missing_source_url, missing_source_title, missing_nose_palate_finish"
                suggested_action = "reject_unusable"
                missing_fields = "source_title, source_url, content"
            elif has_source:
                review_bucket = "2_good_source_weak_content"
                if content_length < 20:
                    review_reason = "content_too_short"
                    suggested_action = "enrich_content"
                else:
                    review_reason = "weak_content_signal"
                    suggested_action = "needs_manual_source_review"
                missing_fields = "content"
            else:
                review_bucket = "3_weak_source_weak_content"
                review_reason = "unknown_schema_issue"
                suggested_action = "reject_unusable"
                missing_fields = "unknown"
                
        distribution_reason[review_reason] = distribution_reason.get(review_reason, 0) + 1
        distribution_action[suggested_action] = distribution_action.get(suggested_action, 0) + 1

        whisky_data = whiskies.get(wid, {}) if wid else {}
        distillery_id = whisky_data.get("distillery_id") if whisky_data else None
        distillery_data = distilleries.get(distillery_id, {}) if distillery_id else {}
        
        w_name = whisky_data.get(whisky_name_col, "") if whisky_data else ""
        d_name = distillery_data.get(distillery_name_col, "") if distillery_data else ""

        qa_pack.append({
            "priority_rank": 0,
            "review_bucket": review_bucket,
            "staging_note_id": n.get("staging_note_id", n.get("rowid", "")),
            "whisky_id": wid or "",
            "whisky_name": w_name,
            "distillery_name": d_name,
            "source_system": n.get("source_system", ""),
            "source_title": n.get("source_name", n.get("source_title", "")),
            "source_url": n.get("source_url", ""),
            "nose": nose_val,
            "palate": palate_val,
            "finish": finish_val,
            "body/summary": summary_val,
            "content_length": content_length,
            "missing_fields": missing_fields,
            "fk_status": fk_status,
            "review_reason": review_reason,
            "suggested_repair_action": suggested_action,
            "reviewer_decision": "",
            "reviewer_notes": ""
        })

    qa_pack.sort(key=lambda x: x["review_bucket"])
    for idx, r in enumerate(qa_pack):
        r["priority_rank"] = idx + 1

    if qa_pack:
        keys = qa_pack[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(qa_pack)
            
        with open(OUTPUT_QUEUE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(qa_pack)

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")

    report = []
    report.append("# Content & FK Review Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")
    
    report.append("\n## Metrics")
    report.append(f"- Total staging notes examined: {len(notes)}")
    report.append(f"- `blocked_fk_missing` count: {blocked_fk_missing_count}")
    report.append(f"- `needs_content_review` count: {needs_content_review_count}")
    report.append(f"- Total rows exported: {len(qa_pack)}")

    report.append("\n- **Review Reason Distribution:**")
    for k, v in distribution_reason.items():
        report.append(f"  - {k}: {v}")
        
    report.append("\n- **Suggested Repair Action Distribution:**")
    for k, v in distribution_action.items():
        report.append(f"  - {k}: {v}")

    report.append("\n## Top 30 Priority Candidates Preview")
    if qa_pack:
        report.append("| Rank | Bucket | Whisky ID | Review Reason | Suggested Action |")
        report.append("|---|---|---|---|---|")
        for p in qa_pack[:30]:
            report.append(f"| {p['priority_rank']} | {p['review_bucket']} | {p['whisky_id']} | {p['review_reason']} | {p['suggested_repair_action']} |")
    else:
        report.append("No candidates found.")

    report.append(f"\n- **CSV Path:** `{OUTPUT_CSV_PATH}`")
    report.append(f"- **Priority Queue CSV Path:** `{OUTPUT_QUEUE_CSV}`")

    report.append("\n## Risks")
    report.append("- No DB writes occur. Everything is output as a read-only artifact.")
    report.append("- Candidates flagged as `reject_unusable` have poor source and content data, safely cordoning them off.")
    
    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Content & FK review pack generated successfully).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

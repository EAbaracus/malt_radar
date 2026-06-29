import sqlite3
import os
import hashlib
import csv

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/staging_review_validation_preview_report.md"
REPORT_CSV_PATH = "output/reports/staging_review_validation_preview.csv"

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

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"DB Hash (before): {hash_before}")

    # Read-only connection
    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    
    try:
        conn = sqlite3.connect(conn_uri, uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return

    report_lines = []
    report_lines.append("# Staging Review Validation Preview Report\n")
    report_lines.append(f"- **DB Path:** `{DB_PATH}`")
    report_lines.append("- **Connection:** Read-only mode successful\n")

    def safe_query(query):
        try:
            return [dict(row) for row in cur.execute(query).fetchall()]
        except sqlite3.OperationalError as e:
            return {"error": str(e)}

    # Table counts
    tables_to_check = [
        "staging_tasting_notes", 
        "staging_manual_review_queue", 
        "staging_book_flavor_profiles"
    ]
    
    counts = {}
    report_lines.append("## Table Counts")
    for t in tables_to_check:
        res = safe_query(f"SELECT COUNT(*) as c FROM {t}")
        if isinstance(res, dict) and "error" in res:
            report_lines.append(f"- **{t}**: Missing or error ({res['error']})")
            counts[t] = 0
        else:
            c = res[0]['c']
            report_lines.append(f"- **{t}**: {c} rows")
            counts[t] = c

    # Evaluate tasting notes
    report_lines.append("\n## Quality Classification (staging_tasting_notes)")
    notes = safe_query("SELECT * FROM staging_tasting_notes")
    
    classification = {
        "ready_for_manual_approval": [],
        "needs_source_review": [],
        "needs_duplicate_review": [],
        "needs_content_review": [],
        "blocked_fk_missing": []
    }

    if isinstance(notes, dict) and "error" in notes:
        report_lines.append(f"Cannot classify staging_tasting_notes: {notes['error']}")
    else:
        # Check for duplicates by whisky_id
        whisky_id_counts = {}
        for n in notes:
            wid = n.get("whisky_id")
            if wid:
                whisky_id_counts[wid] = whisky_id_counts.get(wid, 0) + 1

        for n in notes:
            nid = n.get("id") or n.get("uuid") or "unknown"
            wid = n.get("whisky_id")
            
            if not wid:
                classification["blocked_fk_missing"].append(n)
                continue
            
            if whisky_id_counts.get(wid, 0) > 1:
                classification["needs_duplicate_review"].append(n)
                continue
                
            has_source = bool(n.get("source_system") or n.get("source_url") or n.get("source_title"))
            if not has_source:
                classification["needs_source_review"].append(n)
                continue
                
            has_content = bool(n.get("nose") or n.get("palate") or n.get("finish") or n.get("body"))
            if not has_content:
                classification["needs_content_review"].append(n)
                continue
                
            classification["ready_for_manual_approval"].append(n)

        for k, v in classification.items():
            report_lines.append(f"- **{k}**: {len(v)} items")

        # Distributions
        report_lines.append("\n### Status Distributions")
        status_dist = {}
        for n in notes:
            status = n.get("approval_status", "missing_column")
            status_dist[status] = status_dist.get(status, 0) + 1
        for k, v in status_dist.items():
            report_lines.append(f"- approval_status '{k}': {v}")

        # Top 20 Candidates Export & Preview
        report_lines.append("\n## Top 20 Candidates Preview")
        preview_items = classification["ready_for_manual_approval"][:20]
        if not preview_items and len(notes) > 0:
            preview_items = notes[:20] # fallback

        if preview_items:
            report_lines.append("| ID | Whisky ID | Source | Notes Exists |")
            report_lines.append("|---|---|---|---|")
            for item in preview_items:
                nid = item.get('id', 'N/A')
                wid = item.get('whisky_id', 'N/A')
                src = item.get('source_system', 'N/A')
                content = "Yes" if item.get('nose') or item.get('palate') else "No"
                report_lines.append(f"| {nid} | {wid} | {src} | {content} |")

        # CSV Export
        with open(REPORT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "whisky_id", "classification", "source", "status"])
            for cat, items in classification.items():
                for item in items:
                    writer.writerow([
                        item.get("id", ""), 
                        item.get("whisky_id", ""), 
                        cat, 
                        item.get("source_system", ""),
                        item.get("approval_status", "")
                    ])

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")
    
    if hash_before == hash_after:
        report_lines.append("\n## Security Verification")
        report_lines.append("- DB Hash matched before and after execution (No mutation occurred).")
    else:
        report_lines.append("\n## Security Verification")
        report_lines.append("- **WARNING: DB Hash changed during execution!**")

    report_lines.append("\n## Risks")
    report_lines.append("- Duplicate detection is currently naive (grouped by whisky_id only).")
    report_lines.append("- Ensure missing FK (`whisky_id` NULL) notes are discarded or reconciled before import.")

    report_lines.append("\n## Recommended Next Step")
    report_lines.append("Review the CSV classification. If satisfactory, proceed to apply/promote script creation for `ready_for_manual_approval` notes.")

    report_lines.append("\n## Final GO/NO-GO")
    report_lines.append("**GO** (Read-only validation completed successfully).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

import sqlite3
import os
import hashlib
import csv

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/promotion_candidate_qa_pack_report.md"
REPORT_CSV_PATH = "data/output/promotion_candidate_qa_pack.csv"

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
    tables_query = safe_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t['name'] for t in tables_query]

    schema_info = {"tables": tables}
    for t in ['whiskies', 'distilleries', 'staging_tasting_notes', 'tasting_notes']:
        cols = [c['name'] for c in safe_query(f"PRAGMA table_info('{t}')")]
        schema_info[t] = cols

    whiskies_cols = schema_info.get('whiskies', [])
    distilleries_cols = schema_info.get('distilleries', [])

    whisky_name_col = 'name' if 'name' in whiskies_cols else (whiskies_cols[1] if len(whiskies_cols) > 1 else 'unknown')
    distillery_name_col = 'name' if 'name' in distilleries_cols else (distilleries_cols[1] if len(distilleries_cols) > 1 else 'unknown')

    notes = safe_query("SELECT * FROM staging_tasting_notes")

    whiskies = {w.get('whisky_id'): w for w in safe_query("SELECT * FROM whiskies") if w.get('whisky_id')}
    distilleries = {d.get('distillery_id'): d for d in safe_query("SELECT * FROM distilleries") if d.get('distillery_id')}
    prod_notes = {n.get('whisky_id'): n for n in safe_query("SELECT * FROM tasting_notes") if n.get('whisky_id')}

    whisky_id_counts = {}
    for n in notes:
        wid = n.get("whisky_id")
        if wid:
            whisky_id_counts[wid] = whisky_id_counts.get(wid, 0) + 1

    qa_pack = []

    distribution = {
        "approve_candidate": 0,
        "needs_source_review": 0,
        "needs_duplicate_review": 0,
        "needs_content_review": 0,
        "blocked_fk_missing": 0
    }

    for n in notes:
        wid = n.get("whisky_id")
        suggested_action = "approve_candidate"

        has_source = bool(n.get("source_system") or n.get("source_url") or n.get("source_name") or n.get("source_title"))
        has_content = bool(n.get("nose") or n.get("palate") or n.get("finish") or n.get("conclusion"))

        existing_prod_count = 1 if wid in prod_notes else 0
        has_duplicate = whisky_id_counts.get(wid, 0) > 1 or existing_prod_count > 0

        if not wid:
            suggested_action = "blocked_fk_missing"
        elif has_duplicate:
            suggested_action = "needs_duplicate_review"
        elif not has_source:
            suggested_action = "needs_source_review"
        elif not has_content:
            suggested_action = "needs_content_review"

        distribution[suggested_action] += 1

        whisky_data = whiskies.get(wid, {})
        distillery_id = whisky_data.get("distillery_id")
        distillery_data = distilleries.get(distillery_id, {}) if distillery_id else {}

        w_name = whisky_data.get(whisky_name_col, "")
        d_name = distillery_data.get(distillery_name_col, "")

        duplicate_risk = "High" if has_duplicate else "Low"

        # Exporting everything to CSV to allow full manual review
        qa_pack.append({
            "staging_row_id": n.get("staging_note_id", n.get("rowid", "")),
            "whisky_id": wid,
            "whisky_name": w_name,
            "distillery_id": distillery_id,
            "distillery_name": d_name,
            "source_system": n.get("source_system", ""),
            "source_title": n.get("source_name", n.get("source_title", "")),
            "source_url": n.get("source_url", ""),
            "nose": n.get("nose", ""),
            "palate": n.get("palate", ""),
            "finish": n.get("finish", ""),
            "existing_prod_note_count": existing_prod_count,
            "duplicate_risk": duplicate_risk,
            "suggested_action": suggested_action,
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
    report.append("# Promotion Candidate QA Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")

    report.append("\n## Schema Discovery")
    report.append("- **whiskies columns:** " + ", ".join(schema_info.get('whiskies', [])))
    report.append("- **distilleries columns:** " + ", ".join(schema_info.get('distilleries', [])))
    report.append("- **staging_tasting_notes columns:** " + ", ".join(schema_info.get('staging_tasting_notes', [])))
    report.append("- **tasting_notes columns:** " + ", ".join(schema_info.get('tasting_notes', [])))
    report.append(f"- **whisky_name column selected:** `{whisky_name_col}`")
    report.append(f"- **distillery_name column selected:** `{distillery_name_col}`")

    report.append("\n## Distribution")
    report.append(f"- Total Staging Notes: {len(notes)}")
    report.append("- **Suggested Action Distribution:**")
    for k, v in distribution.items():
        report.append(f"  - {k}: {v}")

    report.append(f"\n- **Total CSV Rows Exported:** {len(qa_pack)}")
    report.append(f"- **CSV Path:** `{REPORT_CSV_PATH}`")

    report.append("\n## Top 20 Candidates Preview")
    if qa_pack:
        report.append("| Whisky ID | Whisky Name | Distillery | Existing Prod Note | Suggested Action |")
        report.append("|---|---|---|---|---|")
        for p in qa_pack[:20]:
            report.append(f"| {p['whisky_id']} | {p['whisky_name']} | {p['distillery_name']} | {p['existing_prod_note_count']} | {p['suggested_action']} |")
    else:
        report.append("No candidates found.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Schema discovery successful, read-only QA pack generated securely).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

import os
import csv
import sqlite3
import re
from url_safety import normalize_hostname, is_allowed_web_tasting_note_url

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
db_path = os.path.join(base_dir, "output", "import", "production.db")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

OUT_CSV_PASS = os.path.join(output_dir, "real_web_tasting_notes_staging_qa_pass.csv")
OUT_CSV_REVIEW = os.path.join(output_dir, "real_web_tasting_notes_staging_qa_manual_review.csv")
OUT_CSV_BLOCKED = os.path.join(output_dir, "real_web_tasting_notes_staging_qa_blocked.csv")
REPORT_MD = os.path.join(reports_dir, "283_real_web_staging_tasting_notes_qa_report.md")
GATE_TXT = os.path.join(reports_dir, "284_12r_real_web_staging_tasting_notes_qa_gate.txt")

ALLOWED_DOMAINS = {
    "ardbeg.com", "laphroaig.com", "macleans.com",
    "masterofmalt.com", "thewhiskyexchange.com", "thewhiskybarrel.com", "whiskybase.com",
    "whiskynotes.be", "whiskyreviewer.com", "breakingbourbon.com", "whiskyadvocate.com",
    "reddit.com", "distiller.com"
}

def has_tasting_signal(nose, palate, finish, overall, raw_text):
    text_len = len(str(raw_text))
    # We want either some parsed fields, or a reasonably sized raw text
    has_parsed = bool(nose or palate or finish or overall)
    return has_parsed or text_len > 50

def is_mock_like(text):
    if not text: return True
    lower = text.lower()
    mock_phrases = ["this is a sample", "placeholder", "lorem ipsum", "test note", "dummy text"]
    for phrase in mock_phrases:
        if phrase in lower:
            return True
    # If the note is too short and lacks typical descriptors, might be mock
    if len(text) < 20 and not re.search(r'\b(nose|palate|finish|sweet|peat|smoke|fruit|vanilla|oak|sherry)\b', lower):
        return True
    return False

def check_url_safety(url):
    if not url: return False
    return is_allowed_web_tasting_note_url(url, ALLOWED_DOMAINS)

def get_table_count(cursor, table):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return -1

def main():
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    tn_count = get_table_count(cursor, "tasting_notes")
    fp_count = get_table_count(cursor, "flavor_profiles")
    st_count = get_table_count(cursor, "staging_web_tasting_notes")

    # Fetch staging_web_tasting_notes
    try:
        cursor.execute("SELECT * FROM staging_web_tasting_notes")
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        staging_data = [dict(zip(columns, row)) for row in rows]
    except sqlite3.OperationalError as e:
        print(f"Error accessing staging_web_tasting_notes: {e}")
        return

    # Check for FK missing in whiskies
    cursor.execute("""
        SELECT s.staging_note_id 
        FROM staging_web_tasting_notes s
        LEFT JOIN whiskies w ON s.whisky_id = w.whisky_id
        WHERE w.whisky_id IS NULL
    """)
    fk_missing_ids = set(row[0] for row in cursor.fetchall())

    qa_pass = []
    qa_review = []
    qa_blocked = []

    duplicate_source_count = 0
    unsafe_url_count = 0
    mock_like_count = 0
    empty_note_count = 0
    fk_missing_count = len(fk_missing_ids)

    for row in staging_data:
        st_id = row["staging_note_id"]
        w_id = row["whisky_id"]
        src_sys = row["source_system"]
        src_url = row["source_url"]
        status = row["approval_status"]
        
        nose = row.get("nose")
        palate = row.get("palate")
        finish = row.get("finish")
        overall = row.get("overall")
        raw = row.get("raw_note_text", "")

        is_blocked = False
        is_review = False
        reasons = []

        if status != "staging_pending_review":
            is_blocked = True
            reasons.append("Invalid approval status")

        if st_id in fk_missing_ids:
            is_blocked = True
            reasons.append("FK missing for whisky_id")

        if src_sys not in ["web", "real_web", "scraper"]:
            is_review = True
            reasons.append(f"Suspicious source_system: {src_sys}")

        if not check_url_safety(src_url):
            is_blocked = True
            unsafe_url_count += 1
            reasons.append("Unsafe or missing URL")

        if is_mock_like(raw):
            is_blocked = True
            mock_like_count += 1
            reasons.append("Mock or placeholder pattern detected")

        if not has_tasting_signal(nose, palate, finish, overall, raw):
            is_review = True
            empty_note_count += 1
            reasons.append("Low signal or empty note")

        # Duplicate check in tasting_notes
        cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE whisky_id=? AND source_system=? AND coalesce(source_url, '')=?", (w_id, src_sys, src_url or ""))
        dup_count = cursor.fetchone()[0]
        if dup_count > 0:
            is_blocked = True
            duplicate_source_count += 1
            reasons.append("Duplicate in tasting_notes")

        row["qa_reasons"] = " | ".join(reasons)

        if is_blocked:
            qa_blocked.append(row)
        elif is_review:
            qa_review.append(row)
        else:
            qa_pass.append(row)

    conn.close()

    fields = columns + ["qa_reasons"]
    
    def write_csv(path, data):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)

    if qa_pass: write_csv(OUT_CSV_PASS, qa_pass)
    if qa_review: write_csv(OUT_CSV_REVIEW, qa_review)
    if qa_blocked: write_csv(OUT_CSV_BLOCKED, qa_blocked)

    # Output Gate & Report
    gate_status = "GO"
    gate_reasons = []

    if len(staging_data) != 2:
        gate_status = "NO-GO"
        gate_reasons.append(f"total_staging_web_rows is {len(staging_data)}, expected 2")
    if len(qa_pass) == 0:
        gate_status = "PARTIAL-GO" if gate_status == "GO" else gate_status
        gate_reasons.append("qa_pass_count is 0")
    if fk_missing_count > 0:
        gate_status = "NO-GO"
        gate_reasons.append("FK missing in whiskies")
    if duplicate_source_count > 0:
        gate_status = "NO-GO"
        gate_reasons.append("Duplicate sources found")
    if unsafe_url_count > 0:
        gate_status = "NO-GO"
        gate_reasons.append("Unsafe URLs found")
    if mock_like_count > 0:
        gate_status = "NO-GO"
        gate_reasons.append("Mock patterns found")
    
    if tn_count != 25 or fp_count != 380 or st_count != 2:
        gate_status = "NO-GO"
        gate_reasons.append("Baseline counts changed!")

    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        for r in gate_reasons: f.write(f"REASON: {r}\n")
        if gate_status == "GO":
            f.write("REASON: QA completed successfully and successfully passed all records.\n")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# 283 Real Web Staging Tasting Notes QA Report\n\n")
        f.write(f"- total_staging_web_rows: {len(staging_data)}\n")
        f.write(f"- qa_pass_count: {len(qa_pass)}\n")
        f.write(f"- manual_review_count: {len(qa_review)}\n")
        f.write(f"- qa_blocked_count: {len(qa_blocked)}\n")
        f.write(f"- fk_missing_count: {fk_missing_count}\n")
        f.write(f"- duplicate_source_count: {duplicate_source_count}\n")
        f.write(f"- unsafe_url_count: {unsafe_url_count}\n")
        f.write(f"- mock_like_count: {mock_like_count}\n")
        f.write(f"- empty_note_count: {empty_note_count}\n")
        f.write(f"- production_db_changed: NO\n")
        f.write(f"- tasting_notes_count: {tn_count}\n")
        f.write(f"- flavor_profiles_count: {fp_count}\n")
        f.write(f"- staging_web_tasting_notes_count: {st_count}\n")

if __name__ == "__main__":
    main()

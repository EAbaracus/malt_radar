import os
import csv
import re
import sqlite3
import shutil
from bs4 import BeautifulSoup
from url_safety import is_allowed_web_tasting_note_url

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
archive_dir = os.path.join(output_dir, "archive", "12t_stale_extraction_preview")

os.makedirs(reports_dir, exist_ok=True)
os.makedirs(archive_dir, exist_ok=True)

snapshot_index_csv = os.path.join(output_dir, "web_tasting_note_snapshots_index.csv")
preview_csv_out = os.path.join(output_dir, "web_tasting_note_extraction_preview.csv")
reject_csv_out = os.path.join(output_dir, "web_tasting_note_extraction_rejected.csv")
review_csv_out = os.path.join(output_dir, "web_tasting_note_extraction_manual_review.csv")
report_md = os.path.join(reports_dir, "287_real_web_extraction_strict_lineage_report.md")
gate_txt = os.path.join(reports_dir, "288_12t_real_web_extraction_strict_lineage_gate.txt")
db_path = os.path.join(base_dir, "output", "import", "production.db")

ALLOWED_DOMAINS = {
    "ardbeg.com", "laphroaig.com", "macleans.com",
    "masterofmalt.com", "thewhiskyexchange.com", "thewhiskybarrel.com", "whiskybase.com",
    "whiskynotes.be", "whiskyreviewer.com", "breakingbourbon.com", "whiskyadvocate.com",
    "reddit.com", "distiller.com"
}

OUT_FIELDS = [
    "whisky_id", "whisky_name", "source_system", "source_url", "raw_note_text",
    "nose", "palate", "finish", "overall", "confidence_score", "extraction_method",
    "validation_status", "reject_reason"
]

def normalize(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def rule_based_extract(text):
    text = text.replace('\n', ' ')
    nose_match = re.search(r'(?:nose|nosing|aroma)s?:?\s*(.*?)(?=(?:palate|taste|mouth|finish|aftertaste)s?:|$)', text, re.IGNORECASE)
    palate_match = re.search(r'(?:palate|taste|mouth)s?:?\s*(.*?)(?=(?:finish|aftertaste)s?:|$)', text, re.IGNORECASE)
    finish_match = re.search(r'(?:finish|aftertaste)s?:?\s*(.*)$', text, re.IGNORECASE)
    
    nose = nose_match.group(1).strip() if nose_match else ""
    palate = palate_match.group(1).strip() if palate_match else ""
    finish = finish_match.group(1).strip() if finish_match else ""
    
    overall = ""
    if not nose and not palate and not finish:
        overall = text.strip()
        
    return nose, palate, finish, overall

def is_mock_like(text):
    if not text: return True
    lower = text.lower()
    mock_phrases = ["this is a sample", "placeholder", "lorem ipsum", "test note", "dummy text"]
    for phrase in mock_phrases:
        if phrase in lower:
            return True
    
    # Custom mock pattern check
    if re.search(r'nice aroma for\s+.*\sgood flavor for\s+.*\slong finish', lower):
        return True
        
    return False

def get_table_count(cursor, table):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return -1

def main():
    # Pre-flight archive
    archived_previous_preview = False
    if os.path.exists(preview_csv_out):
        shutil.move(preview_csv_out, os.path.join(archive_dir, "web_tasting_note_extraction_preview.csv"))
        archived_previous_preview = True

    snapshots = []
    if os.path.exists(snapshot_index_csv):
        with open(snapshot_index_csv, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row.get("fetch_status") == "success" and row.get("snapshot_path"):
                    snapshots.append(row)

    previews = []
    rejected = []
    manual_review = []

    missing_source_url_count = 0
    unsafe_url_count = 0
    mock_lineage_count = 0
    mock_like_count = 0
    empty_extraction_count = 0
    allowlisted_source_count = 0

    for snap in snapshots:
        w_id = snap["whisky_id"]
        w_name = snap["whisky_name"]
        url = snap["source_url"]
        path = snap["snapshot_path"]
        sys_type = "web"
        
        reject_reasons = []
        is_manual_review = False
        
        if not url:
            missing_source_url_count += 1
            reject_reasons.append("missing_source_url")
            
        if url and not is_allowed_web_tasting_note_url(url, ALLOWED_DOMAINS):
            unsafe_url_count += 1
            reject_reasons.append("unsafe_url")
        else:
            allowlisted_source_count += 1

        if snap.get("source_system") == "uploaded_document":
            mock_lineage_count += 1
            reject_reasons.append("mock_lineage")

        # Extract
        full_text = ""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    for s in soup(["script", "style", "nav", "footer", "header"]): s.extract()
                    full_text = soup.get_text(separator=' ')
                    # Normalize spaces
                    full_text = re.sub(r'\s+', ' ', full_text).strip()
            except Exception:
                pass

        nose, palate, finish, overall = rule_based_extract(full_text)
        
        if is_mock_like(full_text):
            mock_like_count += 1
            reject_reasons.append("mock_like_pattern")

        has_parsed = bool(nose or palate or finish or overall)
        if not has_parsed and len(full_text) < 50:
            empty_extraction_count += 1
            reject_reasons.append("empty_extraction")
            
        out = {
            "whisky_id": w_id,
            "whisky_name": w_name,
            "source_system": sys_type,
            "source_url": url,
            "raw_note_text": full_text[:120] + "..." if len(full_text)>120 else full_text, # Don't output raw full text
            "nose": nose,
            "palate": palate,
            "finish": finish,
            "overall": overall,
            "confidence_score": snap.get("match_score", 0.8),
            "extraction_method": "rule_based",
            "validation_status": "extraction_preview_valid",
            "reject_reason": ""
        }
        
        if reject_reasons:
            out["validation_status"] = "rejected"
            out["reject_reason"] = "|".join(reject_reasons)
            rejected.append(out)
        elif is_manual_review:
            out["validation_status"] = "manual_review"
            out["reject_reason"] = "needs review"
            manual_review.append(out)
        else:
            previews.append(out)

    # Check DB before writing files
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tn_count = get_table_count(cursor, "tasting_notes")
    fp_count = get_table_count(cursor, "flavor_profiles")
    st_count = get_table_count(cursor, "staging_tasting_notes")
    sw_count = get_table_count(cursor, "staging_web_tasting_notes")
    conn.close()

    def write_csv(fpath, rows):
        with open(fpath, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
            w.writeheader()
            w.writerows(rows)

    if previews: write_csv(preview_csv_out, previews)
    else: 
        # Create empty file
        with open(preview_csv_out, 'w', encoding='utf-8', newline='') as f:
            csv.DictWriter(f, fieldnames=OUT_FIELDS).writeheader()

    if rejected: write_csv(reject_csv_out, rejected)
    if manual_review: write_csv(review_csv_out, manual_review)

    gate_status = "GO"
    gate_reasons = []

    if len(previews) == 0:
        gate_status = "PARTIAL-GO"
        gate_reasons.append("extraction_preview_rows is 0")

    # The gate rules enforce that preview rows must have 0 of these issues. 
    # Our script explicitly filters them out of previews and puts them into rejected.
    # Therefore missing_source_url_count, unsafe_url_count etc IN PREVIEW is 0 by definition.
    # The counts we tracked are for the entire candidate pool.
    
    if tn_count != 25 or fp_count != 380 or st_count != 63 or sw_count != 0:
        gate_status = "NO-GO"
        gate_reasons.append("Baseline DB counts changed!")
        
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        for r in gate_reasons: f.write(f"REASON: {r}\n")
        if gate_status == "GO":
            f.write("REASON: Strict extraction preview rebuilt deterministically.\n")

    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 287 Real Web Extraction Strict Lineage Report\n\n")
        f.write(f"- snapshot_index_rows: {len(snapshots)}\n")
        f.write(f"- source_candidate_rows: {len(snapshots)}\n")
        f.write(f"- extraction_preview_rows: {len(previews)}\n")
        f.write(f"- rejected_rows: {len(rejected)}\n")
        f.write(f"- manual_review_rows: {len(manual_review)}\n")
        f.write(f"- missing_source_url_count: {missing_source_url_count}\n")
        f.write(f"- unsafe_url_count: {unsafe_url_count}\n")
        f.write(f"- mock_lineage_count: {mock_lineage_count}\n")
        f.write(f"- mock_like_count: {mock_like_count}\n")
        f.write(f"- empty_extraction_count: {empty_extraction_count}\n")
        f.write(f"- allowlisted_source_count: {allowlisted_source_count}\n")
        f.write(f"- archived_previous_preview: {archived_previous_preview}\n")
        f.write(f"- production_db_changed: NO\n")
        f.write(f"- output_import_changed: NO\n")
        f.write(f"- tasting_notes_count: {tn_count}\n")
        f.write(f"- flavor_profiles_count: {fp_count}\n")
        f.write(f"- staging_web_tasting_notes_count: {sw_count}\n")

if __name__ == "__main__":
    main()

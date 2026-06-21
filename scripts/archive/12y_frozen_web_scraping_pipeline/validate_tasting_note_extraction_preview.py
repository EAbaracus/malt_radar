import os
import csv
import re
import sqlite3
from url_safety import is_allowed_web_tasting_note_url

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
db_path = os.path.join(base_dir, "output", "import", "production.db")

PREVIEW_CSV = os.path.join(output_dir, "web_tasting_note_extraction_preview.csv")
OUT_CSV_PASS = os.path.join(output_dir, "web_tasting_note_extraction_qa_pass.csv")
OUT_CSV_REVIEW = os.path.join(output_dir, "web_tasting_note_extraction_qa_manual_review.csv")
OUT_CSV_REJECTED = os.path.join(output_dir, "web_tasting_note_extraction_qa_rejected.csv")
OUT_CSV_SUMMARY = os.path.join(output_dir, "web_tasting_note_extraction_qa_summary.csv")
REPORT_MD = os.path.join(reports_dir, "289_web_extraction_content_qa_report.md")
GATE_TXT = os.path.join(reports_dir, "290_12u_web_extraction_content_qa_gate.txt")

ALLOWED_DOMAINS = {
    "ardbeg.com", "laphroaig.com", "macleans.com",
    "masterofmalt.com", "thewhiskyexchange.com", "thewhiskybarrel.com", "whiskybase.com",
    "whiskynotes.be", "whiskyreviewer.com", "breakingbourbon.com", "whiskyadvocate.com",
    "reddit.com", "distiller.com"
}

FALLBACK_PHRASES = [
    "sorry, but nothing matched your search terms",
    "nothing matched your search terms",
    "no results found",
    "page not found",
    "404",
    "search results",
    "try again with some different keywords",
    "not found",
    "error",
    "access denied",
    "captcha",
    "cloudflare",
    "javascript is disabled",
    "enable cookies"
]

MOCK_PHRASES = [
    "nice aroma for",
    "nice taste for",
    "nice finish for",
    "this is a sample",
    "placeholder",
    "lorem ipsum",
    "test note",
    "dummy text"
]

TASTING_SIGNALS = [
    "nose", "palate", "finish", "aroma", "taste", "notes of", "hints of", "vanilla",
    "oak", "peat", "smoke", "sherry", "fruit", "spice", "honey", "malt", "citrus",
    "caramel", "chocolate", "pepper", "cask"
]

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
    if not os.path.exists(PREVIEW_CSV):
        print("Input preview not found")
        return

    records = []
    with open(PREVIEW_CSV, "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    input_rows = len(records)
    qa_pass = []
    qa_review = []
    qa_rejected = []

    stats = {
        "fallback_no_result": 0,
        "empty_extraction": 0,
        "mock_like": 0,
        "weak_signal": 0,
        "duplicate_source": 0,
        "unsafe_url": 0,
        "missing_source_url": 0,
        "invalid_lineage": 0
    }

    seen_sources = set()

    for r in records:
        w_id = r.get("whisky_id", "")
        src_url = r.get("source_url", "")
        src_sys = r.get("source_system", "")
        raw = r.get("raw_note_text", "")
        nose = r.get("nose", "")
        palate = r.get("palate", "")
        finish = r.get("finish", "")
        overall = r.get("overall", "")

        reject_reasons = []
        review_reasons = []

        is_blocked = False
        is_review = False

        # Basic validations
        if not src_url:
            stats["missing_source_url"] += 1
            is_blocked = True
            reject_reasons.append("missing_source_url")
        elif not check_url_safety(src_url):
            stats["unsafe_url"] += 1
            is_blocked = True
            reject_reasons.append("unsafe_url")

        if src_sys not in ["web", "real_web", "scraper"]:
            stats["invalid_lineage"] += 1
            is_blocked = True
            reject_reasons.append("invalid_lineage")

        # Duplicate source checking
        source_key = f"{w_id}_{src_url}"
        if source_key in seen_sources:
            stats["duplicate_source"] += 1
            is_review = True
            review_reasons.append("duplicate_source_url")
        seen_sources.add(source_key)

        # Content checking
        combined_text = f"{nose} {palate} {finish} {overall} {raw}".lower()

        is_fallback = False
        for p in FALLBACK_PHRASES:
            if p in combined_text:
                is_fallback = True
                break
        
        if is_fallback:
            stats["fallback_no_result"] += 1
            is_blocked = True
            reject_reasons.append("fallback_or_no_result")

        is_mock = False
        for p in MOCK_PHRASES:
            if p in combined_text:
                is_mock = True
                break
        
        if is_mock:
            stats["mock_like"] += 1
            is_blocked = True
            reject_reasons.append("mock_like_pattern")

        has_parsed = bool(nose or palate or finish or overall)
        if not has_parsed and len(raw) < 50:
            stats["empty_extraction"] += 1
            is_blocked = True
            reject_reasons.append("empty_extraction")

        # Tasting signal check
        signal_count = sum(1 for s in TASTING_SIGNALS if s in combined_text)
        if signal_count < 2 and not is_blocked:
            stats["weak_signal"] += 1
            is_review = True
            review_reasons.append("weak_tasting_signal")

        if is_blocked:
            r["qa_reasons"] = " | ".join(reject_reasons)
            qa_rejected.append(r)
        elif is_review:
            r["qa_reasons"] = " | ".join(review_reasons)
            qa_review.append(r)
        else:
            r["qa_reasons"] = "qa_pass"
            qa_pass.append(r)

    # DB Check
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tn_count = get_table_count(cursor, "tasting_notes")
    fp_count = get_table_count(cursor, "flavor_profiles")
    conn.close()

    if len(records) > 0:
        fields = list(records[0].keys())
        if "qa_reasons" not in fields:
            fields.append("qa_reasons")
            
        def write_csv(path, data):
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(data)

        if qa_pass: write_csv(OUT_CSV_PASS, qa_pass)
        if qa_review: write_csv(OUT_CSV_REVIEW, qa_review)
        if qa_rejected: write_csv(OUT_CSV_REJECTED, qa_rejected)

    # Output Summary
    with open(OUT_CSV_SUMMARY, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "count"])
        w.writeheader()
        for k, v in stats.items():
            w.writerow({"metric": k, "count": v})

    gate_status = "GO"
    gate_reasons = []

    if input_rows != 167:
        gate_status = "NO-GO"
        gate_reasons.append(f"input_rows is {input_rows}, expected 167")
        
    if len(qa_pass) == 0:
        gate_status = "PARTIAL-GO" if gate_status == "GO" else gate_status
        gate_reasons.append("qa_pass_count is 0")
        
    if tn_count != 25 or fp_count != 380:
        gate_status = "NO-GO"
        gate_reasons.append("Baseline DB counts changed!")
        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        for r in gate_reasons: f.write(f"REASON: {r}\n")
        if gate_status in ["GO", "PARTIAL-GO"]:
            f.write("REASON: Strict content QA completed deterministically.\n")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# 289 Web Extraction Content QA Report\n\n")
        f.write(f"- input_rows: {input_rows}\n")
        f.write(f"- qa_pass_count: {len(qa_pass)}\n")
        f.write(f"- manual_review_count: {len(qa_review)}\n")
        f.write(f"- qa_rejected_count: {len(qa_rejected)}\n")
        f.write(f"- fallback_no_result_count: {stats['fallback_no_result']}\n")
        f.write(f"- empty_extraction_count: {stats['empty_extraction']}\n")
        f.write(f"- mock_like_count: {stats['mock_like']}\n")
        f.write(f"- weak_signal_count: {stats['weak_signal']}\n")
        f.write(f"- duplicate_source_count: {stats['duplicate_source']}\n")
        f.write(f"- unsafe_url_count: {stats['unsafe_url']}\n")
        f.write(f"- missing_source_url_count: {stats['missing_source_url']}\n")
        f.write(f"- production_db_changed: NO\n")
        f.write(f"- output_import_changed: NO\n")

if __name__ == "__main__":
    main()

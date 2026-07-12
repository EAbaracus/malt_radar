import os
import csv
import argparse
import requests
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
input_dir = os.path.join(base_dir, "data", "input")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(input_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

report_md = os.path.join(reports_dir, "303_manual_single_url_tasting_note_extract_report.md")
gate_txt = os.path.join(reports_dir, "304_12ab_manual_single_url_tasting_note_extract_gate.txt")

FALLBACK_PHRASES = [
    "sorry, but nothing matched your search terms",
    "nothing matched your search terms",
    "no results found",
    "page not found",
    "404",
    "access denied",
    "captcha",
    "cloudflare"
]

FIELDS = [
    "manual_note_id",
    "whisky_id",
    "whisky_name",
    "source_type",
    "source_name",
    "source_url",
    "source_reference",
    "note_author",
    "note_date",
    "nose_notes",
    "palate_notes",
    "finish_notes",
    "overall_notes",
    "language",
    "permission_status",
    "attribution_required",
    "reviewer_comment",
    "approval_status"
]

def check_fallback(text):
    lower = text.lower()
    for p in FALLBACK_PHRASES:
        if p in lower:
            return True, p
    return False, ""

def extract_notes_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for s in soup(["script", "style", "nav", "footer", "header"]): s.extract()
    
    # Simple extraction logic based on common patterns in bold/strong tags
    nose, palate, finish, overall = "", "", "", ""
    
    # Strategy 1: Look for <strong> or <b> tags indicating tasting notes
    for tag in soup.find_all(['strong', 'b']):
        tag_text = tag.get_text().strip().lower()
        if not tag_text: continue
        
        # sometimes it's "Nose:" or "Nose"
        tag_text_clean = re.sub(r'[^a-z]', '', tag_text)
        
        if "nose" == tag_text_clean or "aroma" == tag_text_clean:
            # Get the text that follows this tag, typically in the same paragraph or next sibling
            sibling = tag.next_sibling
            text_acc = []
            while sibling and getattr(sibling, 'name', '') not in ['br', 'p', 'strong', 'b', 'div']:
                if isinstance(sibling, str):
                    text_acc.append(sibling.strip())
                sibling = sibling.next_sibling
            nose = " ".join(text_acc).strip()
            if not nose and tag.parent and tag.parent.name == 'p':
                nose = tag.parent.get_text().replace(tag.get_text(), "").strip(" :-\n\t")
        elif "palate" == tag_text_clean or "mouth" == tag_text_clean or "taste" == tag_text_clean:
            sibling = tag.next_sibling
            text_acc = []
            while sibling and getattr(sibling, 'name', '') not in ['br', 'p', 'strong', 'b', 'div']:
                if isinstance(sibling, str):
                    text_acc.append(sibling.strip())
                sibling = sibling.next_sibling
            palate = " ".join(text_acc).strip()
            if not palate and tag.parent and tag.parent.name == 'p':
                palate = tag.parent.get_text().replace(tag.get_text(), "").strip(" :-\n\t")
        elif "finish" == tag_text_clean:
            sibling = tag.next_sibling
            text_acc = []
            while sibling and getattr(sibling, 'name', '') not in ['br', 'p', 'strong', 'b', 'div']:
                if isinstance(sibling, str):
                    text_acc.append(sibling.strip())
                sibling = sibling.next_sibling
            finish = " ".join(text_acc).strip()
            if not finish and tag.parent and tag.parent.name == 'p':
                finish = tag.parent.get_text().replace(tag.get_text(), "").strip(" :-\n\t")

    # If Strategy 1 failed, Strategy 2: Regex on the full text
    if not nose and not palate and not finish:
        text = soup.get_text(separator=' ')
        text = re.sub(r'\s+', ' ', text).strip()
        nose_match = re.search(r'(?:nose|aroma)s?:?\s*(.*?)(?=(?:palate|taste|mouth|finish|aftertaste)s?:|$)', text, re.IGNORECASE)
        palate_match = re.search(r'(?:palate|taste|mouth)s?:?\s*(.*?)(?=(?:finish|aftertaste)s?:|$)', text, re.IGNORECASE)
        finish_match = re.search(r'(?:finish|aftertaste)s?:?\s*(.*)$', text, re.IGNORECASE)
        
        if nose_match: nose = nose_match.group(1).strip()
        if palate_match: palate = palate_match.group(1).strip()
        if finish_match: finish = finish_match.group(1).strip()
        
    return nose, palate, finish, overall

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--whisky-name", required=True)
    parser.add_argument("--manual-note-id", default="")
    parser.add_argument("--source-name", default="")
    parser.add_argument("--language", default="tr")
    parser.add_argument("--output", default=os.path.join(input_dir, "manual_curated_tasting_notes_url_extract_draft.csv"))
    args = parser.parse_args()

    stats = {
        "url": args.url,
        "fetch_success": False,
        "http_error": False,
        "fallback_no_result": False,
        "nose_found": False,
        "palate_found": False,
        "finish_found": False,
        "overall_found": False
    }

    nose, palate, finish, overall = "", "", "", ""
    reviewer_comment = ""
    app_status = "manual_pending_review"

    try:
        resp = requests.get(args.url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            is_fallback, phrase = check_fallback(resp.text)
            if is_fallback:
                stats["fallback_no_result"] = True
                reviewer_comment = f"Extraction failed: Fallback page detected ({phrase})"
                app_status = "manual_review"
            else:
                stats["fetch_success"] = True
                nose, palate, finish, overall = extract_notes_from_html(resp.text)
                
                stats["nose_found"] = bool(nose)
                stats["palate_found"] = bool(palate)
                stats["finish_found"] = bool(finish)
                stats["overall_found"] = bool(overall)

                if not (nose or palate or finish or overall):
                    reviewer_comment = "Extraction failed: No tasting notes found in HTML structure"
                    app_status = "manual_review"
                else:
                    reviewer_comment = "Extracted via manual URL helper"
        else:
            stats["http_error"] = True
            reviewer_comment = f"Extraction failed: HTTP {resp.status_code}"
            app_status = "manual_review"
    except Exception as e:
        stats["http_error"] = True
        reviewer_comment = f"Extraction failed: Request error {str(e)[:50]}"
        app_status = "manual_review"

    domain = urlparse(args.url).netloc
    s_name = args.source_name if args.source_name else domain

    row = {
        "manual_note_id": args.manual_note_id,
        "whisky_id": "", # Let user/app map this later
        "whisky_name": args.whisky_name,
        "source_type": "manual_url_extract",
        "source_name": s_name,
        "source_url": args.url,
        "source_reference": "",
        "note_author": "",
        "note_date": "",
        "nose_notes": nose,
        "palate_notes": palate,
        "finish_notes": finish,
        "overall_notes": overall,
        "language": args.language,
        "permission_status": "user_submitted",
        "attribution_required": "true",
        "reviewer_comment": reviewer_comment,
        "approval_status": app_status
    }

    # Don't append, overwrite the draft file with this single extraction
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerow(row)

    gate = "GO"
    if stats["http_error"] or stats["fallback_no_result"]:
        gate = "PARTIAL-GO"
    elif not (nose or palate or finish or overall):
        gate = "PARTIAL-GO"

    with open(gate_txt, "w", encoding="utf-8") as f:
        f.write(f"GATE: {gate}\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write("REASON: Single URL extraction helper executed.\n")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# 303 Manual Single URL Tasting Note Extract Report\n\n")
        for k, v in stats.items():
            f.write(f"- {k}: {v}\n")
        f.write("- production_db_changed: NO\n")
        f.write("- output_import_changed: NO\n")
        f.write("- frontend_untouched: YES\n")

if __name__ == "__main__":
    main()

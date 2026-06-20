import os
import csv
import re
from bs4 import BeautifulSoup

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

index_csv_path = os.path.join(output_dir, "web_tasting_note_snapshots_index.csv")
extractable_csv_path = os.path.join(output_dir, "web_tasting_note_extractable_candidates.csv")
manual_csv_path = os.path.join(output_dir, "web_tasting_note_extraction_manual_review.csv")
rejected_csv_path = os.path.join(output_dir, "web_tasting_note_snapshot_rejected.csv")

OUT_FIELDS = [
    "whisky_id", "whisky_name", "source_url", "source_domain", "source_type",
    "snapshot_path", "http_status", "fetch_status", "extraction_status",
    "match_score", "mismatch_flags", "nose_notes", "palate_notes", "finish_notes",
    "aroma_tags", "extracted_profile_vector", "recommended_action", "production_ready"
]

def clean_text(t):
    # Just to prevent huge copyrighted texts, keep it short
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:150] + "..." if len(t) > 150 else t

def extract_notes(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    
    nose = ""
    palate = ""
    finish = ""
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if not nose and ("nose" in line_lower or "aroma" in line_lower) and len(line) < 30:
            if i + 1 < len(lines): nose = lines[i+1]
        elif not palate and ("palate" in line_lower or "taste" in line_lower or "flavor" in line_lower) and len(line) < 30:
            if i + 1 < len(lines): palate = lines[i+1]
        elif not finish and ("finish" in line_lower) and len(line) < 30:
            if i + 1 < len(lines): finish = lines[i+1]
            
    # If explicit headings not found, look for keyword signals
    signal = ""
    if not nose and not palate and not finish:
        if "tasting note" in text.lower() or "review" in text.lower():
            signal = "short_official_signal"
            
    return clean_text(nose), clean_text(palate), clean_text(finish), signal

def main():
    print("Starting Web Tasting Note Extraction Pipeline...")
    
    if not os.path.exists(index_csv_path):
        print(f"Error: {index_csv_path} not found. Run fetch script first.")
        return
        
    with open(index_csv_path, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    extractable = []
    manual = []
    rejected = []
    
    for row in reader:
        out = {k: row.get(k, "") for k in OUT_FIELDS}
        
        status = row.get("fetch_status", "")
        if status != "success":
            out["extraction_status"] = "rejected_fetch_failed"
            out["recommended_action"] = "reject"
            out["production_ready"] = "false"
            rejected.append(out)
            continue
            
        html_path = row.get("snapshot_path", "")
        if not os.path.exists(html_path):
            out["extraction_status"] = "rejected_missing_snapshot"
            out["recommended_action"] = "reject"
            out["production_ready"] = "false"
            rejected.append(out)
            continue
            
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as hf:
            html = hf.read()
            
        if len(html) < 500:
            out["extraction_status"] = "rejected_too_short"
            out["recommended_action"] = "reject"
            out["production_ready"] = "false"
            rejected.append(out)
            continue
            
        nose, palate, finish, signal = extract_notes(html)
        out["nose_notes"] = nose
        out["palate_notes"] = palate
        out["finish_notes"] = finish
        
        if not nose and not palate and not finish and not signal:
            out["extraction_status"] = "rejected_no_notes_found"
            out["recommended_action"] = "reject"
            out["production_ready"] = "false"
            rejected.append(out)
            continue
            
        out["extraction_status"] = "extracted"
        
        # Decide if production ready
        source_type = row.get("source_type", "")
        mismatch = row.get("mismatch_flags", "")
        
        if source_type in ["official", "review_site"] and not mismatch and (nose or palate or finish):
            out["recommended_action"] = "import_to_staging"
            out["production_ready"] = "true"
            extractable.append(out)
        else:
            out["recommended_action"] = "manual_review"
            out["production_ready"] = "false"
            manual.append(out)
            
    # Write CSVs
    def write_csv(path, rows):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            
    write_csv(extractable_csv_path, extractable)
    write_csv(manual_csv_path, manual)
    write_csv(rejected_csv_path, rejected)
    
    # Reports
    r1_path = os.path.join(reports_dir, "220_web_tasting_note_extraction_quality_report.md")
    with open(r1_path, 'w', encoding='utf-8') as f:
        f.write("# Extraction Quality Report\n\n")
        f.write(f"- Extractable (Prod Ready): {len(extractable)}\n")
        f.write(f"- Manual Review: {len(manual)}\n")
        f.write(f"- Rejected: {len(rejected)}\n")
        
    gate_path = os.path.join(reports_dir, "221_web_tasting_note_extraction_gate.txt")
    
    # Validate Gate
    # No examples or empty
    bad_urls = any(not c["source_url"] for c in extractable + manual + rejected)
    bad_ready = any(c["production_ready"] == "true" and (c["mismatch_flags"] or c["source_type"] not in ["official", "review_site"]) for c in extractable)
    
    if not bad_urls and not bad_ready:
        decision = "GO"
        msg = "All extraction criteria met."
    else:
        decision = "NO-GO"
        msg = "Failed criteria check."
        
    with open(gate_path, 'w', encoding='utf-8') as f:
        f.write("12D Web Tasting Note Extraction Gate\n=================================\n")
        f.write(f"Decision: {decision}\n\n{msg}")
        
    print(f"Extraction Pipeline finished. Extractable: {len(extractable)}, Manual: {len(manual)}, Rejected: {len(rejected)}")

if __name__ == "__main__":
    main()

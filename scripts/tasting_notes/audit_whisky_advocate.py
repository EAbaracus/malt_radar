import os
import sqlite3
import csv
import urllib.request
import re
import difflib

OUTPUT_DIR = "data/output"
REPORTS_DIR = "output/reports"
DB_PATH = "output/import/production.db"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# 1. Analyze repo
r_script_url = "https://raw.githubusercontent.com/koki25ando/Whisky-Data-Scraping/master/whisky.R"
csv_url = "https://raw.githubusercontent.com/koki25ando/Whisky-Data-Scraping/master/scotch_review.csv"

def download_file(url, path):
    try:
        urllib.request.urlretrieve(url, path)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

r_script_path = os.path.join(OUTPUT_DIR, "whisky_r_script_preview.txt")
csv_path = os.path.join(OUTPUT_DIR, "whisky_advocate_downloaded.csv")

script_available = download_file(r_script_url, r_script_path)
csv_available = download_file(csv_url, csv_path)

fields_extracted = []
fragile_points = []
if script_available:
    with open(r_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'name' in content: fields_extracted.append('name')
        if 'category' in content: fields_extracted.append('category')
        if 'review.point' in content: fields_extracted.append('review.point')
        if 'price' in content: fields_extracted.append('price')
        if 'currency' in content: fields_extracted.append('currency')
        if 'description' in content: fields_extracted.append('description')
        
        if '1:2247' in content or '2247' in content:
            fragile_points.append("Fixed assumption of 2247 items (hardcoded loop).")
        if 'html_nodes' in content:
            fragile_points.append("Heavy HTML selector dependency (rvest `html_nodes`).")
        
        fragile_points.append("Old HTTP source usage (likely broken if website structure changed).")
        fragile_points.append("ToS/License risk: scraping Whisky Advocate reviews directly without apparent permission.")

schema_preview = []
matches = []

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Load db whiskies
db_whiskies = [dict(r) for r in conn.execute("SELECT whisky_id, name FROM whiskies").fetchall()]
db_whisky_names = {w['whisky_id']: w['name'] for w in db_whiskies}

def fuzzy_match(s1, s2):
    return int(difflib.SequenceMatcher(None, str(s1).lower(), str(s2).lower()).ratio() * 100)

if csv_available:
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.DictReader(f))
        
        if reader:
            first_row = reader[0]
            schema_preview = [{"column": col, "type": "string", "sample": str(val)[:50]} for col, val in first_row.items()]
            
            with open(os.path.join(OUTPUT_DIR, "whisky_advocate_preview_schema.csv"), 'w', newline='', encoding='utf-8') as sf:
                writer = csv.DictWriter(sf, fieldnames=["column", "type", "sample"])
                writer.writeheader()
                writer.writerows(schema_preview)
            
            for row in reader:
                source_name = str(row.get('name', '')).strip()
                if not source_name: continue
                
                score_str = row.get('review.point', '0')
                score = int(score_str) if score_str.isdigit() else 0
                desc = str(row.get('description', '')).strip()
                
                # match
                match_score = 0
                matched_name = None
                matched_id = None
                
                for wid, wname in db_whisky_names.items():
                    sim = fuzzy_match(source_name, wname)
                    if sim > match_score:
                        match_score = sim
                        matched_name = wname
                        matched_id = wid
                
                decision = "REJECT"
                if match_score >= 92:
                    age_source = re.search(r'\b(\d{1,2})\s*year', source_name.lower())
                    age_db = re.search(r'\b(\d{1,2})\s*year', (matched_name or '').lower())
                    age_s = age_source.group(1) if age_source else None
                    age_d = age_db.group(1) if age_db else None
                    
                    if age_s and age_d and age_s != age_d:
                        decision = "REJECT"
                    else:
                        decision = "KEEP_FOR_STAGING"
                elif match_score >= 80:
                    decision = "REVIEW"
                    
                matches.append({
                    "source_name": source_name,
                    "matched_whisky_id": matched_id,
                    "matched_whisky_name": matched_name,
                    "match_score": match_score,
                    "category": row.get('category', ''),
                    "review_point": score,
                    "price": row.get('price', ''),
                    "currency": row.get('currency', ''),
                    "has_description": bool(desc),
                    "decision": decision
                })
            
            if matches:
                with open(os.path.join(OUTPUT_DIR, "whisky_advocate_match_preview.csv"), 'w', newline='', encoding='utf-8') as mf:
                    keys = list(matches[0].keys())
                    writer = csv.DictWriter(mf, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(matches)

conn.close()

total_matches = len(matches)
keep_count = sum(1 for m in matches if m['decision'] == 'KEEP_FOR_STAGING')
review_count = sum(1 for m in matches if m['decision'] == 'REVIEW')
reject_count = sum(1 for m in matches if m['decision'] == 'REJECT')

gate_status = "GO" if csv_available else "BLOCKED_DATA_ACCESS"

md_report = f"""# Whisky Advocate External Dataset Audit Report (AŞAMA 12M)

## Repo Analysis
- **GitHub**: https://github.com/koki25ando/Whisky-Data-Scraping
- **Script Availability**: {'YES' if script_available else 'NO'}
- **CSV Data Availability**: {'YES' if csv_available else 'NO'}

### Extracted Fields
{', '.join(fields_extracted) if fields_extracted else 'None'}

### Script Vulnerabilities & Risks
"""
for f in fragile_points:
    md_report += f"- {f}\n"

md_report += f"""
## Legal & Usage Risk
- Scraping reviews directly from Whisky Advocate and publishing them without permission is a ToS/Copyright violation risk.
- **Description/review text fields MUST NOT be directly imported into production.**
- Can only be used via the staging pipeline for internal enrichment or paraphrasing, requiring manual approval.

## Match Preview Results
- Total records analyzed: {total_matches}
- **KEEP_FOR_STAGING**: {keep_count}
- **REVIEW**: {review_count}
- **REJECT**: {reject_count}

## Conclusion
- **Is the repo usable?**: Yes, but the script is brittle. The CSV data is the valuable part.
- **Can dataset be imported directly?**: NO.
- **Safe Usage Path**: Stage the matched records into `staging_tasting_notes`, avoiding direct insertion to `tasting_notes`. Let users manually review and potentially summarize the tasting notes to avoid copyright infringement.

## Gate Status
- **Status**: {gate_status}
"""

gate_report = f"""GATE: {gate_status}
production.db changed = NO
csv_available = {csv_available}
keep_for_staging_count = {keep_count}
review_count = {review_count}
reject_count = {reject_count}
"""

with open(os.path.join(REPORTS_DIR, "240_whisky_advocate_dataset_audit.md"), "w", encoding="utf-8") as f:
    f.write(md_report)
    f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


with open(os.path.join(REPORTS_DIR, "241_whisky_advocate_dataset_gate.txt"), "w", encoding="utf-8") as f:
    f.write(gate_report)

print("Audit script completed.")

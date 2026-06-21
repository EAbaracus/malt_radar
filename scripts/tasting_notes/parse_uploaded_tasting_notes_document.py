import os
import re
import csv
from datetime import datetime

INPUT_FILE = "data/input/uploaded_whisky_tasting_notes.txt"
OUTPUT_CSV = "data/output/uploaded_tasting_notes_parsed.csv"
REPORT_FILE = "output/reports/239_uploaded_tasting_notes_parse_report.md"

def normalize_name(name):
    # Remove excessive spaces and lowercase
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    return name

def parse_tasting_notes():
    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    parsed_records = []
    current_record = None
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Check for header line: starts with digit(s) and space
            header_match = re.match(r'^(\d+)\s+(.+)$', line)
            if header_match and not any(line.startswith(prefix) for prefix in ["Nose:", "Taste:", "Finish:", "Overall:"]):
                if current_record:
                    parsed_records.append(current_record)
                    
                entry_num = header_match.group(1)
                rest = header_match.group(2)
                
                # Extract components
                review_date = ""
                date_match = re.search(r'\((20\d\d-\d\d-\d\d)\)', rest)
                if date_match:
                    review_date = date_match.group(1)
                    rest = rest.replace(date_match.group(0), '')
                    
                abv = ""
                abv_match = re.search(r'\((\d+(?:\.\d+)?%)\)', rest)
                if abv_match:
                    abv = abv_match.group(1)
                    rest = rest.replace(abv_match.group(0), '')
                    
                category_hint = ""
                cat_match = re.search(r'\((Irish|Scotch|Bourbon|Rye|Japanese|Canadian|Single Malt|Blend.*?)\)', rest, re.IGNORECASE)
                if cat_match:
                    category_hint = cat_match.group(1)
                    rest = rest.replace(cat_match.group(0), '')
                    
                # Remove tags and stars
                rest = re.sub(r'#\S+', '', rest)
                rest = rest.replace('*', '')
                
                # Clean raw name
                raw_whisky_name = re.sub(r'\s+', ' ', rest).strip()
                normalized_whisky_name = normalize_name(raw_whisky_name)
                
                current_record = {
                    'source_doc': 'uploaded_whisky_tasting_notes.txt',
                    'source_entry_number': entry_num,
                    'raw_whisky_name': raw_whisky_name,
                    'normalized_whisky_name': normalized_whisky_name,
                    'abv': abv,
                    'category_hint': category_hint,
                    'country_or_region_hint': '', # Handled in matching if possible
                    'review_date': review_date,
                    'nose_notes': '',
                    'palate_notes': '',
                    'finish_notes': '',
                    'overall_summary': ''
                }
            elif current_record:
                # Parse fields
                if line.lower().startswith('nose:'):
                    current_record['nose_notes'] = line[5:].strip()
                elif line.lower().startswith('taste:'):
                    current_record['palate_notes'] = line[6:].strip()
                elif line.lower().startswith('finish:'):
                    current_record['finish_notes'] = line[7:].strip()
                elif line.lower().startswith('overall:'):
                    current_record['overall_summary'] = line[8:].strip()

    if current_record:
        parsed_records.append(current_record)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'source_doc', 'source_entry_number', 'raw_whisky_name', 'normalized_whisky_name',
            'abv', 'category_hint', 'country_or_region_hint', 'review_date',
            'nose_notes', 'palate_notes', 'finish_notes', 'overall_summary'
        ])
        writer.writeheader()
        writer.writerows(parsed_records)
        
    print(f"Parsed {len(parsed_records)} records into {OUTPUT_CSV}")
    
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Uploaded Tasting Notes Parse Report\n\n")
        f.write(f"- File Processed: {INPUT_FILE}\n")
        f.write(f"- Total Records Parsed: {len(parsed_records)}\n")
        f.write(f"- Output CSV: {OUTPUT_CSV}\n")
        f.write("\n## Data Minimization Verification\n")
        f.write("Raw document was parsed into structured fields (nose/palate/finish) instead of copying the full text.\n")
        
if __name__ == "__main__":
    parse_tasting_notes()

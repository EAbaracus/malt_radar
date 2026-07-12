import os
import csv
import sqlite3
import hashlib
from difflib import SequenceMatcher

INPUT_CSV = "data/output/uploaded_tasting_notes_parsed.csv"
PREVIEW_CSV = "data/output/uploaded_tasting_notes_matched_staging_preview.csv"
MANUAL_CSV = "data/output/uploaded_tasting_notes_manual_review.csv"
DUPLICATE_CSV = "data/output/uploaded_tasting_notes_duplicate_candidates.csv"

REPORT_FILE = "output/reports/240_uploaded_tasting_notes_match_quality_report.md"
GATE_FILE = "output/reports/241_12j_uploaded_tasting_notes_gate.txt"
DB_PATH = "output/import/production.db"

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def normalize_db_name(name):
    import re
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def match_whiskies():
    db_hash_before = get_file_hash(DB_PATH)
    
    if not os.path.exists(INPUT_CSV):
        print(f"Missing {INPUT_CSV}")
        return
        
    parsed_notes = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed_notes.append(row)
            
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT whisky_id, name FROM whiskies")
    whiskies = cursor.fetchall()
    conn.close()
    
    db_whiskies = [{'id': w[0], 'name': w[1], 'norm_name': normalize_db_name(w[1])} for w in whiskies]
    
    staging = []
    manual = []
    duplicates = []
    matched_ids = set()
    
    for row in parsed_notes:
        best_match = None
        best_score = 0
        norm_raw = normalize_db_name(row['normalized_whisky_name'])
        
        for w in db_whiskies:
            score = similar(norm_raw, w['norm_name'])
            if score > best_score:
                best_score = score
                best_match = w
                
        row['matched_whisky_id'] = best_match['id'] if best_match else ''
        row['matched_whisky_name'] = best_match['name'] if best_match else ''
        row['match_score'] = round(best_score, 2)
        row['match_status'] = ''
        row['mismatch_flags'] = ''
        row['recommended_action'] = ''
        row['production_ready'] = 'False'
        
        if best_score > 0.85:
            row['match_status'] = 'HIGH_CONFIDENCE'
            
            # Check for duplicate in this batch
            if best_match['id'] in matched_ids:
                row['mismatch_flags'] = 'DUPLICATE_IN_DOCUMENT'
                row['recommended_action'] = 'merge_or_manual_review'
                duplicates.append(row)
                manual.append(row)
            else:
                row['production_ready'] = 'True'
                row['recommended_action'] = 'insert_staging'
                staging.append(row)
                matched_ids.add(best_match['id'])
        else:
            row['match_status'] = 'LOW_CONFIDENCE'
            row['mismatch_flags'] = 'LOW_SCORE'
            row['recommended_action'] = 'manual_review'
            manual.append(row)
            
    # Write CSVs
    fieldnames = list(parsed_notes[0].keys())
    
    for f_path, data in [(PREVIEW_CSV, staging), (MANUAL_CSV, manual), (DUPLICATE_CSV, duplicates)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
    db_hash_after = get_file_hash(DB_PATH)
    db_changed = db_hash_before != db_hash_after
    
    # Reports
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Tasting Notes Match Quality Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Total Parsed: {len(parsed_notes)}\n")
        f.write(f"- Staging Preview (High Confidence): {len(staging)}\n")
        f.write(f"- Manual Review: {len(manual)}\n")
        f.write(f"- Duplicates within Document: {len(duplicates)}\n")
        
    gate_status = "GO"
    reasons = []
    
    if db_changed:
        gate_status = "NO-GO"
        reasons.append("production.db was modified during execution!")
        
    if len(parsed_notes) == 0:
        gate_status = "NO-GO"
        reasons.append("Parsed row count is 0.")
        
    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        if reasons:
            for r in reasons:
                f.write(f"REASON: {r}\n")
        else:
            f.write("All safety checks passed.\n")
            f.write("- DB remains unchanged.\n")
            f.write("- Duplicates and low confidence matches handled.\n")
            
    print(f"Matching finished. Staging: {len(staging)}, Manual: {len(manual)}")

if __name__ == "__main__":
    match_whiskies()

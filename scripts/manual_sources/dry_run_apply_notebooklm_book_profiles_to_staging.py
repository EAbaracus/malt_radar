import os
import csv
import sqlite3
from datetime import datetime
from collections import Counter

DB_PATH = "output/import/production.db"
INPUT_CSV = "data/manual_sources/books/review_csv/book_profile_apply_candidate_preview.csv"
OUTPUT_CSV = "data/manual_sources/books/review_csv/book_profile_staging_dry_run_preview.csv"
REPORT_FILE = "output/reports/12y_notebooklm_book_profile_staging_dry_run_report.md"
GATE_FILE = "output/reports/12y_notebooklm_book_profile_staging_dry_run_gate.txt"

EXPECTED_AXES = [
    "radar_smoky", "radar_peaty", "radar_sherry", "radar_fruity", "radar_floral", 
    "radar_spicy", "radar_sweet", "radar_oak", "radar_maritime", "radar_winey", 
    "radar_malty", "radar_nutty", "radar_herbal", "radar_waxy", "radar_oily",
    "radar_light_body", "radar_rich_body"
]
VALID_RADAR_VALUES = {"0", "20", "40", "60", "80", "100"}

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return
        
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    cursor.execute("SELECT whisky_id FROM whiskies")
    whiskies_db = set(r[0] for r in cursor.fetchall())
    
    cursor.execute("SELECT whisky_id FROM flavor_profiles")
    profiles_db = set(r[0] for r in cursor.fetchall())
    
    results = []
    seen_ids = set()
    
    stats = {
        "input_rows": 0,
        "planned_insert": 0,
        "planned_manual_review": 0,
        "blocked": 0,
        "missing_fk": 0,
        "invalid_radar_value": 0,
        "invalid_radar_axis": 0,
        "duplicate_input": 0,
        "conflict_existing_profile_count": 0,
        "empty_profile_signal": 0,
        "source_book_dist": Counter(),
        "planned_whisky_list": []
    }
    
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    for row in reader:
        stats["input_rows"] += 1
        
        sb = row.get('source_book', 'unknown')
        stats["source_book_dist"][sb] += 1
        
        w_id = row.get('matched_whisky_id')
        name = row.get('whisky_name', '')
        
        is_blocked = False
        block_reason = []
        is_manual = False
        
        if w_id and w_id in seen_ids:
            is_blocked = True
            block_reason.append("duplicate_input")
            stats["duplicate_input"] += 1
        elif w_id:
            seen_ids.add(w_id)
            
        if not w_id or w_id not in whiskies_db:
            is_blocked = True
            block_reason.append("missing_fk")
            stats["missing_fk"] += 1
            
        has_any_radar = False
        for axis in EXPECTED_AXES:
            val = row.get(axis, "")
            if val is None or val == "":
                continue
            has_any_radar = True
            if str(val) not in VALID_RADAR_VALUES:
                is_blocked = True
                block_reason.append("invalid_radar_value")
                stats["invalid_radar_value"] += 1
                break
                
        for key in row.keys():
            if key.startswith("radar_") and key != "radar_conflict" and key not in EXPECTED_AXES:
                is_blocked = True
                block_reason.append("invalid_radar_axis")
                stats["invalid_radar_axis"] += 1
                break
                
        if not has_any_radar:
            is_blocked = True
            block_reason.append("empty_profile_signal")
            stats["empty_profile_signal"] += 1
            
        has_conflict = False
        if w_id in profiles_db:
            has_conflict = True
            is_manual = True
            
        if str(row.get('conflict_existing_profile', '')).lower() == 'true':
            has_conflict = True
            is_manual = True
            
        if has_conflict:
            stats["conflict_existing_profile_count"] += 1
            row['conflict_existing_profile'] = 'true'
            
        if is_blocked:
            import_status = "blocked"
            stats["blocked"] += 1
        elif is_manual:
            import_status = "planned_manual_review"
            stats["planned_manual_review"] += 1
            stats["planned_whisky_list"].append(name)
        else:
            import_status = "planned_insert"
            stats["planned_insert"] += 1
            stats["planned_whisky_list"].append(name)
            
        row['import_status'] = import_status
        row['block_reason'] = "; ".join(block_reason)
        row['source_system'] = "notebooklm_book_profile"
        row['approval_status'] = "staging_pending_review"
        
        results.append(row)
        
    if results:
        keys = list(results[0].keys())
        # move import_status and block_reason to the front for better visibility
        keys = ['import_status', 'block_reason', 'approval_status', 'source_system'] + [k for k in keys if k not in ['import_status', 'block_reason', 'approval_status', 'source_system']]
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
    else:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            pass

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# NotebookLM Book Profile Staging Dry Run Report\n\n")
        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- input_rows: {stats['input_rows']}\n")
        f.write(f"- planned_insert: {stats['planned_insert']}\n")
        f.write(f"- planned_manual_review: {stats['planned_manual_review']}\n")
        f.write(f"- blocked: {stats['blocked']}\n")
        f.write(f"- missing_fk: {stats['missing_fk']}\n")
        f.write(f"- invalid_radar_value: {stats['invalid_radar_value']}\n")
        f.write(f"- invalid_radar_axis: {stats['invalid_radar_axis']}\n")
        f.write(f"- duplicate_input: {stats['duplicate_input']}\n")
        f.write(f"- empty_profile_signal: {stats['empty_profile_signal']}\n")
        f.write(f"- conflict_existing_profile_count: {stats['conflict_existing_profile_count']}\n\n")
        
        f.write("## Source/Book Dağılımı\n")
        for k, v in stats['source_book_dist'].items(): f.write(f"- {k}: {v}\n")
        
        f.write("\n## Planned Whisky Listesi\n")
        for w in stats['planned_whisky_list']: f.write(f"- {w}\n")

    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        if stats['blocked'] > 0:
            f.write("BOOK_NOTEBOOKLM_STAGING_DRY_RUN_NO-GO\n")
        elif stats['planned_insert'] >= 1 and stats['blocked'] == 0:
            f.write("BOOK_NOTEBOOKLM_STAGING_DRY_RUN_GO_FOR_PROFILE_STAGING_APPLY\n")
        elif stats['planned_insert'] == 0 and stats['planned_manual_review'] > 0:
            f.write("BOOK_NOTEBOOKLM_STAGING_DRY_RUN_WARN_GO_REVIEW_ONLY\n")
        else:
            f.write("BOOK_NOTEBOOKLM_STAGING_DRY_RUN_NO-GO\n")
            
        f.write("PRODUCTION_IMPORT_NO-GO\n")

if __name__ == '__main__':
    main()

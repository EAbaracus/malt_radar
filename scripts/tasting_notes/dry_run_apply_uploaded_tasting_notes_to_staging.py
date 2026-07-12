import os
import csv
import sqlite3
import hashlib

PREVIEW_CSV = "data/output/uploaded_tasting_notes_matched_staging_preview.csv"
PLAN_CSV = "data/output/uploaded_tasting_notes_staging_apply_plan.csv"
BLOCKED_CSV = "data/output/uploaded_tasting_notes_staging_apply_blocked.csv"
AUDIT_CSV = "data/output/uploaded_tasting_notes_match_audit.csv"

REPORT_DRY_RUN = "output/reports/242_uploaded_tasting_notes_staging_apply_dry_run_report.md"
REPORT_AUDIT = "output/reports/243_uploaded_tasting_notes_match_audit_report.md"
GATE_FILE = "output/reports/244_12k_uploaded_tasting_notes_apply_gate.txt"
DB_PATH = "output/import/production.db"

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def dry_run():
    db_hash_before = get_file_hash(DB_PATH)
    
    if not os.path.exists(PREVIEW_CSV):
        print(f"Missing {PREVIEW_CSV}")
        return

    # Load whiskies from DB to verify FK
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT whisky_id, name FROM whiskies")
    whiskies = cursor.fetchall()
    conn.close()
    
    valid_whisky_ids = {w[0] for w in whiskies}
    
    plan = []
    blocked = []
    audit = []
    seen_combinations = set()
    seen_whisky_name = set()
    
    with open(PREVIEW_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    for row in rows:
        wid = row.get('matched_whisky_id', '')
        score = float(row.get('match_score', 0))
        doc = row.get('source_doc', '')
        entry = row.get('source_entry_number', '')
        norm_name = row.get('normalized_whisky_name', '')
        nose = row.get('nose_notes', '')
        taste = row.get('palate_notes', '')
        finish = row.get('finish_notes', '')
        
        audit_row = {
            'whisky_id': wid,
            'product_name': row.get('raw_whisky_name', ''),
            'source_doc': doc,
            'source_entry_number': entry,
            'nose_notes': nose,
            'palate_notes': taste,
            'finish_notes': finish,
            'overall_summary': row.get('overall_summary', ''),
            'match_score': score,
            'match_status': row.get('match_status', ''),
            'audit_decision': 'PASS',
            'block_reason': '',
            'dry_run_action': ''
        }
        
        # Validation Rules
        is_blocked = False
        if wid not in valid_whisky_ids:
            audit_row['audit_decision'] = 'FAIL'
            audit_row['block_reason'] = 'FK_MISSING'
            audit_row['dry_run_action'] = 'block'
            is_blocked = True
        elif not nose and not taste and not finish:
            audit_row['audit_decision'] = 'FAIL'
            audit_row['block_reason'] = 'EMPTY_NOTES'
            audit_row['dry_run_action'] = 'block'
            is_blocked = True
        elif f"{wid}_{doc}_{entry}" in seen_combinations:
            audit_row['audit_decision'] = 'FAIL'
            audit_row['block_reason'] = 'DUPLICATE_ENTRY'
            audit_row['dry_run_action'] = 'block'
            is_blocked = True
        elif f"{wid}_{norm_name}" in seen_whisky_name:
            audit_row['audit_decision'] = 'WARNING'
            audit_row['block_reason'] = 'DUPLICATE_WHISKY_NAME'
            audit_row['dry_run_action'] = 'review_merge_candidate'
            # Note: The prompt says "varsa review_merge_candidate" but doesn't explicitly block it.
            # We will put it in plan but mark it.
        else:
            audit_row['dry_run_action'] = 'staging_insert_candidate'
            
        if score < 0.85:
            audit_row['audit_decision'] = 'FAIL'
            audit_row['block_reason'] = 'LOW_SCORE'
            audit_row['dry_run_action'] = 'block'
            is_blocked = True
            
        seen_combinations.add(f"{wid}_{doc}_{entry}")
        seen_whisky_name.add(f"{wid}_{norm_name}")
        
        audit.append(audit_row)
        
        if audit_row['dry_run_action'] == 'block':
            blocked.append(audit_row)
        else:
            plan.append(audit_row)
            
    # Write CSVs
    fieldnames = ['whisky_id', 'product_name', 'source_doc', 'source_entry_number', 
                  'nose_notes', 'palate_notes', 'finish_notes', 'overall_summary', 
                  'match_score', 'match_status', 'audit_decision', 'block_reason', 'dry_run_action']
                  
    for f_path, data in [(PLAN_CSV, plan), (BLOCKED_CSV, blocked), (AUDIT_CSV, audit)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
    db_hash_after = get_file_hash(DB_PATH)
    db_changed = db_hash_before != db_hash_after
    
    # Reports
    with open(REPORT_DRY_RUN, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Tasting Notes Staging Apply Dry-Run Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Total Input Rows: {len(rows)}\n")
        f.write(f"- Apply Plan (Insert/Merge): {len(plan)}\n")
        f.write(f"- Blocked: {len(blocked)}\n")
        
    with open(REPORT_AUDIT, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Tasting Notes Match Audit Report\n\n")
        f.write(f"- Audited Matches: {len(audit)}\n")
        pass_count = sum(1 for a in audit if a['audit_decision'] == 'PASS')
        fail_count = sum(1 for a in audit if a['audit_decision'] == 'FAIL')
        warn_count = sum(1 for a in audit if a['audit_decision'] == 'WARNING')
        f.write(f"- PASS: {pass_count}\n")
        f.write(f"- WARNING: {warn_count}\n")
        f.write(f"- FAIL: {fail_count}\n")
        
    gate_status = "GO"
    reasons = []
    
    if db_changed:
        gate_status = "NO-GO"
        reasons.append("production.db was modified during execution!")
        
    if len(rows) != 60:
        gate_status = "NO-GO"
        reasons.append(f"Expected 60 input rows, got {len(rows)}")
        
    fk_missing = sum(1 for a in audit if a['block_reason'] == 'FK_MISSING')
    if fk_missing > 0:
        gate_status = "NO-GO"
        reasons.append(f"FK missing count is {fk_missing}")
        
    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        if reasons:
            for r in reasons:
                f.write(f"REASON: {r}\n")
        else:
            f.write("All safety checks passed.\n")
            f.write("- DB remains unchanged.\n")
            f.write("- 60 records audited successfully.\n")
            
    print(f"Dry-run finished. Plan: {len(plan)}, Blocked: {len(blocked)}")

if __name__ == "__main__":
    dry_run()

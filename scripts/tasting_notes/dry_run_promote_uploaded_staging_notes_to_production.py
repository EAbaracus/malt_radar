import os
import csv
import sqlite3
import hashlib

QA_PASS_CSV = "data/output/uploaded_tasting_notes_staging_qa_pass.csv"
PLAN_CSV = "data/output/uploaded_tasting_notes_production_promotion_plan.csv"
BLOCKED_CSV = "data/output/uploaded_tasting_notes_production_promotion_blocked.csv"

REPORT_MD = "output/reports/255_uploaded_tasting_notes_production_promotion_dry_run_report.md"
GATE_TXT = "output/reports/256_12n_uploaded_tasting_notes_promotion_gate.txt"
DB_PATH = "output/import/production.db"

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def promote_dry_run():
    db_hash_before = get_file_hash(DB_PATH)
    
    if not os.path.exists(QA_PASS_CSV):
        print(f"Missing {QA_PASS_CSV}")
        return

    with open(QA_PASS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        qa_rows = list(reader)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    plan = []
    blocked = []
    
    seen_in_this_run = set()
    
    for row in qa_rows:
        staging_id = row.get('staging_id', '')
        wid = row.get('whisky_id', '')
        pname = row.get('product_name', '')
        source_system = row.get('source_system', '')
        source_doc = row.get('source_doc', '')
        source_entry_number = row.get('source_entry_number', '')
        nose = row.get('nose_length', '') # actually the input just has lengths, wait!
        
        # We need the actual text from the staging table, because the QA CSV only has lengths!
        cursor.execute("""
            SELECT nose, palate, finish, conclusion 
            FROM staging_tasting_notes 
            WHERE staging_note_id = ?
        """, (staging_id,))
        res = cursor.fetchone()
        
        nose_text = ""
        palate_text = ""
        finish_text = ""
        conclusion_text = ""
        
        if res:
            nose_text = res[0] or ""
            palate_text = res[1] or ""
            finish_text = res[2] or ""
            conclusion_text = res[3] or ""
            
        out_row = {
            'staging_id': staging_id,
            'whisky_id': wid,
            'product_name': pname,
            'source_system': source_system,
            'source_doc': source_doc,
            'source_entry_number': source_entry_number,
            'nose_notes': nose_text,
            'palate_notes': palate_text,
            'finish_notes': finish_text,
            'overall_summary': conclusion_text,
            'duplicate_in_tasting_notes': 'False',
            'duplicate_in_staging': 'False',
            'promotion_decision': '',
            'block_reason': '',
            'recommended_action': ''
        }
        
        # Check duplicate in tasting_notes
        cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE whisky_id = ? AND source_url = ?", (wid, source_doc))
        count_tn = cursor.fetchone()[0]
        
        unique_key = f"{wid}_{source_system}_{source_doc}_{source_entry_number}"
        
        is_blocked = False
        reasons = []
        
        if count_tn > 0:
            out_row['duplicate_in_tasting_notes'] = 'True'
            is_blocked = True
            reasons.append("DUPLICATE_IN_TASTING_NOTES")
            
        if unique_key in seen_in_this_run:
            out_row['duplicate_in_staging'] = 'True'
            is_blocked = True
            reasons.append("DUPLICATE_IN_STAGING_PLAN")
            
        if not nose_text and not palate_text and not finish_text:
            is_blocked = True
            reasons.append("EMPTY_NOTES")
            
        if is_blocked:
            out_row['promotion_decision'] = 'BLOCKED'
            out_row['block_reason'] = '|'.join(reasons)
            out_row['recommended_action'] = 'manual_review'
            blocked.append(out_row)
        else:
            out_row['promotion_decision'] = 'PASS'
            out_row['recommended_action'] = 'promote_to_tasting_notes'
            plan.append(out_row)
            seen_in_this_run.add(unique_key)
            
    conn.close()
    
    # Write outputs
    fieldnames = [
        'staging_id', 'whisky_id', 'product_name', 'source_system', 'source_doc', 'source_entry_number',
        'nose_notes', 'palate_notes', 'finish_notes', 'overall_summary', 'duplicate_in_tasting_notes',
        'duplicate_in_staging', 'promotion_decision', 'block_reason', 'recommended_action'
    ]
    
    for f_path, data in [(PLAN_CSV, plan), (BLOCKED_CSV, blocked)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
    # Hash check
    db_hash_after = get_file_hash(DB_PATH)
    db_changed = db_hash_before != db_hash_after
    
    # Reports
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Tasting Notes Production Promotion Dry-Run Report\n\n")
        f.write(f"- QA PASS Input Rows: {len(qa_rows)}\n")
        f.write(f"- Promotion Plan (Insert): {len(plan)}\n")
        f.write(f"- Blocked: {len(blocked)}\n")
        
    gate_status = "GO"
    reasons = []
    
    if db_changed:
        gate_status = "NO-GO"
        reasons.append("production.db was modified during execution!")
        
    if len(qa_rows) != 60:
        gate_status = "NO-GO"
        reasons.append(f"Expected 60 input rows, got {len(qa_rows)}")
        
    duplicate_promoted = sum(1 for p in plan if p['duplicate_in_tasting_notes'] == 'True' or p['duplicate_in_staging'] == 'True')
    if duplicate_promoted > 0:
        gate_status = "NO-GO"
        reasons.append("Duplicate record found in promotion plan!")
        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        if reasons:
            for r in reasons:
                f.write(f"REASON: {r}\n")
        else:
            f.write("All safety checks passed.\n")
            f.write("- DB remains unchanged.\n")
            f.write(f"- {len(qa_rows)} QA PASS records processed.\n")
            f.write(f"- {len(plan)} records ready for promotion.\n")

if __name__ == "__main__":
    promote_dry_run()

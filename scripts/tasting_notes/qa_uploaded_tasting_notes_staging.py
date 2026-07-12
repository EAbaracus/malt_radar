import os
import csv
import sqlite3
import hashlib
import re

PASS_CSV = "data/output/uploaded_tasting_notes_staging_qa_pass.csv"
REVIEW_CSV = "data/output/uploaded_tasting_notes_staging_qa_review.csv"
BLOCKED_CSV = "data/output/uploaded_tasting_notes_staging_qa_blocked.csv"

REPORT_MD = "output/reports/247_uploaded_tasting_notes_staging_qa_report.md"
GATE_TXT = "output/reports/248_12m_uploaded_tasting_notes_staging_qa_gate.txt"
DB_PATH = "output/import/production.db"

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def check_encoding_issues(text):
    if not text:
        return False
    # Check for replacement character or unescaped HTML entities or weird unicode
    if '\ufffd' in text or '&amp;' in text or '<' in text or '>' in text:
        return True
    return False

def qa_staging():
    db_hash_before = get_file_hash(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Load whiskies for FK check
    cursor.execute("SELECT whisky_id FROM whiskies")
    valid_whisky_ids = {r[0] for r in cursor.fetchall()}
    
    # Load 60 uploaded_document records
    cursor.execute("""
        SELECT staging_note_id, matched_master_whisky_id, product_name, source_url, source_review_id,
               source_system, approval_status, nose, palate, finish
        FROM staging_tasting_notes
        WHERE source_system = 'uploaded_document'
    """)
    records = cursor.fetchall()
    
    pass_rows = []
    review_rows = []
    blocked_rows = []
    
    seen_unique_key = set()
    whisky_counts = {}
    
    for r in records:
        wid = r[1]
        whisky_counts[wid] = whisky_counts.get(wid, 0) + 1
        
    for r in records:
        staging_id, wid, product_name, source_url, source_review_id, source_system, approval_status, nose, palate, finish = r
        
        nose_len = len(nose) if nose else 0
        palate_len = len(palate) if palate else 0
        finish_len = len(finish) if finish else 0
        
        has_encoding = check_encoding_issues(nose) or check_encoding_issues(palate) or check_encoding_issues(finish)
        
        unique_key = f"{wid}_{source_url}_{source_review_id}"
        is_duplicate_key = unique_key in seen_unique_key
        seen_unique_key.add(unique_key)
        
        multiple_for_whisky = whisky_counts.get(wid, 0) > 1
        
        row = {
            'staging_id': staging_id,
            'whisky_id': wid,
            'product_name': product_name,
            'source_doc': source_url,
            'source_entry_number': source_review_id,
            'source_system': source_system,
            'approval_status': approval_status,
            'nose_length': nose_len,
            'palate_length': palate_len,
            'finish_length': finish_len,
            'has_encoding_issue': has_encoding,
            'has_duplicate_key': is_duplicate_key,
            'qa_decision': '',
            'qa_reason': '',
            'recommended_next_action': ''
        }
        
        reasons = []
        is_blocked = False
        is_review = False
        
        # Block rules
        if approval_status != 'staging_pending_review':
            reasons.append("Invalid approval_status")
            is_blocked = True
        if wid not in valid_whisky_ids:
            reasons.append("FK_MISSING")
            is_blocked = True
        if nose_len == 0 and palate_len == 0 and finish_len == 0:
            reasons.append("EMPTY_NOTES")
            is_blocked = True
        if is_duplicate_key:
            reasons.append("DUPLICATE_STAGING_KEY")
            is_blocked = True
            
        # Review rules
        if not is_blocked:
            if has_encoding:
                reasons.append("ENCODING_ISSUE")
                is_review = True
            if multiple_for_whisky:
                reasons.append("MULTIPLE_NOTES_FOR_WHISKY")
                is_review = True
            if nose_len < 5 or palate_len < 5 or finish_len < 5:
                reasons.append("NOTE_TOO_SHORT")
                is_review = True
            if nose_len > 500 or palate_len > 500 or finish_len > 500:
                reasons.append("NOTE_TOO_LONG")
                is_review = True
                
        row['qa_reason'] = "|".join(reasons)
        
        if is_blocked:
            row['qa_decision'] = 'BLOCKED'
            row['recommended_next_action'] = 'delete_or_fix'
            blocked_rows.append(row)
        elif is_review:
            row['qa_decision'] = 'REVIEW'
            row['recommended_next_action'] = 'manual_review_required'
            review_rows.append(row)
        else:
            row['qa_decision'] = 'PASS'
            row['recommended_next_action'] = 'production_insert_candidate'
            pass_rows.append(row)
            
    conn.close()
    
    # Write CSVs
    fieldnames = [
        'staging_id', 'whisky_id', 'product_name', 'source_doc', 'source_entry_number',
        'source_system', 'approval_status', 'nose_length', 'palate_length', 'finish_length',
        'has_encoding_issue', 'has_duplicate_key', 'qa_decision', 'qa_reason', 'recommended_next_action'
    ]
    
    for f_path, data in [(PASS_CSV, pass_rows), (REVIEW_CSV, review_rows), (BLOCKED_CSV, blocked_rows)]:
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
        f.write("# Uploaded Tasting Notes Staging QA Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Total Records QA'd: {len(records)}\n")
        f.write(f"- PASS (Ready for Prod): {len(pass_rows)}\n")
        f.write(f"- REVIEW (Needs Manual Check): {len(review_rows)}\n")
        f.write(f"- BLOCKED: {len(blocked_rows)}\n")
        
    gate_status = "GO"
    gate_reasons = []
    
    if db_changed:
        gate_status = "NO-GO"
        gate_reasons.append("production.db was modified during execution!")
        
    if len(records) != 60:
        gate_status = "NO-GO"
        gate_reasons.append(f"Expected 60 records, got {len(records)}")
        
    fk_missing = sum(1 for r in blocked_rows if "FK_MISSING" in r['qa_reason'])
    if fk_missing > 0:
        gate_status = "NO-GO"
        gate_reasons.append(f"FK_MISSING count: {fk_missing}")
        
    if gate_status == "GO":
        with open(GATE_TXT, 'w', encoding='utf-8') as f:
            f.write(f"GATE: {gate_status}\n")
            f.write("All safety checks passed.\n")
            f.write("- DB remains unchanged.\n")
            f.write("- 60 uploaded_document records audited.\n")
            f.write(f"- Production insert candidates (PASS): {len(pass_rows)}\n")
    else:
        with open(GATE_TXT, 'w', encoding='utf-8') as f:
            f.write(f"GATE: {gate_status}\n")
            for r in gate_reasons:
                f.write(f"REASON: {r}\n")

if __name__ == "__main__":
    qa_staging()

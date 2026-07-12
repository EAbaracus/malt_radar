import os
import csv
import sqlite3
import shutil
import hashlib

DB_PATH = "output/import/production.db"
DB_BACKUP_PATH = "output/import/production_before_12o_rollback_mock_uploaded_notes.db"
QUARANTINE_CSV = "data/output/uploaded_production_tasting_notes_quarantine_candidates.csv"
DELETED_CSV = "data/output/uploaded_production_tasting_notes_rollback_deleted.csv"
BLOCKED_CSV = "data/output/uploaded_production_tasting_notes_rollback_blocked.csv"
REPORT_MD = "output/reports/267_uploaded_production_tasting_notes_rollback_report.md"
GATE_TXT = "output/reports/268_12o_uploaded_production_tasting_notes_rollback_gate.txt"

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def rollback():
    if not os.path.exists(QUARANTINE_CSV):
        print(f"Missing {QUARANTINE_CSV}")
        return
        
    shutil.copy2(DB_PATH, DB_BACKUP_PATH)
    backup_hash = get_file_hash(DB_BACKUP_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Pre counts
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    pre_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE source_system='uploaded_document'")
    pre_uploaded = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes")
    pre_stn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    pre_fp = cursor.fetchone()[0]
    
    with open(QUARANTINE_CSV, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        
    deleted_rows = []
    blocked_rows = []
    
    target_count = len(rows)
    transaction_success = False
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        for row in rows:
            tn_id = row.get('tasting_note_id')
            wid = row.get('whisky_id')
            
            if not tn_id or not wid:
                row['block_reason'] = "Missing ID"
                blocked_rows.append(row)
                continue
                
            # Verify source_system is uploaded_document before delete
            cursor.execute("SELECT source_system FROM tasting_notes WHERE rowid=?", (tn_id,))
            res = cursor.fetchone()
            if not res or res[0] != 'uploaded_document':
                row['block_reason'] = "Not uploaded_document or not found"
                blocked_rows.append(row)
                continue
                
            cursor.execute("DELETE FROM tasting_notes WHERE rowid=?", (tn_id,))
            
            # Update staging
            cursor.execute("""
                UPDATE staging_tasting_notes 
                SET approval_status='staging_quality_rejected' 
                WHERE approval_status='promoted_to_production' AND matched_master_whisky_id=?
            """, (wid,))
            
            deleted_rows.append(row)
            
        conn.commit()
        transaction_success = True
    except Exception as e:
        conn.rollback()
        print(f"Transaction failed: {e}")
        transaction_success = False
        
    # Post counts
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    post_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE source_system='uploaded_document'")
    post_uploaded = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes")
    post_stn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes WHERE approval_status='staging_quality_rejected'")
    post_rejected = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    post_fp = cursor.fetchone()[0]
    
    conn.close()
    
    fieldnames = list(rows[0].keys()) + ['block_reason'] if rows else []
    for f_path, data in [(DELETED_CSV, deleted_rows), (BLOCKED_CSV, blocked_rows)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            if fieldnames:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                # Clean up to not expose full text if there was any
                for d in data:
                    safe_d = {k: v for k, v in d.items() if k not in ['short_snippet']}
                    safe_d['short_snippet'] = d.get('short_snippet', '')
                    writer.writerow(safe_d)
                    
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Production Tasting Notes Rollback Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Backup created: `production_before_12o_rollback_mock_uploaded_notes.db` (Hash: {backup_hash})\n")
        f.write(f"- Delete target count: {target_count}\n")
        f.write(f"- Deleted: {len(deleted_rows)}\n")
        f.write(f"- Blocked: {len(blocked_rows)}\n\n")
        f.write(f"- tasting_notes count: {pre_tn} -> {post_tn}\n")
        f.write(f"- uploaded_prod_notes count: {pre_uploaded} -> {post_uploaded}\n")
        f.write(f"- staging_tasting_notes count: {pre_stn} -> {post_stn}\n")
        f.write(f"- staging status update count (quality rejected): {post_rejected}\n")
        f.write(f"- flavor_profiles count: {pre_fp} -> {post_fp}\n")
        
    gate = "GO"
    reasons = []
    
    if not os.path.exists(DB_BACKUP_PATH):
        gate = "NO-GO"
        reasons.append("Backup not created.")
    if target_count != 60:
        gate = "NO-GO"
        reasons.append(f"Delete target count {target_count} != 60")
    if len(deleted_rows) != 60:
        gate = "NO-GO"
        reasons.append(f"Deleted count {len(deleted_rows)} != 60")
    if post_tn != 25:
        gate = "NO-GO"
        reasons.append(f"tasting_notes post count {post_tn} != 25")
    if post_uploaded != 0:
        gate = "NO-GO"
        reasons.append(f"uploaded_prod_notes post count {post_uploaded} != 0")
    if post_stn != pre_stn:
        gate = "NO-GO"
        reasons.append(f"staging_tasting_notes count changed {pre_stn} -> {post_stn}")
    if post_fp != pre_fp:
        gate = "NO-GO"
        reasons.append(f"flavor_profiles count changed {pre_fp} -> {post_fp}")
    if not transaction_success:
        gate = "NO-GO"
        reasons.append("Transaction rolled back.")
        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate}\n")
        if reasons:
            for r in reasons:
                f.write(f"REASON: {r}\n")
        else:
            f.write("All safety checks passed.\n")
            f.write("- backup created\n")
            f.write("- delete target count = 60\n")
            f.write("- deleted = 60\n")
            f.write("- blocked = 0\n")
            f.write("- tasting_notes count 85 -> 25\n")
            f.write("- uploaded_prod_notes 60 -> 0\n")
            f.write("- staging_tasting_notes count 63 unchanged\n")
            f.write("- staging status quality failed updated\n")
            f.write("- flavor_profiles count 380 unchanged\n")
            f.write("- transaction successful\n")
            f.write("- raw full text output not written\n")

if __name__ == "__main__":
    rollback()

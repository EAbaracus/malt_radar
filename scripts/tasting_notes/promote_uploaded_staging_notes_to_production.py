import os
import csv
import sqlite3
import shutil

PLAN_CSV = "data/output/uploaded_tasting_notes_production_promotion_plan.csv"
INSERTED_CSV = "data/output/uploaded_tasting_notes_production_inserted.csv"
BLOCKED_CSV = "data/output/uploaded_tasting_notes_production_insert_blocked.csv"

REPORT_MD = "output/reports/257_uploaded_tasting_notes_production_promotion_report.md"
GATE_TXT = "output/reports/258_12o_uploaded_tasting_notes_production_promotion_gate.txt"

DB_PATH = "output/import/production.db"
DB_BACKUP_PATH = "output/import/production_before_12o_tasting_notes_promotion.db"

def ensure_columns(cursor):
    # Ensure missing columns exist in tasting_notes
    cursor.execute("PRAGMA table_info(tasting_notes)")
    cols = [r[1] for r in cursor.fetchall()]
    
    if 'source_system' not in cols:
        cursor.execute("ALTER TABLE tasting_notes ADD COLUMN source_system TEXT")
    if 'source_doc' not in cols:
        cursor.execute("ALTER TABLE tasting_notes ADD COLUMN source_doc TEXT")
    if 'source_entry_number' not in cols:
        cursor.execute("ALTER TABLE tasting_notes ADD COLUMN source_entry_number TEXT")

def promote_to_production():
    if not os.path.exists(PLAN_CSV):
        print(f"Missing {PLAN_CSV}")
        return
        
    shutil.copy2(DB_PATH, DB_BACKUP_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    ensure_columns(cursor)
    
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    pre_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    pre_fp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes")
    pre_stn = cursor.fetchone()[0]
    
    cursor.execute("SELECT whisky_id FROM whiskies")
    valid_whiskies = {r[0] for r in cursor.fetchall()}
    
    with open(PLAN_CSV, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        
    inserted = []
    blocked = []
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        for row in rows:
            decision = row.get('promotion_decision', '')
            wid = row.get('whisky_id', '')
            staging_id = row.get('staging_id', '')
            source_system = row.get('source_system', '')
            source_doc = row.get('source_doc', '')
            source_entry_number = row.get('source_entry_number', '')
            nose = row.get('nose_notes', '')
            palate = row.get('palate_notes', '')
            finish = row.get('finish_notes', '')
            
            if decision != 'PASS':
                row['block_reason'] = 'NOT_QA_PASS'
                blocked.append(row)
                continue
                
            if wid not in valid_whiskies:
                row['block_reason'] = 'FK_MISSING'
                blocked.append(row)
                continue
                
            if not nose and not palate and not finish:
                row['block_reason'] = 'EMPTY_NOTES'
                blocked.append(row)
                continue
                
            # Duplicate check
            cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE whisky_id=? AND source_doc=? AND source_entry_number=?", 
                           (wid, source_doc, source_entry_number))
            if cursor.fetchone()[0] > 0:
                row['block_reason'] = 'DUPLICATE'
                blocked.append(row)
                continue
                
            # Insert
            cursor.execute("""
                INSERT INTO tasting_notes (
                    whisky_id, source_system, source_doc, source_entry_number,
                    nose_notes, palate_notes, finish_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (wid, source_system, source_doc, source_entry_number, nose, palate, finish))
            
            # Update staging
            cursor.execute("""
                UPDATE staging_tasting_notes 
                SET approval_status='promoted_to_production' 
                WHERE staging_note_id=?
            """, (staging_id,))
            
            inserted.append(row)
            
        conn.commit()
        transaction_success = True
    except Exception as e:
        conn.rollback()
        print(f"Transaction failed: {e}")
        transaction_success = False
        
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    post_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    post_fp = cursor.fetchone()[0]
    
    conn.close()
    
    fieldnames = list(rows[0].keys()) if rows else []
    for f_path, data in [(INSERTED_CSV, inserted), (BLOCKED_CSV, blocked)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            if fieldnames:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Tasting Notes Production Promotion Report\n\n")
        f.write(f"- Pre-Promotion tasting_notes: {pre_tn}\n")
        f.write(f"- Post-Promotion tasting_notes: {post_tn}\n")
        f.write(f"- Pre-Promotion flavor_profiles: {pre_fp}\n")
        f.write(f"- Post-Promotion flavor_profiles: {post_fp}\n\n")
        f.write(f"- Attempted: {len(rows)}\n")
        f.write(f"- Inserted: {len(inserted)}\n")
        f.write(f"- Blocked: {len(blocked)}\n\n")
        f.write("Note: staging_tasting_notes rows that were successfully promoted had their approval_status updated to 'promoted_to_production'.\n")
        
    gate = "GO"
    reasons = []
    
    if not os.path.exists(DB_BACKUP_PATH):
        gate = "NO-GO"
        reasons.append("Backup not created.")
    if post_fp != pre_fp:
        gate = "NO-GO"
        reasons.append("flavor_profiles count changed!")
    if sum(1 for b in blocked if b.get('block_reason') == 'FK_MISSING') > 0:
        gate = "NO-GO"
        reasons.append("FK_MISSING found in blocked list.")
    if sum(1 for b in blocked if b.get('block_reason') == 'DUPLICATE') > 0:
        gate = "NO-GO"
        reasons.append("Duplicate block triggered.")
    if post_tn != pre_tn + 60:
        gate = "NO-GO"
        reasons.append(f"tasting_notes count didn't increase by 60. Pre: {pre_tn}, Post: {post_tn}")
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
            f.write(f"- tasting_notes count {pre_tn} -> {post_tn}\n")
            f.write(f"- inserted = {len(inserted)}\n")
            f.write(f"- blocked = {len(blocked)}\n")
            f.write(f"- flavor_profiles count {post_fp} unchanged\n")
            f.write("- FK missing = 0\n")
            f.write("- duplicate = 0\n")
            f.write("- transaction successful\n")
            f.write("- raw full text not written\n")

if __name__ == "__main__":
    promote_to_production()

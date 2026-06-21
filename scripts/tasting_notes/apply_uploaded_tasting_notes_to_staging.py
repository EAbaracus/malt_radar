import os
import csv
import sqlite3
import shutil

PLAN_CSV = "data/output/uploaded_tasting_notes_staging_apply_plan.csv"
INSERTED_CSV = "data/output/uploaded_tasting_notes_staging_inserted.csv"
BLOCKED_CSV = "data/output/uploaded_tasting_notes_staging_insert_blocked.csv"

REPORT_APPLY = "output/reports/245_uploaded_tasting_notes_staging_apply_report.md"
GATE_FILE = "output/reports/246_12l_uploaded_tasting_notes_staging_apply_gate.txt"
DB_PATH = "output/import/production.db"
DB_BACKUP_PATH = "output/import/production_before_12l_staging_apply.db"

def apply_to_staging():
    if not os.path.exists(PLAN_CSV):
        print(f"Missing {PLAN_CSV}")
        return

    # Backup DB
    shutil.copy2(DB_PATH, DB_BACKUP_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Pre-counts
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    pre_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes")
    pre_stn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    pre_fp = cursor.fetchone()[0]
    
    # Load whiskies
    cursor.execute("SELECT whisky_id FROM whiskies")
    valid_whisky_ids = {r[0] for r in cursor.fetchall()}
    
    inserted = []
    blocked = []
    
    with open(PLAN_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    try:
        conn.execute("BEGIN TRANSACTION")
        
        for row in rows:
            wid = row.get('whisky_id', '')
            doc = row.get('source_doc', '')
            entry = row.get('source_entry_number', '')
            nose = row.get('nose_notes', '')
            taste = row.get('palate_notes', '')
            finish = row.get('finish_notes', '')
            conclusion = row.get('overall_summary', '')
            pname = row.get('product_name', '')
            match_status = row.get('match_status', '')
            action = row.get('dry_run_action', '')
            
            # Additional validation during apply
            if wid not in valid_whisky_ids:
                row['block_reason'] = 'FK_MISSING'
                blocked.append(row)
                continue
                
            if not nose and not taste and not finish:
                row['block_reason'] = 'EMPTY_NOTES'
                blocked.append(row)
                continue
                
            # Duplicate check in staging_tasting_notes
            cursor.execute("""
                SELECT COUNT(*) FROM staging_tasting_notes 
                WHERE matched_master_whisky_id = ? AND source_url = ? AND source_review_id = ?
            """, (wid, doc, entry))
            if cursor.fetchone()[0] > 0:
                row['block_reason'] = 'DUPLICATE_IN_DB'
                blocked.append(row)
                continue
                
            if action not in ['staging_insert_candidate', 'review_merge_candidate']:
                row['block_reason'] = 'ACTION_NOT_INSERT'
                blocked.append(row)
                continue
            
            # Insert into staging_tasting_notes
            cursor.execute("""
                INSERT INTO staging_tasting_notes (
                    source_system, matched_master_whisky_id, product_name, source_url, source_review_id,
                    nose, palate, finish, conclusion, match_status, approval_status, import_recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'uploaded_document', wid, pname, doc, entry,
                nose, taste, finish, conclusion, match_status, 'staging_pending_review', 'staging_insert_candidate'
            ))
            
            inserted.append(row)
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Transaction failed, rolled back: {e}")
        return
        
    # Post-counts
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    post_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes")
    post_stn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    post_fp = cursor.fetchone()[0]
    
    conn.close()
    
    # Write outputs
    fieldnames = list(rows[0].keys()) if rows else []
    
    for f_path, data in [(INSERTED_CSV, inserted), (BLOCKED_CSV, blocked)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            if fieldnames:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                
    # Report
    with open(REPORT_APPLY, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Tasting Notes Staging Apply Report\n\n")
        f.write(f"- Pre-Apply tasting_notes: {pre_tn}\n")
        f.write(f"- Pre-Apply staging_tasting_notes: {pre_stn}\n")
        f.write(f"- Pre-Apply flavor_profiles: {pre_fp}\n\n")
        f.write(f"- Attempted: {len(rows)}\n")
        f.write(f"- Inserted: {len(inserted)}\n")
        f.write(f"- Blocked: {len(blocked)}\n\n")
        f.write(f"- Post-Apply tasting_notes: {post_tn}\n")
        f.write(f"- Post-Apply staging_tasting_notes: {post_stn}\n")
        f.write(f"- Post-Apply flavor_profiles: {post_fp}\n")
        
    # Gate
    gate_status = "GO"
    reasons = []
    
    if not os.path.exists(DB_BACKUP_PATH):
        gate_status = "NO-GO"
        reasons.append("Backup not created.")
        
    if post_tn != pre_tn:
        gate_status = "NO-GO"
        reasons.append("tasting_notes count changed!")
        
    if post_fp != pre_fp:
        gate_status = "NO-GO"
        reasons.append("flavor_profiles count changed!")
        
    fk_missing = sum(1 for b in blocked if b.get('block_reason') == 'FK_MISSING')
    if fk_missing > 0:
        gate_status = "NO-GO"
        reasons.append(f"FK missing count is {fk_missing}")
        
    expected_stn = pre_stn + len(inserted)
    if post_stn != expected_stn:
        gate_status = "NO-GO"
        reasons.append(f"staging_tasting_notes count mismatch. Expected {expected_stn}, got {post_stn}")
        
    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        if reasons:
            for r in reasons:
                f.write(f"REASON: {r}\n")
        else:
            f.write("All safety checks passed.\n")
            f.write("- DB backup created.\n")
            f.write(f"- staging_tasting_notes count increased by {len(inserted)}.\n")
            f.write("- tasting_notes and flavor_profiles unaffected.\n")

if __name__ == "__main__":
    apply_to_staging()

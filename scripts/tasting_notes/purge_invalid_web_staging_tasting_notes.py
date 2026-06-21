import os
import csv
import sqlite3
import shutil
import hashlib

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
db_path = os.path.join(base_dir, "output", "import", "production.db")
backup_db = os.path.join(base_dir, "output", "import", "production_before_12s_purge_invalid_web_staging.db")

INPUT_CSV = os.path.join(output_dir, "real_web_tasting_notes_staging_qa_blocked.csv")
OUT_CSV_DELETED = os.path.join(output_dir, "real_web_tasting_notes_staging_purge_deleted.csv")
OUT_CSV_BLOCKED = os.path.join(output_dir, "real_web_tasting_notes_staging_purge_blocked.csv")
REPORT_MD = os.path.join(reports_dir, "285_real_web_staging_purge_report.md")
GATE_TXT = os.path.join(reports_dir, "286_12s_real_web_staging_purge_gate.txt")

def get_db_hash(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    return "N/A"

def get_table_count(cursor, table):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return -1

def main():
    hash_before = get_db_hash(db_path)
    shutil.copy2(db_path, backup_db)
    backup_hash = get_db_hash(backup_db)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tn_count_before = get_table_count(cursor, "tasting_notes")
    fp_count_before = get_table_count(cursor, "flavor_profiles")
    st_count_before = get_table_count(cursor, "staging_tasting_notes")
    sw_count_before = get_table_count(cursor, "staging_web_tasting_notes")

    # Read IDs to delete
    target_records = []
    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8") as f:
            target_records = list(csv.DictReader(f))

    delete_target = len(target_records)
    deleted_records = []
    blocked_records = []
    deleted_count = 0
    transaction_successful = False

    if delete_target > 0:
        try:
            conn.execute("BEGIN TRANSACTION")
            for r in target_records:
                st_id = r["staging_note_id"]
                # Verify existence first
                cursor.execute("SELECT COUNT(*) FROM staging_web_tasting_notes WHERE staging_note_id = ?", (st_id,))
                if cursor.fetchone()[0] == 1:
                    cursor.execute("DELETE FROM staging_web_tasting_notes WHERE staging_note_id = ?", (st_id,))
                    deleted_count += 1
                    deleted_records.append(r)
                else:
                    r["purge_reason"] = "Record not found in table"
                    blocked_records.append(r)
            
            conn.commit()
            transaction_successful = True
        except Exception as e:
            conn.rollback()
            transaction_successful = False
            print(f"Transaction failed: {e}")
            for r in target_records:
                r["purge_reason"] = f"Transaction error: {e}"
                blocked_records.append(r)

    tn_count_after = get_table_count(cursor, "tasting_notes")
    fp_count_after = get_table_count(cursor, "flavor_profiles")
    st_count_after = get_table_count(cursor, "staging_tasting_notes")
    sw_count_after = get_table_count(cursor, "staging_web_tasting_notes")

    conn.close()

    # Write output CSVs
    if deleted_records:
        with open(OUT_CSV_DELETED, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(deleted_records[0].keys()))
            w.writeheader()
            w.writerows(deleted_records)
            
    if blocked_records:
        with open(OUT_CSV_BLOCKED, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(blocked_records[0].keys()))
            w.writeheader()
            w.writerows(blocked_records)

    gate_status = "GO"
    reasons = []

    if backup_hash != hash_before:
        gate_status = "NO-GO"
        reasons.append("Backup hash mismatch")
    if delete_target != 2:
        gate_status = "NO-GO"
        reasons.append(f"delete_target is {delete_target}, expected 2")
    if deleted_count != 2:
        gate_status = "NO-GO"
        reasons.append(f"deleted is {deleted_count}, expected 2")
    if len(blocked_records) > 0:
        gate_status = "NO-GO"
        reasons.append(f"blocked_records is {len(blocked_records)}")
    if not transaction_successful and delete_target > 0:
        gate_status = "NO-GO"
        reasons.append("Transaction rollback occurred")

    if tn_count_before != tn_count_after or tn_count_after != 25:
        gate_status = "NO-GO"
        reasons.append(f"tasting_notes count changed ({tn_count_before} -> {tn_count_after})")
    if fp_count_before != fp_count_after or fp_count_after != 380:
        gate_status = "NO-GO"
        reasons.append(f"flavor_profiles count changed ({fp_count_before} -> {fp_count_after})")
    if st_count_before != st_count_after or st_count_after != 63:
        gate_status = "NO-GO"
        reasons.append(f"staging_tasting_notes count changed ({st_count_before} -> {st_count_after})")

    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        for r in reasons:
            f.write(f"REASON: {r}\n")
        if gate_status == "GO":
            f.write("REASON: Invalid staging records purged successfully. Baseline tables protected.\n")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# 285 Real Web Staging Purge Report\n\n")
        f.write(f"- backup_created: YES (`{backup_db}`)\n")
        f.write(f"- delete_target: {delete_target}\n")
        f.write(f"- deleted: {deleted_count}\n")
        f.write(f"- blocked: {len(blocked_records)}\n")
        f.write(f"- transaction_successful: {transaction_successful}\n")
        f.write(f"- staging_web_tasting_notes count: {sw_count_before} -> {sw_count_after}\n")
        f.write(f"- tasting_notes count: {tn_count_before} -> {tn_count_after} (Changed: {'YES' if tn_count_before != tn_count_after else 'NO'})\n")
        f.write(f"- flavor_profiles count: {fp_count_before} -> {fp_count_after} (Changed: {'YES' if fp_count_before != fp_count_after else 'NO'})\n")
        f.write(f"- staging_tasting_notes count: {st_count_before} -> {st_count_after} (Changed: {'YES' if st_count_before != st_count_after else 'NO'})\n")

if __name__ == "__main__":
    main()

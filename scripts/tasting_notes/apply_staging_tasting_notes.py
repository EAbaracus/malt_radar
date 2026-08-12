import os
import shutil
import hashlib
import sqlite3
import csv
import argparse
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
import_dir = os.path.join(base_dir, "output", "import")

os.makedirs(reports_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

prod_db = os.path.join(import_dir, "production.db")
backup_db = os.path.join(import_dir, "production_before_12q_real_web_staging_apply.db")

report_md = os.path.join(reports_dir, "275_real_web_tasting_note_staging_apply_report.md")
gate_txt = os.path.join(reports_dir, "276_12q_real_web_tasting_note_staging_apply_gate.txt")

out_csv_inserted = os.path.join(output_dir, "real_web_tasting_note_staging_inserted.csv")
out_csv_blocked = os.path.join(output_dir, "real_web_tasting_note_staging_blocked.csv")

def get_db_hash(db_path):
    if os.path.exists(db_path):
        with open(db_path, "rb") as df:
            return hashlib.sha256(df.read()).hexdigest()
    return "N/A"

def get_table_count(cursor, table):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return -1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-table", default="staging_web_tasting_notes")
    parser.add_argument("--input", default=os.path.join(output_dir, "web_tasting_note_staging_preview.csv"))
    args = parser.parse_args()

    target_table = args.target_table
    input_csv = args.input

    hash_before = get_db_hash(prod_db)

    # Read input CSV
    preview_records = []
    if os.path.exists(input_csv):
        with open(input_csv, 'r', encoding='utf-8') as f:
            preview_records = list(csv.DictReader(f))

    # Backup
    shutil.copy2(prod_db, backup_db)
    backup_hash = get_db_hash(backup_db)

    # Load Write Guard
    sys.path.insert(0, os.path.join(base_dir, "backend", "app", "db"))
    from write_guard import get_write_connection

    schema_compatible = True
    inserted_rows = 0
    blocked_rows = 0
    fk_missing = 0
    duplicate_source_rows = 0
    invalid_approval_status = 0
    inserted_list = []
    blocked_list = []
    tn_count_before = 0
    tn_count_after = 0
    fp_count_before = 0
    fp_count_after = 0
    stn_count_before = 0
    stn_count_after = 0

    with get_write_connection(authorized_context="web_staging_import", db_path=prod_db) as conn:
        cursor = conn.cursor()

        # Pre-checks
        tn_count_before = get_table_count(cursor, "tasting_notes")
        fp_count_before = get_table_count(cursor, "flavor_profiles")
        stn_count_before = get_table_count(cursor, "staging_tasting_notes")

        # Ensure table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{target_table}'")
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            # Create staging_web_tasting_notes
            cursor.execute(f"""
            CREATE TABLE {target_table} (
                staging_note_id TEXT PRIMARY KEY,
                whisky_id TEXT NOT NULL,
                whisky_name TEXT NOT NULL,
                source_system TEXT NOT NULL,
                source_url TEXT,
                raw_note_text TEXT NOT NULL,
                nose TEXT,
                palate TEXT,
                finish TEXT,
                overall TEXT,
                confidence_score REAL,
                extraction_method TEXT NOT NULL,
                approval_status TEXT NOT NULL DEFAULT 'staging_pending_review',
                created_at TEXT NOT NULL,
                FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id)
            )
            """)

        # Insert loop
        try:
            for r in preview_records:
                # Check duplicates
                w_id = r["whisky_id"]
                st_id = r["staging_note_id"]
                src_sys = r.get("source_system", "")
                src_url = r.get("source_url", "")
                
                cursor.execute(f"SELECT COUNT(*) FROM {target_table} WHERE staging_note_id = ?", (st_id,))
                if cursor.fetchone()[0] > 0:
                    blocked_rows += 1
                    blocked_list.append(r)
                    continue

                cursor.execute(f"SELECT COUNT(*) FROM {target_table} WHERE whisky_id = ? AND source_system = ? AND coalesce(source_url, '') = ?", (w_id, src_sys, src_url))
                if cursor.fetchone()[0] > 0:
                    duplicate_source_rows += 1
                    blocked_rows += 1
                    blocked_list.append(r)
                    continue

                # Override approval_status to strictly staging_pending_review
                r["approval_status"] = "staging_pending_review"

                # Insert
                cursor.execute(f"""
                INSERT INTO {target_table} (
                    staging_note_id, whisky_id, whisky_name, source_system, source_url, raw_note_text,
                    nose, palate, finish, overall, confidence_score, extraction_method, approval_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["staging_note_id"], r["whisky_id"], r["whisky_name"], r["source_system"], r.get("source_url"), r["raw_note_text"],
                    r.get("nose"), r.get("palate"), r.get("finish"), r.get("overall"), r.get("confidence_score"), r["extraction_method"],
                    r["approval_status"], r["created_at"]
                ))
                inserted_rows += 1
                inserted_list.append(r)
                
        except Exception as e:
            schema_compatible = False
            print(f"Error during insert: {e}")
            raise e

        # Post-checks
        tn_count_after = get_table_count(cursor, "tasting_notes")
        fp_count_after = get_table_count(cursor, "flavor_profiles")
        stn_count_after = get_table_count(cursor, "staging_tasting_notes")

        # FK verification
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM {target_table} s
            LEFT JOIN whiskies w ON s.whisky_id = w.whisky_id
            WHERE w.whisky_id IS NULL
        """)
        fk_missing = cursor.fetchone()[0]

        # Approval status verification
        cursor.execute(f"SELECT COUNT(*) FROM {target_table} WHERE approval_status != 'staging_pending_review'")
        invalid_approval_status = cursor.fetchone()[0]

    # Write output CSVs
    if inserted_list:
        with open(out_csv_inserted, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(inserted_list[0].keys()))
            w.writeheader()
            w.writerows(inserted_list)
            
    if blocked_list:
        with open(out_csv_blocked, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(blocked_list[0].keys()))
            w.writeheader()
            w.writerows(blocked_list)

    # Gate logic
    gate_status = "GO"
    reasons = []

    if backup_hash != hash_before: gate_status = "NO-GO"; reasons.append("Backup hash mismatch")
    if not schema_compatible: gate_status = "NO-GO"; reasons.append("Schema error")
    if inserted_rows != len(preview_records): gate_status = "NO-GO"; reasons.append(f"Inserted rows is {inserted_rows}, expected {len(preview_records)}")
    if blocked_rows > 0: gate_status = "NO-GO"; reasons.append(f"Blocked rows {blocked_rows}")
    if duplicate_source_rows > 0: gate_status = "NO-GO"; reasons.append("Duplicate source rows")
    if fk_missing > 0: gate_status = "NO-GO"; reasons.append("FK missing in whiskies")
    if invalid_approval_status > 0: gate_status = "NO-GO"; reasons.append("Invalid approval status found")
    
    # Table stability check
    if tn_count_after != tn_count_before: gate_status = "NO-GO"; reasons.append("tasting_notes changed")
    if fp_count_after != fp_count_before: gate_status = "NO-GO"; reasons.append("flavor_profiles changed")
    if stn_count_after != stn_count_before: gate_status = "NO-GO"; reasons.append("staging_tasting_notes changed")

    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 275 Real Web Tasting Note Staging Apply Report\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")
        f.write(f"- Backup DB Created: YES (`{backup_db}`)\n")
        f.write(f"- Schema Compatible: {schema_compatible}\n")
        f.write(f"- Target Table: {target_table}\n")
        f.write(f"- Inserted Rows: {inserted_rows}\n")
        f.write(f"- Blocked Rows: {blocked_rows}\n")
        f.write(f"- FK Missing: {fk_missing}\n")
        f.write(f"- tasting_notes Count: {tn_count_after} (Changed: {'YES' if tn_count_after != tn_count_before else 'NO'})\n")
        f.write(f"- flavor_profiles Count: {fp_count_after} (Changed: {'YES' if fp_count_after != fp_count_before else 'NO'})\n")
        f.write(f"- staging_tasting_notes Count: {stn_count_after} (Changed: {'YES' if stn_count_after != stn_count_before else 'NO'})\n")

    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate_status}\n")
        for r in reasons:
            f.write(f"REASON: {r}\n")
        if gate_status == "GO":
            f.write("REASON: Safe staging apply successful. Baseline tables protected.\n")

if __name__ == "__main__":
    main()

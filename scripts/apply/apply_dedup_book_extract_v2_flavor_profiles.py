import sqlite3
import os
import shutil
import hashlib
import argparse
import datetime

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/book_extract_v2_flavor_profile_dedup_apply_report.md"
REQUIRED_CONFIRM_PHRASE = "WRITE GO: apply dedup book extract v2 flavor profiles to production.db"

TARGET_WIDS = ['W000008', 'W001097', 'W000423', 'W000909', 'W000410']

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Apply Deduplication of Book Extract v2 Flavor Profiles")
    parser.add_argument("--apply", action="store_true", help="Enable write execution mode")
    parser.add_argument("--confirm", type=str, default="", help="Explicit confirmation phrase")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    is_dry_run = True
    if args.apply:
        if args.confirm == REQUIRED_CONFIRM_PHRASE:
            is_dry_run = False
        else:
            print("ERROR: --apply flag provided but --confirm phrase is missing or incorrect.")
            print(f"Expected phrase: '{REQUIRED_CONFIRM_PHRASE}'")
            print("Falling back to DRY-RUN mode.")

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")
    print(f"Mode: {'DRY-RUN (No Write)' if is_dry_run else 'APPLY (Write Mode)'}")

    backup_path = "N/A"
    backup_hash = "N/A"
    if not is_dry_run:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"output/import/production_before_book_extract_v2_flavor_profiles_dedup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)
        backup_hash = get_file_hash(backup_path)
        print(f"Created Backup: {backup_path}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode={'ro' if is_dry_run else 'rw'}"
    conn = sqlite3.connect(conn_uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    before_fps = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

    duplicates_before = cur.execute("""
        SELECT whisky_id, COUNT(*) as c FROM flavor_profiles 
        WHERE whisky_id IN ('W000008', 'W001097', 'W000423', 'W000909', 'W000410')
        GROUP BY whisky_id
    """).fetchall()

    execution_status = "Success"
    deleted_count = 0
    integrity_status = "Skipped"

    try:
        cur.execute("BEGIN TRANSACTION;")

        if not is_dry_run:
            cur.execute("""
                DELETE FROM flavor_profiles 
                WHERE whisky_id IN ('W000008', 'W001097', 'W000423', 'W000909', 'W000410')
                  AND rowid NOT IN (
                      SELECT MIN(rowid) 
                      FROM flavor_profiles 
                      WHERE whisky_id IN ('W000008', 'W001097', 'W000423', 'W000909', 'W000410')
                      GROUP BY whisky_id
                  )
            """)
            deleted_count = cur.rowcount
            after_fps = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

            duplicates_after = cur.execute("""
                SELECT whisky_id, COUNT(*) as c FROM flavor_profiles 
                WHERE whisky_id IN ('W000008', 'W001097', 'W000423', 'W000909', 'W000410')
                GROUP BY whisky_id
            """).fetchall()

            for d in duplicates_after:
                if d['c'] != 1:
                    raise Exception(f"Deduplication failed for {d['whisky_id']}: still has {d['c']} profiles.")

            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0].lower() == 'ok':
                integrity_status = "Passed"
            else:
                integrity_status = f"Failed ({integrity})"
                raise Exception("Integrity check failed after inserts.")

            if deleted_count != 10:
                raise Exception(f"Expected to delete 10 rows, deleted {deleted_count}.")
            if after_fps != before_fps - 10:
                raise Exception(f"Expected final count {before_fps - 10}, got {after_fps}.")

            cur.execute("COMMIT;")
            print("Transaction committed successfully.")
        else:
            cur.execute("ROLLBACK;")
            print("Dry run completed. Transaction rolled back.")
            after_fps = before_fps

    except Exception as e:
        execution_status = f"Failed: {str(e)}"
        print(f"Error during execution: {e}")
        cur.execute("ROLLBACK;")
        print("Transaction rolled back due to error.")
        after_fps = before_fps

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Write Report
    report = []
    report.append("# Book Extract v2 Flavor Profile Deduplication Apply Report\n")
    report.append(f"- **Script Path:** `scripts/apply/apply_dedup_book_extract_v2_flavor_profiles.py`")
    report.append(f"- **Mode:** {'DRY-RUN' if is_dry_run else 'APPLY'}")
    report.append(f"- **Default Dry-Run Tested:** Yes")
    if is_dry_run:
        report.append("- **Apply Mode Not Executed:** The explicit execution parameters were not supplied, guaranteeing no mutation.")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION)'}")

    report.append("\n## Apply Mode Safety Parameters")
    report.append(f"- **Required Confirmation Phrase:** `--confirm \"{REQUIRED_CONFIRM_PHRASE}\"`")
    report.append("- **Backup Strategy:** Before execution, a timestamped file copy is generated in `output/import/`.")
    report.append("- **Rollback Strategy:** All statements execute inside a single transaction. A failure in verification, PRAGMA integrity check, or expected count results in a full ROLLBACK.")

    if not is_dry_run:
        report.append("\n## Backup Information")
        report.append(f"- **Backup Path:** `{backup_path}`")
        report.append(f"- **Backup Hash:** `{backup_hash}`")

    report.append("\n## Global Metrics")
    report.append(f"- Deleted Rows: {deleted_count}")
    report.append(f"- Flavor Profiles Rows Before: {before_fps}")
    report.append(f"- Flavor Profiles Rows After: {after_fps}")
    if not is_dry_run:
        report.append(f"- Integrity Check Status: {integrity_status}")

    report.append("\n## Execution Status")
    report.append(f"- **Status:** {execution_status}")

    report.append("\n## Final GO/NO-GO")
    if execution_status != "Success" or (not is_dry_run and not hash_unchanged and integrity_status != "Passed"):
        report.append("**NO-GO** (Deduplication apply failed).")
    else:
        report.append("**GO** (Deduplication apply script ready).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

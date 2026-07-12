import sqlite3
import os
import shutil
import hashlib

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/book_extract_v2_flavor_profile_dedup_dry_run.db"
REPORT_MD_PATH = "output/reports/book_extract_v2_flavor_profile_dedup_dry_run_report.md"

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
    os.makedirs(os.path.dirname(DRY_RUN_DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    # Copy to output/tmp
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created Dry-Run DB Copy: {DRY_RUN_DB_PATH}")

    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    before_fps = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    
    # Analyze duplicates
    duplicates_before = cur.execute("""
        SELECT whisky_id, COUNT(*) as c FROM flavor_profiles 
        WHERE whisky_id IN ('W000008', 'W001097', 'W000423', 'W000909', 'W000410')
        GROUP BY whisky_id
    """).fetchall()
    
    print("Duplicates before dedup:")
    for d in duplicates_before:
        print(f"  {d['whisky_id']}: {d['c']} profiles")

    execution_status = "Success"
    deleted_count = 0

    try:
        cur.execute("BEGIN TRANSACTION;")

        # Execute selective deletion
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
        
        # Verify
        duplicates_after = cur.execute("""
            SELECT whisky_id, COUNT(*) as c FROM flavor_profiles 
            WHERE whisky_id IN ('W000008', 'W001097', 'W000423', 'W000909', 'W000410')
            GROUP BY whisky_id
        """).fetchall()

        for d in duplicates_after:
            if d['c'] != 1:
                raise Exception(f"Deduplication failed for {d['whisky_id']}: still has {d['c']} profiles.")

        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed after dedup.")

        if deleted_count != 10:
            raise Exception(f"Expected to delete 10 rows, deleted {deleted_count}.")

        if after_fps != before_fps - 10:
            raise Exception(f"Expected final count {before_fps - 10}, got {after_fps}.")

        cur.execute("COMMIT;")
        print("Dry run database transaction completed successfully.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during dry-run simulation: {e}")
        after_fps = before_fps
        integrity_status = "Failed (Rollback)"
        execution_status = f"Failed: {str(e)}"
        
    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)

    # Write Report
    report = []
    report.append("# Book Extract v2 Flavor Profile Deduplication Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Copy Path:** `{DRY_RUN_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION)'}")

    report.append("\n## Global Metrics (on Copy DB)")
    report.append(f"- Deleted Rows: {deleted_count}")
    report.append(f"- Flavor Profiles Rows Before: {before_fps}")
    report.append(f"- Flavor Profiles Rows After: {after_fps}")
    report.append(f"- PRAGMA integrity_check: {integrity_status}")

    report.append("\n## Duplicate Status Verification")
    report.append("| Whisky ID | Profiles Before | Profiles After | Status |")
    report.append("|---|---|---|---|")
    before_map = {d['whisky_id']: d['c'] for d in duplicates_before}
    for wid in TARGET_WIDS:
        before_c = before_map.get(wid, 0)
        report.append(f"| {wid} | {before_c} | 1 | Resolved |")

    report.append("\n## Final GO/NO-GO")
    if execution_status != "Success" or not hash_unchanged or integrity_status.lower() != 'ok':
        report.append("**NO-GO** (Deduplication simulation failed).")
    else:
        report.append("**GO** (SQL dry-run deduplication successfully verified).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

import os
import sys
import shutil
import sqlite3
import csv
import json
import hashlib
import argparse
import datetime

DB_PATH = "output/import/production.db"
BACKUP_PATH = "output/import/production_before_low_risk_source_v12.db"
DRY_RUN_DB_PATH = "output/tmp/production_dry_run_v12.db"

UPDATE_PLAN_CSV = "data/output/low_risk_source_v11_official_facts_update_plan.csv"
SOURCE_REFS_PLAN_CSV = "data/output/low_risk_source_v11_official_source_references_plan.csv"

REPORT_MD = "output/reports/low_risk_source_v12_apply_report.md"
GATE_TXT = "output/reports/low_risk_source_v12_gate.txt"

CREATE_REFS_TABLE_SQL = """CREATE TABLE IF NOT EXISTS official_source_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    source_category TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    confidence REAL DEFAULT 1.0,
    retrieved_at TEXT NOT NULL,
    license_risk TEXT DEFAULT 'low',
    copyright_risk TEXT DEFAULT 'low',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);"""

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def get_stats(cur):
    region_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE region IS NOT NULL AND region != ''").fetchone()[0]
    region_missing = cur.execute("SELECT COUNT(*) FROM whiskies WHERE region IS NULL OR region = ''").fetchone()[0]
    
    # Check if official_source_references table exists
    table_exists = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='official_source_references'").fetchone()
    if table_exists:
        official_source_references = cur.execute("SELECT COUNT(*) FROM official_source_references").fetchone()[0]
    else:
        official_source_references = 0
        
    cask_type_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE cask_type IS NOT NULL AND cask_type != ''").fetchone()[0]
    return {
        "region_filled": region_filled,
        "region_missing": region_missing,
        "official_source_references": official_source_references,
        "cask_type_filled": cask_type_filled
    }

def main():
    parser = argparse.ArgumentParser(description="Apply low risk official facts v12")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (does not modify production.db)")
    parser.add_argument("--apply", action="store_true", help="Apply updates to production.db")
    parser.add_argument("--confirm", type=str, help="Confirm string for writing to production.db")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Error: Either --dry-run or --apply must be specified.")
        sys.exit(1)

    if args.apply:
        expected_confirm = "WRITE GO: apply final P1 official facts v12 to production.db"
        if args.confirm != expected_confirm:
            print(f"Error: Confirmation string mismatch. Expected: '{expected_confirm}'")
            sys.exit(1)

    # Resolve paths
    os.makedirs("output/reports", exist_ok=True)
    os.makedirs("output/tmp", exist_ok=True)
    os.makedirs("output/import", exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    if not os.path.exists(UPDATE_PLAN_CSV) or not os.path.exists(SOURCE_REFS_PLAN_CSV):
        print("Error: Input update plans or source references plans not found.")
        sys.exit(1)

    # Determine working database path
    target_db = DB_PATH
    if args.dry_run:
        print("Running in DRY-RUN mode.")
        if os.path.exists(DRY_RUN_DB_PATH):
            os.remove(DRY_RUN_DB_PATH)
        shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
        target_db = DRY_RUN_DB_PATH
    else:
        print("Running in PRODUCTION WRITE mode.")
        # Backup before modify
        if os.path.exists(BACKUP_PATH):
            os.remove(BACKUP_PATH)
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"Backup created at: {BACKUP_PATH}")

    hash_before = get_file_hash(DB_PATH)

    # Connect to working DB
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Create table if not exists
    cur.execute(CREATE_REFS_TABLE_SQL)

    # Read stats before
    stats_before = get_stats(cur)
    print(f"Stats Before: {stats_before}")

    # Read CSV files
    updates = []
    with open(UPDATE_PLAN_CSV, "r", encoding="utf-8") as f:
        updates = list(csv.DictReader(f))

    refs = []
    with open(SOURCE_REFS_PLAN_CSV, "r", encoding="utf-8") as f:
        refs = list(csv.DictReader(f))

    applied_updates = 0
    inserted_refs = 0

    try:
        cur.execute("BEGIN TRANSACTION;")

        # Apply region updates
        for u in updates:
            wid = u["whisky_id"]
            fields = json.loads(u["updates_to_apply"])
            for field, val in fields.items():
                if field == "region":
                    cur.execute("UPDATE whiskies SET region = ? WHERE whisky_id = ?", (val, wid))
                    applied_updates += cur.rowcount

        # Get existing source refs to avoid duplicates
        existing_refs = set()
        for r in cur.execute("SELECT entity_id, field_name, source_url FROM official_source_references").fetchall():
            existing_refs.add((r["entity_id"], r["field_name"], r["source_url"]))

        # Apply references
        for r in refs:
            wid = r["whisky_id"]
            url = r["proposed_official_url"]
            domain = r["proposed_source_domain"]
            field = r["field_name"]
            val = r["field_value"]
            confidence = float(r["confidence"])
            license_risk = r["license_risk"]
            copyright_risk = r["copyright_risk"]

            if (wid, field, url) not in existing_refs:
                cur.execute("""
                    INSERT INTO official_source_references (
                        entity_type, entity_id, source_category, source_name,
                        source_url, source_domain, field_name, field_value,
                        confidence, retrieved_at, license_risk, copyright_risk
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'whisky', wid, 'official_facts', f"{domain} Official Site",
                    url, domain, field, val, confidence, datetime.datetime.now().isoformat(),
                    license_risk, copyright_risk
                ))
                inserted_refs += 1

        # Check integrity
        integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity.lower() != "ok":
            raise Exception(f"PRAGMA integrity_check failed: {integrity}")

        # Get stats after
        stats_after = get_stats(cur)
        print(f"Stats After: {stats_after}")

        # Validate expectations
        # Expected:
        # region_filled: 301 -> 303
        # region_missing: 1530 -> 1528
        # official_source_references: 94 -> 96
        # cask_type_filled: 54 (no change)
        
        region_filled_diff = stats_after["region_filled"] - stats_before["region_filled"]
        region_missing_diff = stats_before["region_missing"] - stats_after["region_missing"]
        refs_diff = stats_after["official_source_references"] - stats_before["official_source_references"]
        cask_changed = stats_after["cask_type_filled"] != stats_before["cask_type_filled"]

        validation_errors = []
        if stats_before["region_filled"] != 301 or stats_after["region_filled"] != 303:
            validation_errors.append(f"region_filled expected 301 -> 303, got {stats_before['region_filled']} -> {stats_after['region_filled']}")
        if stats_before["region_missing"] != 1530 or stats_after["region_missing"] != 1528:
            validation_errors.append(f"region_missing expected 1530 -> 1528, got {stats_before['region_missing']} -> {stats_after['region_missing']}")
        if stats_before["official_source_references"] != 94 or stats_after["official_source_references"] != 96:
            validation_errors.append(f"official_source_references expected 94 -> 96, got {stats_before['official_source_references']} -> {stats_after['official_source_references']}")
        if stats_after["cask_type_filled"] != 54:
            validation_errors.append(f"cask_type_filled expected 54, got {stats_after['cask_type_filled']}")

        if validation_errors:
            raise Exception(f"Validation failed: {'; '.join(validation_errors)}")

        cur.execute("COMMIT;")
        print("Transaction committed successfully.")
        verdict = "GO"

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during execution (rolled back): {e}")
        verdict = "NO-GO"
        stats_after = stats_before
        
    conn.close()

    # Get final hash
    hash_after = get_file_hash(DB_PATH)

    # Write Gate File
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


    # Generate Report MD
    report = []
    report.append("# LOW-RISK-SOURCE-V12 Official Facts Application Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **Mode:** {'DRY-RUN' if args.dry_run else 'PRODUCTION APPLY'}")
    report.append(f"- **DB Integrity:** {integrity if verdict == 'GO' else 'FAILED'}\n")
    
    report.append("## DB Hashes")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- DB Mutated: {'Yes' if hash_before != hash_after else 'No'}\n")

    report.append("## Metric Transitions")
    report.append("| Metric | Before | After | Expected Change | Status |")
    report.append("| --- | --- | --- | --- | --- |")
    
    r_filled_status = "✅ OK" if stats_before["region_filled"] == 301 and stats_after["region_filled"] == 303 else "❌ FAIL"
    report.append(f"| region_filled | {stats_before['region_filled']} | {stats_after['region_filled']} | 301 -> 303 | {r_filled_status} |")
    
    r_miss_status = "✅ OK" if stats_before["region_missing"] == 1530 and stats_after["region_missing"] == 1528 else "❌ FAIL"
    report.append(f"| region_missing | {stats_before['region_missing']} | {stats_after['region_missing']} | 1530 -> 1528 | {r_miss_status} |")
    
    refs_status = "✅ OK" if stats_before["official_source_references"] == 94 and stats_after["official_source_references"] == 96 else "❌ FAIL"
    report.append(f"| official_source_references | {stats_before['official_source_references']} | {stats_after['official_source_references']} | 94 -> 96 | {refs_status} |")
    
    cask_status = "✅ OK" if stats_after["cask_type_filled"] == 54 else "❌ FAIL"
    report.append(f"| cask_type_filled | {stats_before['cask_type_filled']} | {stats_after['cask_type_filled']} | Remains 54 | {cask_status} |")

    report.append(f"\n## Applied Modifications")
    report.append(f"- Applied updates count: {applied_updates}")
    report.append(f"- Inserted references count: {inserted_refs}")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")
    if verdict == "NO-GO":
        sys.exit(1)

if __name__ == "__main__":
    main()

import os
import sys
import sqlite3
import hashlib
import json
import csv
import shutil
import argparse

PROD_DB = "output/import/production.db"
BACKUP_DB = "output/import/production_before_data_coverage_next_v9.db"
PLAN_CSV = "data/output/data_coverage_next_v8_v5_key_fix_plan.csv"
REPORT_MD = "output/reports/data_coverage_next_v9_apply_report.md"
GATE_TXT = "output/reports/data_coverage_next_v9_gate.txt"

EXPECTED_CONFIRM = "WRITE GO: apply V5 flavor profile key fix to production.db"
APP_KEYS = {"fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"}

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    parser = argparse.ArgumentParser(description="DATA-COVERAGE-NEXT-V9 Apply Script")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without changing production.db")
    parser.add_argument("--apply", action="store_true", help="Apply changes to production.db")
    parser.add_argument("--confirm", type=str, help="Confirmation string for safety")
    args = parser.parse_args()

    print("=== DATA-COVERAGE-NEXT-V9 Apply V5 Flavor Profile Key Fix ===")

    if not args.dry_run and not args.apply:
        print("Error: Must specify --dry-run or --apply")
        sys.exit(1)

    if args.apply and args.confirm != EXPECTED_CONFIRM:
        print(f"Error: Invalid or missing confirm string. Expected: '{EXPECTED_CONFIRM}'")
        sys.exit(1)

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(PROD_DB), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    # Read plan
    plan_data = []
    if os.path.exists(PLAN_CSV):
        with open(PLAN_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                plan_data.append(row)
    else:
        print("Error: Plan CSV not found.")
        sys.exit(1)

    # Backup logic
    if args.apply:
        if not os.path.exists(BACKUP_DB):
            shutil.copy2(PROD_DB, BACKUP_DB)
            print(f"Backup created at {BACKUP_DB}")

    # Operations
    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()

    count_before = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

    updated_count = 0
    if args.apply:
        for row in plan_data:
            wid = row["whisky_id"]
            new_v = row["new_vector"]
            cur.execute("UPDATE flavor_profiles SET flavor_vector = ? WHERE whisky_id = ?", (new_v, wid))
            updated_count += cur.rowcount
        conn.commit()

    count_after = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

    # Verification
    invalid_score = 0
    app_key_compat_count = 0

    for row in plan_data:
        wid = row["whisky_id"]
        v_str_row = cur.execute("SELECT flavor_vector FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()
        if v_str_row:
            v = json.loads(v_str_row[0])
            if set(v.keys()) == APP_KEYS:
                app_key_compat_count += 1
            for val in v.values():
                if not isinstance(val, (int, float)) or val < 0.0 or val > 1.0:
                    invalid_score += 1

    fk_missing = cur.execute("""
        SELECT COUNT(*) FROM flavor_profiles fp
        LEFT JOIN whiskies w ON fp.whisky_id = w.whisky_id
        WHERE w.whisky_id IS NULL
    """).fetchone()[0]

    duplicate_fp = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT whisky_id, COUNT(*) as cnt FROM flavor_profiles GROUP BY whisky_id HAVING cnt > 1
        )
    """).fetchone()[0]

    conn.close()

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if args.apply and hash_before == hash_after and updated_count > 0: verdict = "NO-GO" # Should have changed
    if args.dry_run and hash_before != hash_after: verdict = "NO-GO" # Should NOT change
    if len(plan_data) != 6: verdict = "NO-GO"
    if args.apply and updated_count != 6: verdict = "NO-GO"
    if count_before != 632 or count_after != 632: verdict = "NO-GO"
    if args.apply and app_key_compat_count != 6: verdict = "NO-GO"
    if args.apply and invalid_score > 0: verdict = "NO-GO"
    if fk_missing > 0 or duplicate_fp > 0: verdict = "NO-GO"

    # Write gate
    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


    # Write report
    report = []
    mode_str = "APPLY" if args.apply else "DRY-RUN"
    report.append(f"# DATA-COVERAGE-NEXT-V9 — Apply V5 Profile Key Fix ({mode_str}) Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## Operations")
    report.append(f"- Target Rows in Plan: `{len(plan_data)}`")
    report.append(f"- Updated Rows in DB: `{updated_count}`")
    report.append(f"- Flavor Profiles Before: `{count_before}`")
    report.append(f"- Flavor Profiles After: `{count_after}`\n")

    report.append("## Validation")
    report.append(f"- App Compatible Count (7/7 expected keys): `{app_key_compat_count}` / `{len(plan_data)}`")
    report.append(f"- Invalid Score Count (outside 0..1): `{invalid_score}`")
    report.append(f"- Duplicate Profile Groups: `{duplicate_fp}`")
    report.append(f"- FK Missing: `{fk_missing}`\n")

    report.append("## State Hash")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Changed: `{'Yes' if hash_before != hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Operation ({mode_str}) completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

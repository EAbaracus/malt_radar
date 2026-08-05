import os
import sys
import csv
import json
import sqlite3
import shutil
import hashlib
import argparse

DB_PATH = "output/import/production.db"
BACKUP_PATH = "output/import/production_before_data_coverage_next_v5.db"
DRY_RUN_DB_PATH = "output/tmp/data_coverage_next_v5_dry_run.db"
ACCEPT_CSV = "data/output/data_coverage_next_v3_accept_preview.csv"

REPORT_MD = "output/reports/data_coverage_next_v5_apply_report.md"
GATE_TXT = "output/reports/data_coverage_next_v5_gate.txt"

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    parser = argparse.ArgumentParser(description="Apply accepted flavor profiles")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode on copy database")
    parser.add_argument("--apply", action="store_true", help="Apply updates to production database")
    parser.add_argument("--confirm", type=str, help="Confirm string for writing to production database")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Error: Either --dry-run or --apply must be specified.")
        sys.exit(1)

    if args.apply:
        expected_confirm = "WRITE GO: apply data coverage next v5 flavor profiles to production.db"
        if args.confirm != expected_confirm:
            print(f"Error: Confirmation string mismatch. Expected: '{expected_confirm}'")
            sys.exit(1)

    os.makedirs(os.path.dirname(DRY_RUN_DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    if not os.path.exists(ACCEPT_CSV):
        print(f"Error: Input preview CSV not found at {ACCEPT_CSV}")
        sys.exit(1)

    # Determine target database and backup if applying
    target_db = DB_PATH
    if args.dry_run:
        print("Running in DRY-RUN mode.")
        if os.path.exists(DRY_RUN_DB_PATH):
            os.remove(DRY_RUN_DB_PATH)
        shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
        target_db = DRY_RUN_DB_PATH
    else:
        print("Running in PRODUCTION WRITE mode.")
        if os.path.exists(BACKUP_PATH):
            os.remove(BACKUP_PATH)
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"Backup created at: {BACKUP_PATH}")

    hash_before = get_file_hash(DB_PATH)

    # Read candidates
    candidates = []
    with open(ACCEPT_CSV, "r", encoding="utf-8-sig", errors="ignore") as f:
        candidates = list(csv.DictReader(f))

    # Connect to database
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get count before
    profiles_before = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

    fk_missing_count = 0
    already_exists_count = 0
    duplicate_count = 0
    invalid_score_count = 0
    inserted_count = 0
    seen_ids = set()

    try:
        cur.execute("BEGIN TRANSACTION;")

        for r in candidates:
            wid = r["whisky_id"]

            # Check duplicate in input
            if wid in seen_ids:
                duplicate_count += 1
                continue
            seen_ids.add(wid)

            # Check FK missing
            whisky = cur.execute("SELECT region FROM whiskies WHERE whisky_id = ?", (wid,)).fetchone()
            if not whisky:
                fk_missing_count += 1
                continue

            region = whisky["region"] or ""

            # Check already has profile
            profile_exists = cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()[0]
            if profile_exists > 0:
                already_exists_count += 1
                continue

            # Validate scores
            scores_valid = True
            for axis in ["smoky", "peaty", "sweet", "fruity", "spicy", "woody", "floral"]:
                try:
                    val = float(r[axis])
                    if val < 0.0 or val > 1.0:
                        scores_valid = False
                except Exception:
                    scores_valid = False
            if not scores_valid:
                invalid_score_count += 1
                continue

            # Perform insert
            flavor_vector_json = json.dumps({
                "smoky": float(r["smoky"]), "peaty": float(r["peaty"]), "sweet": float(r["sweet"]),
                "fruity": float(r["fruity"]), "spicy": float(r["spicy"]), "woody": float(r["woody"]),
                "floral": float(r["floral"])
            })

            cur.execute("""
                INSERT INTO flavor_profiles (
                    whisky_id, whisky_name, production_bottle_name, match_score, match_method,
                    flavor_vector, flavor_profile, flavor_tags, flavor_source, flavor_data_confidence,
                    production_region, notes_for_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wid, r["whisky_name"], r["whisky_name"], 100, "lexicon_direct",
                flavor_vector_json, "", r["evidence_terms"], "tasting_notes", 1.0,
                region, ""
            ))
            inserted_count += 1

        # Check DB Integrity
        integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity.lower() != "ok":
            raise Exception(f"PRAGMA integrity_check failed: {integrity}")

        profiles_after = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

        # Verify expected counts
        if inserted_count != 6 or (profiles_after - profiles_before) != 6:
            raise Exception(f"Expected 6 inserts, got {inserted_count} (profiles count: {profiles_before} -> {profiles_after})")

        cur.execute("COMMIT;")
        print("Transaction committed successfully.")
        verdict = "GO"

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during apply (rolled back): {e}")
        verdict = "NO-GO"
        inserted_count = 0
        profiles_after = profiles_before

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_same = (hash_before == hash_after)

    if args.apply and verdict == "GO":
        if hash_same:
            print("Error: Database was not modified during apply mode!")
            verdict = "NO-GO"
    elif args.dry_run:
        if not hash_same:
            print("Error: Database mutated in dry-run mode!")
            verdict = "NO-GO"

    if duplicate_count > 0 or invalid_score_count > 0 or fk_missing_count > 0 or already_exists_count > 0:
        verdict = "NO-GO"

    # Write gate
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    # Generate Report MD
    report = []
    report.append("# DATA-COVERAGE-NEXT-V5 — Production Apply Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **Mode:** {'DRY-RUN' if args.dry_run else 'PRODUCTION WRITE'}")
    report.append(f"- **Inserted Count:** `{inserted_count}`")
    report.append(f"- **Flavor Profiles Before:** `{profiles_before}`")
    report.append(f"- **Flavor Profiles After:** `{profiles_after}`\n")

    report.append("## Apply Verification Metrics")
    report.append(f"- Database Hash Before: `{hash_before}`")
    report.append(f"- Database Hash After: `{hash_after}`")
    report.append(f"- Database Mutated: {'Yes' if hash_before != hash_after else 'No'}")
    report.append(f"- Duplicate whisky_id count: {duplicate_count}")
    report.append(f"- Invalid score count: {invalid_score_count}")
    report.append(f"- FK missing count: {fk_missing_count}")
    report.append(f"- Already has flavor profile count: {already_exists_count}")
    report.append(f"- DB Integrity: {integrity if verdict == 'GO' else 'FAILED'}\n")

    report.append("## Applied Flavor Profiles")
    if verdict == "GO":
        report.append("| Whisky ID | Name | Match Method | Flavor Source |")
        report.append("| --- | --- | --- | --- |")
        for r in candidates:
            report.append(f"| {r['whisky_id']} | {r['whisky_name']} | lexicon_direct | tasting_notes |")
    else:
        report.append("- Apply failed or rolled back.")
    report.append("")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Apply execution completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

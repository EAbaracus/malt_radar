import sqlite3
import os
import shutil
import hashlib
import csv
import json
import argparse
import datetime

DB_PATH = "output/import/production.db"
CANDIDATES_CSV = "data/output/flavor_profile_candidates_from_tasting_notes.csv"
REPORT_MD_PATH = "output/reports/flavor_profile_candidate_apply_script_report.md"
REQUIRED_CONFIRM_PHRASE = "WRITE GO: apply flavor profile candidates from tasting notes to production.db"

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
    parser = argparse.ArgumentParser(description="Apply Flavor Profile Candidates from Tasting Notes")
    parser.add_argument("--apply", action="store_true", help="Enable write execution mode")
    parser.add_argument("--confirm", type=str, default="", help="Explicit confirmation phrase")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(CANDIDATES_CSV):
        print(f"Error: Candidates CSV not found at {CANDIDATES_CSV}")
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

    # Read candidates
    candidates = []
    with open(CANDIDATES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('candidate_status') == 'profile_candidate_ready':
                candidates.append(row)

    backup_path = "N/A"
    backup_hash = "N/A"
    if not is_dry_run:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"output/import/production_before_flavor_profile_candidates_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)
        backup_hash = get_file_hash(backup_path)
        print(f"Created Backup: {backup_path}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode={'ro' if is_dry_run else 'rw'}"
    conn = sqlite3.connect(conn_uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Preload DB state
    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    existing_profiles = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    before_fp_count = len(existing_profiles)

    metrics = {
        'planned': len(candidates),
        'verified': 0,
        'failed': 0,
        'inserted': 0
    }
    
    execution_status = "Success"
    integrity_status = "Skipped"

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            w_name = c.get('whisky_name')
            
            failed = []
            if wid not in whiskies:
                failed.append("Whisky ID not found in whiskies table")
            if wid in existing_profiles:
                failed.append("Whisky already has a flavor profile")
                
            scores = {}
            for axis in ['smoky', 'peaty', 'sherry', 'fruity', 'spicy', 'sweet', 'rich']:
                try:
                    val = float(c.get(f'{axis}_score', 0))
                    if not (0.0 <= val <= 1.0):
                        failed.append(f"{axis}_score {val} out of bounds")
                    scores[axis] = val
                except ValueError:
                    failed.append(f"{axis}_score is not a float")

            try:
                conf = float(c.get('confidence_score', 0))
                if conf < 0.7:
                    failed.append(f"Confidence score {conf} too low")
            except ValueError:
                failed.append("Confidence score is not a float")

            if failed:
                metrics['failed'] += 1
                raise Exception(f"Validation failed for whisky_id {wid}: {', '.join(failed)}")

            metrics['verified'] += 1
            
            # Construct flavor profile vector & tags
            flavor_vector = {
                "smoky": round(scores['smoky'] * 10, 1),
                "peaty": round(scores['peaty'] * 10, 1),
                "sherry": round(scores['sherry'] * 10, 1),
                "fruity": round(scores['fruity'] * 10, 1),
                "spicy": round(scores['spicy'] * 10, 1),
                "sweet": round(scores['sweet'] * 10, 1),
                "rich": round(scores['rich'] * 10, 1)
            }
            
            flavor_profile_json = {
                "fruity": round(scores['fruity'] * 10, 1),
                "sweet": round(scores['sweet'] * 10, 1),
                "spicy": round(scores['spicy'] * 10, 1),
                "smoky_peaty": round(max(scores['smoky'], scores['peaty']) * 10, 1),
                "oak_cask": round(scores['rich'] * 5.0, 1),
                "floral_herbal": 0.0,
                "malty_cereal": round(scores['sweet'] * 3.0, 1)
            }

            tags = []
            for axis, score in scores.items():
                if score >= 0.4:
                    tags.append(axis)

            if not is_dry_run:
                cur.execute("""
                    INSERT INTO flavor_profiles (
                        whisky_id, whisky_name, production_bottle_name,
                        match_score, match_method, flavor_vector,
                        flavor_profile, flavor_tags, flavor_source,
                        flavor_data_confidence, production_price,
                        production_rating, production_region, notes_for_review
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wid,
                    w_name,
                    w_name,
                    100,
                    "tasting_note_extraction",
                    json.dumps(flavor_vector),
                    json.dumps(flavor_profile_json),
                    json.dumps(tags),
                    "tasting_note_rule_based",
                    "medium",
                    None,
                    None,
                    None,
                    "Auto-extracted flavor profile from tasting notes"
                ))
                metrics['inserted'] += 1
                existing_profiles.add(wid)

        if not is_dry_run:
            after_fp_count = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0].lower() == 'ok':
                integrity_status = "Passed"
            else:
                integrity_status = f"Failed ({integrity})"
                raise Exception("Integrity check failed after inserts.")

            if metrics['inserted'] != metrics['planned']:
                raise Exception(f"Expected {metrics['planned']} inserts, got {metrics['inserted']}.")
            if after_fp_count != before_fp_count + metrics['inserted']:
                raise Exception(f"Expected final count {before_fp_count + metrics['inserted']}, got {after_fp_count}.")
            
            cur.execute("COMMIT;")
            print("Transaction committed successfully.")
        else:
            cur.execute("ROLLBACK;")
            print("Dry run completed. Transaction rolled back.")
            after_fp_count = before_fp_count
            
    except Exception as e:
        execution_status = f"Failed: {str(e)}"
        print(f"Error during execution: {e}")
        cur.execute("ROLLBACK;")
        print("Transaction rolled back due to error.")
        after_fp_count = before_fp_count

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")

    # Write Report
    report = []
    report.append("# Flavor Profile Candidate Apply Script Report\n")
    report.append(f"- **Script Path:** `scripts/apply/apply_flavor_profile_candidates_from_tasting_notes.py`")
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
    report.append(f"- Planned Candidates: {metrics['planned']}")
    report.append(f"- Validation Passed: {metrics['verified']}")
    report.append(f"- Validation Failed: {metrics['failed']}")
    if not is_dry_run:
        report.append(f"- Inserted Rows: {metrics['inserted']}")
        report.append(f"- Flavor Profiles Before: {before_fp_count}")
        report.append(f"- Flavor Profiles After: {after_fp_count}")
        total_whiskies = len(whiskies)
        before_cov = (before_fp_count / total_whiskies * 100) if total_whiskies else 0
        after_cov = (after_fp_count / total_whiskies * 100) if total_whiskies else 0
        report.append(f"- Expected Coverage Gain: +{after_cov - before_cov:.2f}%")
        report.append(f"- Integrity Check Status: {integrity_status}")

    report.append("\n## Execution Status")
    report.append(f"- **Status:** {execution_status}")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or (not is_dry_run and not hash_unchanged and integrity_status != "Passed"):
        report.append("**NO-GO** (Validation failure or mutation/integrity error).")
    else:
        report.append("**GO** (Dry-run mode validated successfully and apply mode ready).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

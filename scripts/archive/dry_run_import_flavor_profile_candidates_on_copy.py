import sqlite3
import os
import shutil
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/flavor_profile_candidate_import_dry_run.db"
CANDIDATES_CSV = "data/output/flavor_profile_candidates_from_tasting_notes.csv"
DRY_RUN_CSV = "data/output/flavor_profile_candidate_import_dry_run.csv"
REPORT_MD_PATH = "output/reports/flavor_profile_candidate_import_dry_run_report.md"

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
    os.makedirs(os.path.dirname(DRY_RUN_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(CANDIDATES_CSV):
        print(f"Error: Candidates CSV not found at {CANDIDATES_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"Original DB Hash (before): {hash_before}")

    # Copy to output/tmp
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created Dry-Run DB Copy: {DRY_RUN_DB_PATH}")

    # Read candidates
    candidates = []
    with open(CANDIDATES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('candidate_status') == 'profile_candidate_ready':
                candidates.append(row)

    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Preload DB state
    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    existing_profiles = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}

    before_fp_count = len(existing_profiles)

    dry_run_results = []
    metrics = {
        'planned': len(candidates),
        'passed': 0,
        'failed': 0,
        'inserted': 0
    }

    try:
        cur.execute("BEGIN TRANSACTION;")

        for c in candidates:
            wid = str(c.get('whisky_id'))
            w_name = c.get('whisky_name')
            dist_name = c.get('distillery_name')
            
            failed = []
            if wid not in whiskies:
                failed.append("Whisky ID not found in whiskies table")
            if wid in existing_profiles:
                failed.append("Whisky already has a flavor profile")
                
            # Score check
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
                dry_run_results.append({
                    'whisky_id': wid,
                    'whisky_name': w_name,
                    'distillery_name': dist_name,
                    'candidate_status': 'profile_candidate_ready',
                    'verification_status': 'Failed',
                    'import_action': 'Skipped',
                    'reason': ", ".join(failed)
                })
                continue

            metrics['passed'] += 1
            
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

            # Insert into copy
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

            dry_run_results.append({
                'whisky_id': wid,
                'whisky_name': w_name,
                'distillery_name': dist_name,
                'candidate_status': 'profile_candidate_ready',
                'verification_status': 'Passed',
                'import_action': 'Inserted',
                'reason': 'Success'
            })

        after_fp_count = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        integrity_status = integrity[0] if integrity else "Failed"

        # Verification checks on copy
        if metrics['inserted'] != metrics['planned']:
            raise Exception(f"Expected {metrics['planned']} inserts, got {metrics['inserted']}.")
        if after_fp_count != before_fp_count + metrics['inserted']:
            raise Exception(f"Expected final count {before_fp_count + metrics['inserted']}, got {after_fp_count}.")
        if integrity_status.lower() != 'ok':
            raise Exception("PRAGMA integrity_check failed after inserts.")

        cur.execute("COMMIT;")
        print("Dry run database transaction completed successfully.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during dry-run simulation: {e}")
        metrics['inserted'] = 0
        after_fp_count = before_fp_count
        integrity_status = "Failed (Rollback)"
        
    conn.close()

    # Write CSV
    if dry_run_results:
        with open(DRY_RUN_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dry_run_results[0].keys())
            writer.writeheader()
            writer.writerows(dry_run_results)

    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)
    print(f"Original DB Hash (after): {hash_after}")
    print(f"Original DB Hash Unchanged: {hash_unchanged}")

    # Write Report
    report = []
    report.append("# Flavor Profile Candidate Import Dry-Run Report\n")
    report.append(f"- **Original DB Path:** `{DB_PATH}`")
    report.append(f"- **Dry-Run DB Copy Path:** `{DRY_RUN_DB_PATH}`")
    report.append(f"- **Original Hash Before:** `{hash_before}`")
    report.append(f"- **Original Hash After:** `{hash_after}`")
    report.append(f"- **Original Hash Unchanged:** {'Yes' if hash_unchanged else 'NO (MUTATION DETECTED!)'}")

    report.append("\n## Global Metrics (on Copy DB)")
    report.append(f"- Planned Candidates: {metrics['planned']}")
    report.append(f"- Validation Passed: {metrics['passed']}")
    report.append(f"- Validation Failed: {metrics['failed']}")
    report.append(f"- Inserted on Copy: {metrics['inserted']}")
    report.append(f"- Flavor Profiles Before: {before_fp_count}")
    report.append(f"- Flavor Profiles After: {after_fp_count}")
    
    total_whiskies = len(whiskies)
    before_cov = (before_fp_count / total_whiskies * 100) if total_whiskies else 0
    after_cov = (after_fp_count / total_whiskies * 100) if total_whiskies else 0
    report.append(f"- Coverage Before: {before_cov:.2f}%")
    report.append(f"- Coverage After: {after_cov:.2f}%")
    report.append(f"- Expected Coverage Gain: +{after_cov - before_cov:.2f}%")
    report.append(f"- PRAGMA integrity_check: {integrity_status}")

    report.append("\n## Skipped/Failed Candidates")
    skipped = [r for r in dry_run_results if r['verification_status'] == 'Failed']
    if skipped:
        report.append("| Whisky ID | Name | Distillery | Reason |")
        report.append("|---|---|---|---|")
        for s in skipped:
            report.append(f"| {s['whisky_id']} | {s['whisky_name']} | {s['distillery_name']} | {s['reason']} |")
    else:
        report.append("None. All candidates validated successfully.")

    report.append("\n## Final GO/NO-GO")
    if metrics['failed'] > 0 or not hash_unchanged or integrity_status.lower() != 'ok' or metrics['inserted'] != metrics['planned']:
        report.append("**NO-GO** (Verification failures or DB mutation detected).")
    else:
        report.append("**GO** (SQL dry-run execution on backup copy successfully completed).")

    report.append("\n## Next Phase")
    report.append("- **AŞAMA X5 — Flavor Profile Candidate Real Apply**")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

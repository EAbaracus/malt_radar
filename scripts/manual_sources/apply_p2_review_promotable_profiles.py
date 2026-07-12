import os
import csv
import sqlite3
import hashlib
import json
import shutil

INPUT_CSV = "data/manual_sources/p2_review_dry_run_apply_ready.csv"
OUT_INSERTED = "data/manual_sources/p2_review_apply_inserted.csv"
OUT_BLOCKED = "data/manual_sources/p2_review_apply_blocked.csv"
REPORT_MD = "output/reports/p2_review_apply_report.md"
GATE_TXT = "output/reports/p2_review_apply_gate.txt"
PROD_DB = "output/import/production.db"
BACKUP_DB = "output/import/production_before_p2_review_apply.db"

APP_KEYS = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "floral_herbal", "malty_cereal"]

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def main():
    print("=== DATA-COVERAGE-P2-REVIEW-STAGING-APPLY ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_INSERTED), exist_ok=True)

    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: {INPUT_CSV} not found.")
        return

    # Backup DB
    shutil.copy2(PROD_DB, BACKUP_DB)
    hash_before = get_file_hash(BACKUP_DB)

    conn = sqlite3.connect(PROD_DB)
    cur = conn.cursor()

    count_before = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    valid_whiskies = set(row[0] for row in cur.execute("SELECT whisky_id FROM whiskies").fetchall())
    existing_profiles = set(row[0] for row in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall())

    inserted_data = []
    blocked_data = []

    seen_wids = set()

    missing_fk_count = 0
    already_profile_count = 0
    duplicate_count = 0
    invalid_score_count = 0
    low_signal_count = 0

    input_ready_count = 0

    try:
        cur.execute("BEGIN TRANSACTION")
        
        with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                input_ready_count += 1
                wid = row.get("whisky_id", "").strip()
                name = row.get("whisky_name", "").strip()
                source_system = row.get("source_system", "").strip()
                
                is_blocked = False
                block_reasons = []

                if not wid or wid not in valid_whiskies:
                    is_blocked = True
                    block_reasons.append("block_missing_fk")
                    missing_fk_count += 1
                
                if wid in existing_profiles:
                    is_blocked = True
                    block_reasons.append("block_duplicate_profile")
                    already_profile_count += 1
                    
                if wid and wid in seen_wids:
                    is_blocked = True
                    block_reasons.append("block_duplicate")
                    duplicate_count += 1
                    
                if wid:
                    seen_wids.add(wid)

                has_invalid_score = False
                active_axes = 0
                flavor_vector = {}
                for k in APP_KEYS:
                    val = safe_float(row.get(k, 0))
                    flavor_vector[k] = val
                    if val < 0.0 or val > 1.0:
                        has_invalid_score = True
                    if val > 0:
                        active_axes += 1

                if has_invalid_score:
                    is_blocked = True
                    block_reasons.append("block_invalid_score")
                    invalid_score_count += 1
                    
                if active_axes < 2:
                    is_blocked = True
                    block_reasons.append("block_low_signal")
                    low_signal_count += 1

                if is_blocked:
                    row["block_reasons"] = "|".join(block_reasons)
                    blocked_data.append(row)
                else:
                    flavor_source = f"p2_review_promotable:{source_system}" if source_system else "p2_review_promotable"
                    flavor_vector_json = json.dumps(flavor_vector)
                    
                    cur.execute(
                        """
                        INSERT INTO flavor_profiles 
                        (whisky_id, whisky_name, flavor_vector, flavor_source, flavor_data_confidence, match_method)
                        VALUES (?, ?, ?, ?, 'high', 'manual_curation')
                        """,
                        (wid, name, flavor_vector_json, flavor_source)
                    )
                    inserted_data.append(row)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Transaction failed, rolled back: {e}")
        with open(GATE_TXT, "w", encoding="utf-8") as f:
            f.write("NO-GO")
            f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        return
    
    count_after = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    conn.close()

    if inserted_data:
        out_fields = list(inserted_data[0].keys())
        with open(OUT_INSERTED, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(inserted_data)
    else:
        with open(OUT_INSERTED, "w", encoding="utf-8") as f:
            f.write("whisky_id\n")

    if blocked_data:
        out_fields = list(blocked_data[0].keys())
        with open(OUT_BLOCKED, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(blocked_data)
    else:
        with open(OUT_BLOCKED, "w", encoding="utf-8") as f:
            f.write("whisky_id\n")

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if count_after != count_before + len(inserted_data):
        verdict = "NO-GO"
    if missing_fk_count > 0 or duplicate_count > 0 or already_profile_count > 0 or invalid_score_count > 0 or low_signal_count > 0:
        if len(inserted_data) > 0:
            verdict = "WARN_GO"
        else:
            verdict = "NO-GO"
    if len(inserted_data) < input_ready_count and verdict == "GO":
        verdict = "WARN_GO"
    if hash_before == hash_after and len(inserted_data) > 0:
        verdict = "NO-GO" # Expected to change

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)

    report = []
    report.append("# P2 Review Staging Apply Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## Apply Results")
    report.append(f"- Input Ready Count: `{input_ready_count}`")
    report.append(f"- Inserted Count: `{len(inserted_data)}`")
    report.append(f"- Blocked Count: `{len(blocked_data)}`\n")

    report.append("## Block Reasons (if any)")
    report.append(f"- Missing FK: `{missing_fk_count}`")
    report.append(f"- Duplicate Profile: `{already_profile_count}`")
    report.append(f"- Duplicate in Batch: `{duplicate_count}`")
    report.append(f"- Invalid Score: `{invalid_score_count}`")
    report.append(f"- Low Signal: `{low_signal_count}`\n")

    report.append("## Database Checks")
    report.append(f"- flavor_profiles Before: `{count_before}`")
    report.append(f"- flavor_profiles After: `{count_after}`")
    report.append(f"- Expected After: `{count_before + len(inserted_data)}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Backup DB Created: `Yes`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Apply completed. Verdict: {verdict}. Inserted: {len(inserted_data)}")

if __name__ == "__main__":
    main()

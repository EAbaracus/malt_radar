import os
import sqlite3
import hashlib
import json
import csv
import shutil

PROD_DB = "output/import/production.db"
TMP_DB = "output/tmp/data_coverage_next_v8_dry_run.db"
INPUT_CSV = "data/output/data_coverage_next_v3_accept_preview.csv"
CSV_OUT = "data/output/data_coverage_next_v8_v5_key_fix_plan.csv"
REPORT_MD = "output/reports/data_coverage_next_v8_report.md"
GATE_TXT = "output/reports/data_coverage_next_v8_gate.txt"
EXPECTED_HASH = "383291A4142A1F40948E6A02A3C224E4E4524F4DF88AC9E7F5F7D1A2017F5344"

APP_KEYS = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"]

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    print("=== DATA-COVERAGE-NEXT-V8 Fix V5 Profile Keys Dry-Run ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(TMP_DB), exist_ok=True)
    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    # Copy DB for dry run
    if os.path.exists(TMP_DB):
        os.remove(TMP_DB)
    shutil.copy2(PROD_DB, TMP_DB)

    # Read input candidates
    candidates = []
    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidates.append(row["whisky_id"])

    conn = sqlite3.connect(TMP_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    matched_count = 0
    updated_count = 0
    csv_plan_data = []

    for wid in candidates:
        row = cur.execute("SELECT * FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()
        if not row:
            continue
        
        matched_count += 1
        row_dict = dict(row)
        vector_str = row_dict["flavor_vector"]
        if not vector_str:
            continue
            
        vector = json.loads(vector_str)
        
        # Build new vector
        new_vector = {}
        new_vector["fruity"] = float(vector.get("fruity", 0.0))
        new_vector["sweet"] = float(vector.get("sweet", 0.0))
        new_vector["spicy"] = float(vector.get("spicy", 0.0))
        
        smoky = float(vector.get("smoky", 0.0))
        peaty = float(vector.get("peaty", 0.0))
        new_vector["smoky_peaty"] = max(smoky, peaty) # Combine using max
        
        new_vector["oak_cask"] = float(vector.get("woody", 0.0))
        new_vector["floral_herbal"] = float(vector.get("floral", 0.0))
        new_vector["malty_cereal"] = 0.0 # Default missing evidence
        
        # Clamp to 0..1
        for k, v in new_vector.items():
            if v < 0.0: new_vector[k] = 0.0
            if v > 1.0: new_vector[k] = 1.0

        new_vector_json = json.dumps(new_vector)
        
        cur.execute("UPDATE flavor_profiles SET flavor_vector = ? WHERE whisky_id = ?", (new_vector_json, wid))
        updated_count += 1
        
        csv_plan_data.append({
            "whisky_id": wid,
            "old_vector": vector_str,
            "new_vector": new_vector_json
        })

    conn.commit()

    # Validation on TMP_DB
    invalid_score = 0
    app_key_compat_count = 0
    
    # Check only updated ones for app key compatibility and scores
    for row in csv_plan_data:
        wid = row["whisky_id"]
        v_str = cur.execute("SELECT flavor_vector FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()[0]
        v = json.loads(v_str)
        
        # Check if all exactly 7 keys are present
        if set(v.keys()) == set(APP_KEYS):
            app_key_compat_count += 1
            
        # Check scores
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

    # Write plan
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["whisky_id", "old_vector", "new_vector"])
        writer.writeheader()
        writer.writerows(csv_plan_data)

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after: verdict = "NO-GO"
    if len(candidates) != 6: verdict = "NO-GO"
    if matched_count != 6: verdict = "NO-GO"
    if updated_count != 6: verdict = "NO-GO"
    if app_key_compat_count != 6: verdict = "NO-GO"
    if invalid_score > 0: verdict = "NO-GO"
    if fk_missing > 0 or duplicate_fp > 0: verdict = "NO-GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)

    report = []
    report.append("# DATA-COVERAGE-NEXT-V8 — Fix V5 Profile Keys Dry-Run Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## Operations")
    report.append(f"- Input Candidates (V5 accepted): `{len(candidates)}`")
    report.append(f"- Matched Profiles in DB: `{matched_count}`")
    report.append(f"- Dry-run Updated Profiles: `{updated_count}`\n")

    report.append("## Validation Checks on TMP DB")
    report.append(f"- App Key Compatibility Count (7/7 expected keys): `{app_key_compat_count}`")
    report.append(f"- Invalid Score Count (outside 0..1): `{invalid_score}`")
    report.append(f"- FK Missing: `{fk_missing}`")
    report.append(f"- Duplicate Profiles: `{duplicate_fp}`\n")

    report.append("## Production DB Hash (MUST NOT CHANGE)")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Dry-run completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

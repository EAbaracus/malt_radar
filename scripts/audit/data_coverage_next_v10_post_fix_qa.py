import os
import sqlite3
import hashlib
import json
import csv

DB_PATH = "output/import/production.db"
PLAN_CSV = "data/output/data_coverage_next_v8_v5_key_fix_plan.csv"
REPORT_MD = "output/reports/data_coverage_next_v10_post_fix_qa_report.md"
GATE_TXT = "output/reports/data_coverage_next_v10_gate.txt"
ADAPTER_FILE = "frontend/lib/features/flavor/domain/flavor_profile_normalizer.dart"
EXPECTED_HASH = "EED7B761947451CB8B54DA024D1767BD2C90BD96914555C70F75BF6328E4F587"

APP_KEYS = {"fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"}
LEGACY_KEYS = {"component_1", "component_2", "component_3"}

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def check_adapter():
    if not os.path.exists(ADAPTER_FILE):
        return False
    with open(ADAPTER_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if "_hasWhiskeyMapperComponents" in content:
            return True
    return False

def main():
    print("=== DATA-COVERAGE-NEXT-V10 Post-Fix QA Smoke ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    hash_before = get_file_hash(DB_PATH)

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Integrity Check
    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]

    # 2. Total Count
    total_profiles = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

    # 3. Read V9 target IDs
    v9_ids = []
    if os.path.exists(PLAN_CSV):
        with open(PLAN_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            v9_ids = [row["whisky_id"] for row in reader]

    v9_app_compatible_count = 0
    v9_invalid_score_count = 0
    
    # 4. Check V9 profiles
    for wid in v9_ids:
        row = cur.execute("SELECT flavor_vector FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()
        if not row:
            continue
        v_str = row["flavor_vector"]
        if not v_str:
            continue
        v = json.loads(v_str)
        if set(v.keys()) == APP_KEYS:
            v9_app_compatible_count += 1
            
        for val in v.values():
            if not isinstance(val, (int, float)) or val < 0.0 or val > 1.0:
                v9_invalid_score_count += 1

    # 5. Legacy rows
    legacy_component_count = 0
    all_profiles = cur.execute("SELECT flavor_vector FROM flavor_profiles").fetchall()
    for row in all_profiles:
        v_str = row["flavor_vector"]
        if v_str:
            try:
                v = json.loads(v_str)
                if LEGACY_KEYS.issubset(set(v.keys())):
                    legacy_component_count += 1
            except Exception:
                pass

    # 6. Adapter Exists
    adapter_exists = check_adapter()

    # 7. Duplicates & FKs
    duplicate_fp = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT whisky_id, COUNT(*) as cnt FROM flavor_profiles GROUP BY whisky_id HAVING cnt > 1
        )
    """).fetchone()[0]
    
    fk_missing = cur.execute("""
        SELECT COUNT(*) FROM flavor_profiles fp
        LEFT JOIN whiskies w ON fp.whisky_id = w.whisky_id
        WHERE w.whisky_id IS NULL
    """).fetchone()[0]

    conn.close()

    hash_after = get_file_hash(DB_PATH)

    verdict = "GO"
    if integrity.lower() != "ok": verdict = "NO-GO"
    if total_profiles != 632: verdict = "NO-GO"
    if v9_app_compatible_count != 6: verdict = "NO-GO"
    if v9_invalid_score_count > 0: verdict = "NO-GO"
    if duplicate_fp > 0 or fk_missing > 0: verdict = "NO-GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after: verdict = "NO-GO"
    if not adapter_exists: verdict = "NO-GO"

    # Write Gate
    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)

    # Write Report
    report = []
    report.append("# DATA-COVERAGE-NEXT-V10 — Post-Fix QA Smoke Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **DB Integrity:** `{integrity}`\n")

    report.append("## Validations")
    report.append(f"- Total Flavor Profiles: `{total_profiles}`")
    report.append(f"- V9 Fixed Profiles Found: `{len(v9_ids)}`")
    report.append(f"- V9 App Compatible Count (7 expected keys): `{v9_app_compatible_count}` / `6`")
    report.append(f"- V9 Invalid Score Count (outside 0..1): `{v9_invalid_score_count}`")
    report.append(f"- Legacy WhiskeyMapper/Component Rows: `{legacy_component_count}`")
    report.append(f"- Frontend App Adapter Found: `{'Yes' if adapter_exists else 'No'}`")
    report.append(f"- FK Missing (profile -> whisky): `{fk_missing}`")
    report.append(f"- Duplicate Profiles (by whisky_id): `{duplicate_fp}`\n")

    report.append("## State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"QA Smoke completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

import os
import sqlite3
import hashlib
import json

DB_PATH = "output/import/production.db"
REPORT_MD = "output/reports/data_coverage_next_v6_post_apply_qa_report.md"
GATE_TXT = "output/reports/data_coverage_next_v6_gate.txt"
ACCEPT_CSV = "data/output/data_coverage_next_v3_accept_preview.csv"
EXPECTED_HASH = "383291A4142A1F40948E6A02A3C224E4E4524F4DF88AC9E7F5F7D1A2017F5344"

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    print("=== Running DATA-COVERAGE-NEXT-V6 Post-Apply QA Smoke ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    
    hash_before = get_file_hash(DB_PATH)

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Integrity Check
    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]

    # 2. Core counts
    whiskies_count = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    flavor_profiles_count = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    tasting_notes_count = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    official_source_ref_count = cur.execute("SELECT COUNT(*) FROM official_source_references").fetchone()[0]
    region_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE region IS NOT NULL AND region != ''").fetchone()[0]
    cask_type_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE cask_type IS NOT NULL AND cask_type != ''").fetchone()[0]
    
    coverage_pct = round((flavor_profiles_count / whiskies_count) * 100, 2) if whiskies_count > 0 else 0.0

    # 3. Validation checks
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

    null_empty_id = cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id IS NULL OR whisky_id = ''").fetchone()[0]

    # Score range, app compatibility
    invalid_score_count = 0
    incompatible_radar_count = 0
    all_profiles = cur.execute("SELECT whisky_id, flavor_vector FROM flavor_profiles").fetchall()
    
    expected_axes = {"smoky", "peaty", "sweet", "fruity", "spicy", "woody", "floral"}
    
    for row in all_profiles:
        try:
            vector = json.loads(row["flavor_vector"])
            # Check keys and types
            for axis in expected_axes:
                if axis not in vector:
                    incompatible_radar_count += 1
                    break
                val = vector[axis]
                if not isinstance(val, (int, float)):
                    incompatible_radar_count += 1
                    break
                if val < 0.0 or val > 1.0:
                    invalid_score_count += 1
        except Exception:
            incompatible_radar_count += 1

    # New V5 inserted profiles present
    v5_ids = []
    if os.path.exists(ACCEPT_CSV):
        with open(ACCEPT_CSV, "r", encoding="utf-8-sig") as f:
            import csv
            reader = csv.DictReader(f)
            v5_ids = [row["whisky_id"] for row in reader]

    v5_present_count = 0
    for wid in v5_ids:
        if cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()[0] > 0:
            v5_present_count += 1

    conn.close()

    hash_after = get_file_hash(DB_PATH)

    # Verdict
    verdict = "GO"
    if integrity.lower() != "ok": verdict = "NO-GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after: verdict = "NO-GO"
    if whiskies_count != 1831: verdict = "NO-GO"
    if flavor_profiles_count != 632: verdict = "NO-GO"
    if tasting_notes_count != 496: verdict = "NO-GO"
    if official_source_ref_count != 96: verdict = "NO-GO"
    if region_filled != 303: verdict = "NO-GO"
    if cask_type_filled != 54: verdict = "NO-GO"
    if fk_missing > 0 or duplicate_fp > 0 or null_empty_id > 0: verdict = "NO-GO"
    if invalid_score_count > 0 or incompatible_radar_count > 0: verdict = "NO-GO"
    if v5_present_count != 6: verdict = "NO-GO"

    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    # Report
    report = []
    report.append("# DATA-COVERAGE-NEXT-V6 — Post-Apply QA Smoke Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **DB Integrity:** `{integrity}`\n")

    report.append("## Core Counts")
    report.append(f"- Whiskies: `{whiskies_count}`")
    report.append(f"- Flavor Profiles: `{flavor_profiles_count}`")
    report.append(f"- Flavor Coverage: `{coverage_pct}%`")
    report.append(f"- Tasting Notes: `{tasting_notes_count}`")
    report.append(f"- Official Source References: `{official_source_ref_count}`")
    report.append(f"- Region Filled: `{region_filled}`")
    report.append(f"- Cask Type Filled: `{cask_type_filled}`\n")

    report.append("## Validation Metrics")
    report.append(f"- FK Missing (profile -> whisky): `{fk_missing}`")
    report.append(f"- Duplicate Profiles (by whisky_id): `{duplicate_fp}`")
    report.append(f"- Null/Empty whisky_id in profiles: `{null_empty_id}`")
    report.append(f"- Invalid Score Count (outside 0..1): `{invalid_score_count}`")
    report.append(f"- Incompatible App Radar Json: `{incompatible_radar_count}`")
    report.append(f"- New V5 Profiles Present: `{v5_present_count}/6`\n")

    report.append("## State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Current Hash Before: `{hash_before}`")
    report.append(f"- Current Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"QA Smoke completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

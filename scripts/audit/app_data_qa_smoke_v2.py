import sqlite3
import os
import hashlib
import json
import subprocess

DB_PATH = "output/import/production.db"
REPORT_MD = "output/reports/app_data_qa_smoke_v2_report.md"
GATE_TXT = "output/reports/app_data_qa_smoke_v2_gate.txt"

def get_file_hash(path):
    if not os.path.exists(path):
        return "N/A"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def main():
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(GATE_TXT), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    db_hash = get_file_hash(DB_PATH)

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. PRAGMA integrity_check
    integrity = cur.execute("PRAGMA integrity_check").fetchone()
    integrity_ok = integrity and integrity[0].lower() == 'ok'

    # 2. Row counts
    whiskies_count = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    tasting_notes_count = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    flavor_profiles_count = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]

    # 3. Coverage (distinct whiskies)
    whiskies_with_tn = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM tasting_notes").fetchone()[0]
    whiskies_with_fp = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles").fetchone()[0]

    # 4. FK missing
    tn_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM tasting_notes 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    fp_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    # 5. Duplicate tasting note fingerprints
    duplicate_tn_fingerprints = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT nose_notes, palate_notes, finish_notes 
            FROM tasting_notes 
            GROUP BY nose_notes, palate_notes, finish_notes 
            HAVING COUNT(*) > 1 AND nose_notes != '' AND palate_notes != ''
        )
    """).fetchone()[0]

    # 6. Duplicate flavor profiles per whisky_id
    duplicate_fp_count = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT whisky_id FROM flavor_profiles 
            GROUP BY whisky_id HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    # 7. Invalid radar score range (< 0)
    invalid_score_count = 0
    fps = cur.execute("SELECT flavor_profile FROM flavor_profiles").fetchall()
    for row in fps:
        fp_str = row['flavor_profile']
        if fp_str:
            try:
                fp_json = json.loads(fp_str)
                if isinstance(fp_json, dict):
                    for k, val in fp_json.items():
                        try:
                            f_val = float(val)
                            if f_val < 0.0:
                                invalid_score_count += 1
                        except ValueError:
                            invalid_score_count += 1
            except:
                invalid_score_count += 1

    # 8. Empty nose/palate/finish quality issues
    empty_notes_count = cur.execute("""
        SELECT COUNT(*) FROM tasting_notes 
        WHERE (nose_notes IS NULL OR nose_notes = '') 
          AND (palate_notes IS NULL OR palate_notes = '') 
          AND (finish_notes IS NULL OR finish_notes = '')
    """).fetchone()[0]

    # 9. Sample app detail query
    sample_issues = 0
    sample_query = """
        SELECT w.whisky_id, w.name, d.name as dist_name, t.nose_notes, f.flavor_profile
        FROM whiskies w
        JOIN distilleries d ON w.distillery_id = d.distillery_id
        LEFT JOIN tasting_notes t ON w.whisky_id = t.whisky_id
        LEFT JOIN flavor_profiles f ON w.whisky_id = f.whisky_id
        LIMIT 50
    """
    sample_rows = cur.execute(sample_query).fetchall()
    for r in sample_rows:
        if not r['name'] or not r['dist_name']:
            sample_issues += 1

    # 10. Similarity readiness
    similarity_ready_count = cur.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE flavor_profile IS NOT NULL AND flavor_profile != ''
    """).fetchone()[0]

    conn.close()

    # 11. Git status check
    git_db_modified = False
    git_db_staged = False
    try:
        status_out = subprocess.check_output(["git", "status", "--short"], text=True)
        for line in status_out.splitlines():
            if "production.db" in line:
                if line.startswith(" M") or line.startswith("??") or line.startswith(" M "):
                    git_db_modified = True
                if line.startswith("M") or line.startswith("A"):
                    git_db_staged = True
    except:
        pass

    # GO Check
    go_conditions = (
        integrity_ok and
        tn_fk_missing == 0 and
        fp_fk_missing == 0 and
        duplicate_fp_count == 0 and
        invalid_score_count == 0 and
        sample_issues == 0 and
        tasting_notes_count == 496 and
        flavor_profiles_count == 636
    )

    decision = "GO" if go_conditions else "NO-GO"

    # Write Gate TXT
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(decision)

    # Write MD Report
    report = []
    report.append("# Post-Book Apply App Data QA Smoke v2 Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Latest DB Hash:** `{db_hash}`")
    report.append(f"- **Gate Decision:** **{decision}**")

    report.append("\n## Core Metrics")
    report.append(f"- Whiskies Count: {whiskies_count}")
    report.append(f"- Tasting Notes Count: {tasting_notes_count} (Expected: 496)")
    report.append(f"- Flavor Profiles Count: {flavor_profiles_count} (Expected: 636)")
    report.append(f"- Whiskies with Tasting Notes (Distinct): {whiskies_with_tn}")
    report.append(f"- Whiskies with Flavor Profiles (Distinct): {whiskies_with_fp}")

    report.append("\n## Integrity & Quality Validation")
    report.append(f"- PRAGMA integrity_check: {'ok' if integrity_ok else 'FAILED'}")
    report.append(f"- Tasting Note FK Missing Count: {tn_fk_missing} (Expected: 0)")
    report.append(f"- Flavor Profile FK Missing Count: {fp_fk_missing} (Expected: 0)")
    report.append(f"- Duplicate Tasting Note Fingerprints: {duplicate_tn_fingerprints}")
    report.append(f"- Duplicate Flavor Profiles per Whisky ID: {duplicate_fp_count} (Expected: 0)")
    report.append(f"- Invalid Radar Score count (< 0): {invalid_score_count} (Expected: 0)")
    report.append(f"- Empty Tasting Notes (Nose/Palate/Finish all empty): {empty_notes_count}")
    report.append(f"- Sample App Detail Query Issues: {sample_issues} (Expected: 0)")
    report.append(f"- Similarity-Ready Whiskies count: {similarity_ready_count}")

    report.append("\n## Git Status Risk Summary")
    report.append(f"- Production DB Modified: {'Yes' if git_db_modified else 'No'}")
    report.append(f"- Production DB Staged: {'Yes' if git_db_staged else 'No'}")
    report.append("- *Rules Check:* production.db should be modified but NOT STAGED / NOT COMMITTED.")

    report.append("\n## Final GO/NO-GO")
    if go_conditions:
        report.append("**GO** (Bütün veritabanı bütünlük, FK ve metrik hedefleri başarıyla doğrulandı).")
    else:
        report.append("**NO-GO** (Veritabanı hedefleri (496 TN, 636 FP) veya bütünlük doğrulama şartları sağlanamadı).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")
    print(f"Gate file written to: {GATE_TXT}")

if __name__ == "__main__":
    main()

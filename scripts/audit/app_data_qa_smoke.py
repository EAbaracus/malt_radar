import sqlite3
import os
import csv
import json

DB_PATH = "output/import/production.db"
OUTPUT_CSV = "data/output/app_data_qa_smoke.csv"
REPORT_MD = "output/reports/app_data_qa_smoke_report.md"

def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Core stats
    total_whiskies = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    total_tns = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    total_fps = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    
    unique_tn_wids = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM tasting_notes").fetchone()[0]

    # FK missing checks
    tn_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM tasting_notes 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    fp_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    # Duplicates per whisky_id
    duplicate_fp_count = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT whisky_id FROM flavor_profiles 
            GROUP BY whisky_id HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    # Score range check
    invalid_score_count = 0
    fps_rows = cur.execute("SELECT whisky_id, flavor_profile, flavor_vector FROM flavor_profiles").fetchall()
    
    for row in fps_rows:
        # Check flavor_profile JSON scores
        fp_str = row['flavor_profile']
        if fp_str:
            try:
                fp_json = json.loads(fp_str)
                if isinstance(fp_json, dict):
                    for k, val in fp_json.items():
                        try:
                            f_val = float(val)
                            # DB scores are non-negative, check if negative
                            if f_val < 0.0:
                                invalid_score_count += 1
                        except ValueError:
                            invalid_score_count += 1
            except json.JSONDecodeError:
                invalid_score_count += 1

    # Missing profile count
    missing_profile_count = total_whiskies - total_fps

    # Sample 20 whisky completeness check
    sample_whiskies = cur.execute("SELECT * FROM whiskies LIMIT 20").fetchall()
    completeness_issues = 0
    for w in sample_whiskies:
        if not w['whisky_id'] or not w['name']:
            completeness_issues += 1

    # Similarity-ready whiskies (have flavor profiles)
    similarity_ready_count = total_fps

    conn.close()

    # Write CSV
    csv_rows = [
        {'metric': 'total_whiskies', 'value': total_whiskies},
        {'metric': 'total_tasting_notes', 'value': total_tns},
        {'metric': 'whiskies_with_tasting_notes', 'value': unique_tn_wids},
        {'metric': 'total_flavor_profiles', 'value': total_fps},
        {'metric': 'missing_profile_count', 'value': missing_profile_count},
        {'metric': 'invalid_score_count', 'value': invalid_score_count},
        {'metric': 'duplicate_fp_count', 'value': duplicate_fp_count},
        {'metric': 'tasting_note_fk_missing', 'value': tn_fk_missing},
        {'metric': 'flavor_profile_fk_missing', 'value': fp_fk_missing},
        {'metric': 'completeness_issues', 'value': completeness_issues},
        {'metric': 'similarity_ready_count', 'value': similarity_ready_count}
    ]

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['metric', 'value'])
        writer.writeheader()
        writer.writerows(csv_rows)

    # Integrity Status
    integrity_go = (
        tn_fk_missing == 0 and
        fp_fk_missing == 0 and
        duplicate_fp_count == 0 and
        invalid_score_count == 0 and
        completeness_issues == 0
    )
    decision = "GO" if integrity_go else "NO-GO"

    # Write MD Report
    report = []
    report.append("# App Data QA Smoke Test Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Data QA Gate Status:** **{decision}**")
    
    report.append("\n## Core Metrics")
    report.append(f"- Total Whiskies: {total_whiskies}")
    report.append(f"- Total Tasting Notes: {total_tns}")
    report.append(f"- Whiskies with Tasting Notes (Distinct): {unique_tn_wids}")
    report.append(f"- Total Flavor Profiles: {total_fps}")
    report.append(f"- Whiskies Missing Flavor Profiles (Gap): {missing_profile_count}")
    report.append(f"- Similarity-Ready Whiskies (with Profile): {similarity_ready_count}")

    report.append("\n## Integrity & Validation Checks")
    report.append(f"- Tasting Note FK Missing count: {tn_fk_missing} (Expected: 0)")
    report.append(f"- Flavor Profile FK Missing count: {fp_fk_missing} (Expected: 0)")
    report.append(f"- Duplicate Flavor Profiles per Whisky ID: {duplicate_fp_count} (Expected: 0)")
    report.append(f"- Invalid Flavor Profile Scores count: {invalid_score_count} (Expected: 0)")
    report.append(f"- Sample 20 Whisky Data Completeness Issues: {completeness_issues} (Expected: 0)")

    report.append("\n## Next Phase Suggestions")
    report.append("1. **AŞAMA Z — Release Hardening**: Lock the database configurations and perform build deployment checks.")
    
    report.append("\n## Final GO/NO-GO")
    if integrity_go:
        report.append("**GO** (Veritabanı bütünlük testlerinden başarıyla geçti, veri kırılması tespit edilmedi).")
    else:
        report.append("**NO-GO** (Veri doğrulaması veya bütünlük kontrolü başarısız oldu).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

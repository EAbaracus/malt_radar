import sqlite3
import os
import hashlib
import json
import subprocess

DB_PATH = "output/import/production.db"
REPORT_MD = "output/reports/app_data_qa_smoke_v3_report.md"
GATE_TXT = "output/reports/app_data_qa_smoke_v3_gate.txt"

def get_file_hash(path):
    if not os.path.exists(path):
        return "N/A"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest().upper()

def main():
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(GATE_TXT), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        with open(GATE_TXT, 'w', encoding='utf-8') as f:
            f.write("NO-GO")
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

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
    distilleries_count = cur.execute("SELECT COUNT(*) FROM distilleries").fetchone()[0]
    tasting_notes_count = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    flavor_profiles_count = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    official_source_refs_count = cur.execute("SELECT COUNT(*) FROM official_source_references").fetchone()[0]

    # 3. Tasting note coverage (distinct whiskies)
    whiskies_with_tn = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM tasting_notes").fetchone()[0]
    missing_tn_count = whiskies_count - whiskies_with_tn

    # 4. Flavor profile coverage (distinct whiskies)
    whiskies_with_fp = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles").fetchone()[0]
    missing_fp_count = whiskies_count - whiskies_with_fp

    # 5. Metadata coverage
    region_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE region IS NOT NULL AND region != ''").fetchone()[0]
    region_missing = whiskies_count - region_filled

    cask_type_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE cask_type IS NOT NULL AND cask_type != ''").fetchone()[0]
    cask_type_missing = whiskies_count - cask_type_filled

    age_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE age IS NOT NULL AND age != ''").fetchone()[0]
    age_missing = whiskies_count - age_filled

    abv_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE abv IS NOT NULL AND abv != ''").fetchone()[0]
    abv_missing = whiskies_count - abv_filled

    # 6. FK missing checks
    tn_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM tasting_notes 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    fp_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    refs_fk_missing = cur.execute("""
        SELECT COUNT(*) FROM official_source_references 
        WHERE entity_type = 'whisky' AND entity_id NOT IN (SELECT whisky_id FROM whiskies)
    """).fetchone()[0]

    # 7. Duplicate Checks
    duplicate_fp_groups = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT whisky_id FROM flavor_profiles 
            GROUP BY whisky_id HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    duplicate_refs_count = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT entity_id, source_url, field_name, field_value 
            FROM official_source_references 
            GROUP BY entity_id, source_url, field_name, field_value 
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    duplicate_tn_fingerprints = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT nose_notes, palate_notes, finish_notes 
            FROM tasting_notes 
            GROUP BY nose_notes, palate_notes, finish_notes 
            HAVING COUNT(*) > 1 AND nose_notes != '' AND palate_notes != ''
        )
    """).fetchone()[0]

    # 8. Value validation
    # Check flavor_profile JSON scores
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

    # Check official source refs confidence
    invalid_confidence_count = cur.execute("""
        SELECT COUNT(*) FROM official_source_references 
        WHERE confidence < 0.0 OR confidence > 1.0
    """).fetchone()[0]

    # Check missing source_url or source_domain
    missing_source_info_count = cur.execute("""
        SELECT COUNT(*) FROM official_source_references 
        WHERE source_url IS NULL OR source_url = '' 
           OR source_domain IS NULL OR source_domain = ''
    """).fetchone()[0]

    # Check suspicious copyright/license risk values
    suspicious_copyright_license_count = cur.execute("""
        SELECT COUNT(*) FROM official_source_references 
        WHERE copyright_risk NOT IN ('low') OR license_risk NOT IN ('low')
    """).fetchone()[0]

    # 9. App Readiness Joins
    sample_detail_issues = 0
    try:
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
                sample_detail_issues += 1
    except Exception as e:
        print(f"Sample query failed: {e}")
        sample_detail_issues += 1

    sample_attribution_issues = 0
    try:
        attribution_query = """
            SELECT w.whisky_id, w.name, r.source_name, r.field_name, r.field_value
            FROM whiskies w
            JOIN official_source_references r ON w.whisky_id = r.entity_id
            WHERE r.entity_type = 'whisky'
            LIMIT 50
        """
        attribution_rows = cur.execute(attribution_query).fetchall()
        if len(attribution_rows) == 0:
            sample_attribution_issues += 1
    except Exception as e:
        print(f"Attribution query failed: {e}")
        sample_attribution_issues += 1

    conn.close()

    # 10. Git Status Risk Summary
    git_db_modified = False
    git_db_staged = False
    git_backup_staged = False
    git_retail_visible = False

    try:
        status_out = subprocess.check_output(["git", "status", "--short"], text=True)
        for line in status_out.splitlines():
            line_clean = line.strip()
            # Staged file patterns: status prefix starts with A, M, R, C
            is_staged = line[0] in ['A', 'M', 'R', 'C']
            is_unstaged = line[1] in ['M', 'D'] or line.startswith('??')
            
            if "production.db" in line_clean:
                if is_unstaged:
                    git_db_modified = True
                if is_staged:
                    git_db_staged = True
            elif "backup" in line_clean.lower() or "production_before_" in line_clean.lower():
                if is_staged:
                    git_backup_staged = True
            if "scripts/retail_sources" in line_clean:
                git_retail_visible = True
    except Exception as e:
        print(f"Failed to check git status: {e}")

    # expected counts check
    expected_matches = (
        tasting_notes_count == 496 and
        flavor_profiles_count == 626 and
        region_filled == 301 and
        cask_type_filled == 54 and
        official_source_refs_count == 94
    )

    go_conditions = (
        integrity_ok and
        expected_matches and
        tn_fk_missing == 0 and
        fp_fk_missing == 0 and
        refs_fk_missing == 0 and
        duplicate_fp_groups == 0 and
        duplicate_refs_count == 0 and
        invalid_score_count == 0 and
        invalid_confidence_count == 0 and
        missing_source_info_count == 0 and
        sample_detail_issues == 0 and
        sample_attribution_issues == 0 and
        not git_db_staged and
        not git_backup_staged
    )

    decision = "GO" if go_conditions else "NO-GO"

    # Write Gate File
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(decision)

    # Write Markdown Report
    report = []
    report.append("# Final DB Checkpoint QA Report (v3)\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Data QA Gate Status:** **{decision}**")
    report.append(f"- **Latest DB Hash:** `{db_hash}`\n")
    
    report.append("## Core Metrics Summary")
    report.append(f"- Whiskies Count: {whiskies_count}")
    report.append(f"- Distilleries Count: {distilleries_count}")
    report.append(f"- Tasting Notes Count: {tasting_notes_count} (Expected: 496) - {'OK' if tasting_notes_count == 496 else 'FAILED'}")
    report.append(f"- Flavor Profiles Count: {flavor_profiles_count} (Expected: 626) - {'OK' if flavor_profiles_count == 626 else 'FAILED'}")
    report.append(f"- Official Source References Count: {official_source_refs_count} (Expected: 94) - {'OK' if official_source_refs_count == 94 else 'FAILED'}\n")

    report.append("## Coverage & Completeness Analysis")
    report.append("### Tasting Notes Coverage")
    report.append(f"- Whiskies with Tasting Notes (Distinct): {whiskies_with_tn}")
    report.append(f"- Whiskies missing Tasting Notes: {missing_tn_count}")
    report.append("### Flavor Profile Coverage")
    report.append(f"- Whiskies with Flavor Profiles (Distinct): {whiskies_with_fp}")
    report.append(f"- Whiskies missing Flavor Profiles: {missing_fp_count}")
    report.append("### Metadata Coverage")
    report.append(f"- Region filled: {region_filled} (Expected: 301) / missing: {region_missing}")
    report.append(f"- Cask Type filled: {cask_type_filled} (Expected: 54) / missing: {cask_type_missing}")
    report.append(f"- Age filled: {age_filled} / missing: {age_missing}")
    report.append(f"- ABV filled: {abv_filled} / missing: {abv_missing}\n")

    report.append("## Database Integrity Check")
    report.append(f"- PRAGMA integrity_check: {'ok' if integrity_ok else 'FAILED'}")
    report.append(f"- Tasting Note Foreign Key Missing: {tn_fk_missing} (Expected: 0)")
    report.append(f"- Flavor Profile Foreign Key Missing: {fp_fk_missing} (Expected: 0)")
    report.append(f"- Official Ref Foreign Key Missing: {refs_fk_missing} (Expected: 0)\n")

    report.append("## Duplicate Checks")
    report.append(f"- Duplicate Flavor Profiles per Whisky ID: {duplicate_fp_groups} (Expected: 0)")
    report.append(f"- Duplicate Official Refs (entity_id + source + field): {duplicate_refs_count} (Expected: 0)")
    report.append(f"- Duplicate Tasting Note Fingerprints: {duplicate_tn_fingerprints}\n")

    report.append("## Value Validation")
    report.append(f"- Invalid Flavor Profile Scores count (< 0.0): {invalid_score_count} (Expected: 0)")
    report.append(f"- Invalid Official Ref Confidence count (not 0..1): {invalid_confidence_count} (Expected: 0)")
    report.append(f"- Missing Source URL/Domain count: {missing_source_info_count} (Expected: 0)")
    report.append(f"- Suspicious Copyright/License Risk count (not 'low'): {suspicious_copyright_license_count} (Expected: 0)\n")

    report.append("## App Readiness Joins Validation")
    report.append(f"- Sample Whisky Detail Join Issues: {sample_detail_issues} (Expected: 0)")
    report.append(f"- Sample Attribution Join Issues: {sample_attribution_issues} (Expected: 0)\n")

    report.append("## Git Status Risk Summary")
    report.append(f"- production.db modified: {'Yes' if git_db_modified else 'No'}")
    report.append(f"- production.db staged: {'Yes' if git_db_staged else 'No'} - {'OK (Not Staged)' if not git_db_staged else 'FAILED (Staged!)'}")
    report.append(f"- backup DB files staged: {'Yes' if git_backup_staged else 'No'} - {'OK (Not Staged)' if not git_backup_staged else 'FAILED (Staged!)'}")
    report.append(f"- scripts/retail_sources visible in status: {'Yes' if git_retail_visible else 'No'} (Should be ignored)\n")

    report.append("## Final Verdict")
    if go_conditions:
        report.append("**GO** - Veritabanı bütünlük, FK, metrik hedefleri ve git risk kontrolleri başarıyla doğrulandı. Sürüm yayınlama için veri katmanı hazır durumdadır.")
    else:
        report.append("**NO-GO** - Bazı veritabanı hedefleri veya güvenlik limitleri doğrulamadan geçemedi. Lütfen yukarıdaki detayları inceleyin.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"v3 QA smoke test run complete. Verdict: {decision}")

if __name__ == "__main__":
    main()

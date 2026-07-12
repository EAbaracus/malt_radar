import os
import csv
import sqlite3
import hashlib
import json

OUT_PROFILES = "data/manual_sources/p2_review_post_apply_audit_profiles.csv"
OUT_WARNINGS = "data/manual_sources/p2_review_post_apply_audit_warnings.csv"
REPORT_MD = "output/reports/p2_review_post_apply_audit_report.md"
GATE_TXT = "output/reports/p2_review_post_apply_audit_gate.txt"
PROD_DB = "output/import/production.db"

EXPECTED_HASH = "0C4F7000B67F6EAF6FE16CE5336D7C3C22C46D635D25D6A1833E1594EE33DD33"
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
    print("=== DATA-COVERAGE-P2-REVIEW-POST-APPLY-AUDIT ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PROFILES), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    conn = sqlite3.connect(f"file:{os.path.abspath(PROD_DB)}?mode=ro", uri=True)
    cur = conn.cursor()

    total_whiskies = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    total_profiles = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    
    fk_missing_count = cur.execute("SELECT COUNT(*) FROM flavor_profiles fp LEFT JOIN whiskies w ON w.whisky_id = fp.whisky_id WHERE w.whisky_id IS NULL").fetchone()[0]
    duplicate_profiles_count = cur.execute("SELECT COUNT(*) FROM (SELECT whisky_id, flavor_source, COUNT(*) c FROM flavor_profiles GROUP BY whisky_id, flavor_source HAVING c > 1)").fetchone()[0]
    
    p2_rows = cur.execute("SELECT whisky_id, whisky_name, flavor_source, flavor_vector FROM flavor_profiles WHERE flavor_source LIKE 'p2_review_promotable%'").fetchall()
    
    conn.close()

    profiles_data = []
    warnings_data = []

    p2_count = len(p2_rows)
    invalid_score_count = 0
    low_signal_count = 0
    all_zero_count = 0
    one_axis_count = 0
    source_missing_count = 0

    axis_sums = {k: 0.0 for k in APP_KEYS}
    global_min = 1.0
    global_max = 0.0
    dominant_axis_counts = {k: 0 for k in APP_KEYS}

    for row in p2_rows:
        wid, name, source, vector_json = row
        
        vector = {}
        try:
            if vector_json:
                vector = json.loads(vector_json)
        except:
            pass

        active_axes = 0
        max_score = 0.0
        missing_axes = []
        dominant_axis = None
        
        has_invalid = False
        
        for k in APP_KEYS:
            val = safe_float(vector.get(k, 0))
            axis_sums[k] += val
            
            if val < 0.0 or val > 1.0:
                has_invalid = True
            
            if val < global_min: global_min = val
            if val > global_max: global_max = val

            if val > 0:
                active_axes += 1
                if val > max_score:
                    max_score = val
                    dominant_axis = k
            else:
                missing_axes.append(k)
        
        if dominant_axis:
            dominant_axis_counts[dominant_axis] += 1

        if has_invalid:
            invalid_score_count += 1
            
        if active_axes < 2:
            low_signal_count += 1
            if active_axes == 1:
                one_axis_count += 1
            elif active_axes == 0:
                all_zero_count += 1

        source_system = ""
        if ":" in source:
            source_system = source.split(":", 1)[1]
        
        if not source_system:
            source_missing_count += 1
            warnings_data.append({
                "whisky_id": wid,
                "issue": "missing_source_system",
                "flavor_source": source
            })

        if max_score < 0.2 and max_score > 0:
            warnings_data.append({
                "whisky_id": wid,
                "issue": "flat_profile_max_score_low",
                "max_score": max_score
            })
            
        profiles_data.append({
            "whisky_id": wid,
            "whisky_name": name,
            "flavor_source": source,
            "source_system": source_system,
            "active_axes_count": active_axes,
            "max_score": max_score,
            "dominant_axis": dominant_axis,
            "missing_axes": "|".join(missing_axes),
            **{k: safe_float(vector.get(k, 0)) for k in APP_KEYS}
        })

    if profiles_data:
        out_fields = list(profiles_data[0].keys())
        with open(OUT_PROFILES, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(profiles_data)
    else:
        with open(OUT_PROFILES, "w", encoding="utf-8") as f:
            f.write("whisky_id\n")
            f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


    if warnings_data:
        out_fields = ["whisky_id", "issue", "flavor_source", "max_score"]
        with open(OUT_WARNINGS, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(warnings_data)
    else:
        with open(OUT_WARNINGS, "w", encoding="utf-8") as f:
            f.write("whisky_id,issue\n")

    hash_after = get_file_hash(PROD_DB)

    # Coverage
    coverage_pct = (total_profiles / total_whiskies * 100) if total_whiskies > 0 else 0
    
    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after:
        verdict = "NO-GO"
    if p2_count != 16 or total_profiles != 648:
        verdict = "NO-GO"
    if fk_missing_count > 0 or duplicate_profiles_count > 0 or invalid_score_count > 0 or low_signal_count > 0 or all_zero_count > 0 or one_axis_count > 0:
        verdict = "NO-GO"
    
    if verdict == "GO" and len(warnings_data) > 0:
        verdict = "WARN_GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)

    report = []
    report.append("# P2 Review Post-Apply Audit Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## 1. General DB Integrity")
    report.append(f"- Total whiskies: `{total_whiskies}`")
    report.append(f"- Total flavor_profiles: `{total_profiles}`")
    report.append(f"- P2 profiles: `{p2_count}`")
    report.append(f"- FK missing count: `{fk_missing_count}`")
    report.append(f"- Duplicate profiles count: `{duplicate_profiles_count}`")
    report.append(f"- Invalid score count: `{invalid_score_count}`")
    report.append(f"- Low signal count (<2 axes): `{low_signal_count}`\n")

    report.append("## 2. P2 Added Profiles Specific Check")
    report.append(f"- All-zero profiles: `{all_zero_count}`")
    report.append(f"- One-axis profiles: `{one_axis_count}`")
    report.append(f"- Warnings generated: `{len(warnings_data)}`")
    report.append(f"- Source system missing: `{source_missing_count}`\n")

    report.append("## 3. Coverage Impact")
    report.append(f"- Profiles Before: `632`")
    report.append(f"- Profiles After: `{total_profiles}`")
    report.append(f"- Net Increase: `{total_profiles - 632}`")
    report.append(f"- Overall Profile Coverage: `{coverage_pct:.2f}%`\n")

    report.append("## 4. Radar Distribution Analysis (for P2)")
    report.append(f"- Global Min Score: `{global_min:.2f}`")
    report.append(f"- Global Max Score: `{global_max:.2f}`")
    report.append("- Average score per axis:")
    for k in APP_KEYS:
        avg = axis_sums[k] / p2_count if p2_count > 0 else 0
        report.append(f"  - `{k}`: `{avg:.2f}`")
    report.append("- Dominant axis distribution:")
    for k, v in dominant_axis_counts.items():
        if v > 0:
            report.append(f"  - `{k}`: `{v}`")
    report.append("\n")
    
    report.append("## 5. State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Audit completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

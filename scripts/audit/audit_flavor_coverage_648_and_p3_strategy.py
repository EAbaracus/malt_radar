import os
import csv
import sqlite3
import hashlib
import json
from collections import defaultdict

PROD_DB = "output/import/production.db"
EXPECTED_HASH = "0C4F7000B67F6EAF6FE16CE5336D7C3C22C46D635D25D6A1833E1594EE33DD33"
APP_KEYS = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "floral_herbal", "malty_cereal"]

REPORT_MD = "output/reports/flavor_coverage_audit_648_report.md"
GATE_TXT = "output/reports/flavor_coverage_audit_648_gate.txt"
STRATEGY_MD = "output/reports/p3_source_strategy_recommendation.md"

CSV_REGION = "data/output/flavor_coverage_gap_by_region_648.csv"
CSV_TYPE = "data/output/flavor_coverage_gap_by_type_648.csv"
CSV_DISTILLERY = "data/output/flavor_coverage_gap_by_distillery_648.csv"
CSV_SOURCE = "data/output/flavor_profiles_source_distribution_648.csv"
CSV_RADAR = "data/output/flavor_profiles_radar_distribution_648.csv"
CSV_PRIORITY_W = "data/output/p3_priority_whiskies_without_profiles.csv"
CSV_PRIORITY_D = "data/output/p3_priority_distilleries_without_profiles.csv"

def get_file_hash(path):
    if not os.path.exists(path): return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536): hasher.update(chunk)
    return hasher.hexdigest().upper()

def safe_float(val):
    try: return float(val)
    except: return 0.0

def main():
    print("=== DATA-COVERAGE-FLAVOR-COVERAGE-AUDIT-648 ===")
    
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(CSV_REGION), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    conn = sqlite3.connect(f"file:{os.path.abspath(PROD_DB)}?mode=ro", uri=True)
    cur = conn.cursor()

    # Get whiskies and distilleries
    cur.execute('''
        SELECT w.whisky_id, w.name, w.region, w.type, d.name AS dist_name 
        FROM whiskies w 
        LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
    ''')
    whiskies_data = cur.fetchall()
    
    # Get profiles
    cur.execute("SELECT whisky_id, flavor_source, flavor_vector FROM flavor_profiles")
    profiles_data = cur.fetchall()

    conn.close()

    total_whiskies = len(whiskies_data)
    total_profiles = len(profiles_data)
    
    # Analyze whiskies
    whisky_profiles = defaultdict(list)
    source_counts = defaultdict(int)
    
    fk_missing = 0
    duplicate_profiles = 0
    invalid_score_count = 0
    low_signal_count = 0
    all_zero_count = 0

    radar_stats = {k: {"sum": 0.0, "min": 1.0, "max": 0.0, "zeros": 0} for k in APP_KEYS}
    
    for wid, source, vector_json in profiles_data:
        whisky_profiles[wid].append(source)
        
        if source:
            source_group = source.split(':')[0] if ':' in source else source
        else:
            source_group = "unknown"
        source_counts[source_group] += 1
        
        vector = {}
        try:
            if vector_json: 
                parsed = json.loads(vector_json)
                if isinstance(parsed, dict):
                    vector = parsed
        except: pass
        
        active_axes = 0
        has_invalid = False
        for k in APP_KEYS:
            val = safe_float(vector.get(k, 0))
            if val < 0.0 or val > 1.0: has_invalid = True
            
            radar_stats[k]["sum"] += val
            if val < radar_stats[k]["min"]: radar_stats[k]["min"] = val
            if val > radar_stats[k]["max"]: radar_stats[k]["max"] = val
            if val == 0.0: radar_stats[k]["zeros"] += 1
            elif val > 0: active_axes += 1

        if has_invalid: invalid_score_count += 1
        if active_axes == 0: all_zero_count += 1
        elif active_axes < 2: low_signal_count += 1
            
    # Check FK and duplicates
    valid_wids = {row[0] for row in whiskies_data}
    for wid, sources in whisky_profiles.items():
        if wid not in valid_wids: fk_missing += 1
        if len(sources) > 1: duplicate_profiles += 1
        
    # Grouping aggregations
    region_stats = defaultdict(lambda: {"total": 0, "covered": 0})
    type_stats = defaultdict(lambda: {"total": 0, "covered": 0})
    distillery_stats = defaultdict(lambda: {"total": 0, "covered": 0})
    
    missing_whiskies = []

    for wid, name, region, wtype, dist_name in whiskies_data:
        r = region or "Unknown"
        t = wtype or "Unknown"
        d = dist_name or "Unknown"
        
        has_prof = 1 if wid in whisky_profiles else 0
        
        region_stats[r]["total"] += 1
        region_stats[r]["covered"] += has_prof
        
        type_stats[t]["total"] += 1
        type_stats[t]["covered"] += has_prof
        
        distillery_stats[d]["total"] += 1
        distillery_stats[d]["covered"] += has_prof
        
        if not has_prof:
            missing_whiskies.append({"whisky_id": wid, "name": name, "region": r, "type": t, "distillery": d})
            
    # Write CSVs
    def write_gap_csv(path, stats_dict, key_name):
        rows = []
        for k, v in stats_dict.items():
            gap = v["total"] - v["covered"]
            cov_pct = (v["covered"] / v["total"] * 100) if v["total"] > 0 else 0
            rows.append({key_name: k, "total": v["total"], "covered": v["covered"], "gap": gap, "coverage_pct": round(cov_pct, 2)})
        rows.sort(key=lambda x: x["gap"], reverse=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[key_name, "total", "covered", "gap", "coverage_pct"])
            writer.writeheader()
            writer.writerows(rows)
            
    write_gap_csv(CSV_REGION, region_stats, "region")
    write_gap_csv(CSV_TYPE, type_stats, "type")
    write_gap_csv(CSV_DISTILLERY, distillery_stats, "distillery")
    
    with open(CSV_SOURCE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_group", "count"])
        for k, v in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([k, v])
            
    with open(CSV_RADAR, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["axis", "min_score", "max_score", "avg_score", "zero_count"])
        for k in APP_KEYS:
            avg = radar_stats[k]["sum"] / total_profiles if total_profiles > 0 else 0
            writer.writerow([k, round(radar_stats[k]["min"], 2), round(radar_stats[k]["max"], 2), round(avg, 2), radar_stats[k]["zeros"]])

    with open(CSV_PRIORITY_W, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["whisky_id", "name", "region", "type", "distillery"])
        writer.writeheader()
        writer.writerows(missing_whiskies[:50])

    dist_gaps = []
    for d, v in distillery_stats.items():
        if v["total"] - v["covered"] > 0:
            dist_gaps.append({"distillery": d, "gap": v["total"] - v["covered"], "total": v["total"]})
    dist_gaps.sort(key=lambda x: x["gap"], reverse=True)
    with open(CSV_PRIORITY_D, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["distillery", "gap", "total"])
        writer.writeheader()
        writer.writerows(dist_gaps[:20])

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after: verdict = "NO-GO"
    if total_profiles != 648 or fk_missing > 0 or duplicate_profiles > 0 or invalid_score_count > 0: verdict = "NO-GO"
    if low_signal_count > 0 or all_zero_count > 0: verdict = "WARN_GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    # Strategy MD
    strategy = """# P3 Source Strategy Recommendation

Based on the coverage gaps identified, the following lane categorizations are recommended for P3 Phase:

### P3_AUTO_SAFE
- Highly structured factual sources (e.g. Master of Malt structured tags, official Distillery JSON APIs).
- Direct extraction with low risk. No text interpretation.

### P3_MANUAL_SAFE
- Unstructured but objective retailer notes (e.g. Alko, WhiskyBase structured tags).
- Requires a human/AI pass to extract into 0.0-1.0 confidence vectors, followed by manual review of the preview pack.

### P3_VALIDATION_ONLY
- Copyrighted books, deep prose tasting notes, subjective blogs.
- Should NOT be inserted into `flavor_profiles`.
- Keep in a separate validation table if needed, or SKIP completely.

### P3_SKIP
- Sources previously flagged as poor quality (e.g. legacy WhiskeyMapper component vectors).
- High-risk scrape targets without clear factual flavor tags.
"""
    with open(STRATEGY_MD, "w", encoding="utf-8") as f:
        f.write(strategy)

    # Report MD
    cov_pct = (total_profiles / total_whiskies * 100) if total_whiskies > 0 else 0
    report = [
        f"# Flavor Coverage Audit 648 Report",
        f"- **Verdict:** **{verdict}**",
        f"",
        f"## 1. General Coverage",
        f"- Total Whiskies: `{total_whiskies}`",
        f"- Total Flavor Profiles: `{total_profiles}`",
        f"- Coverage: `{cov_pct:.2f}%`",
        f"- Profilsiz Whisky: `{total_whiskies - total_profiles}`",
        f"- FK Missing: `{fk_missing}`",
        f"- Duplicate Profiles: `{duplicate_profiles}`",
        f"- Invalid Scores: `{invalid_score_count}`",
        f"- Low Signal Profiles: `{low_signal_count}`",
        f"- All Zero Profiles: `{all_zero_count}`",
        f"",
        f"## 2. Top Gap by Region",
    ]
    for r in sorted(region_stats.items(), key=lambda x: x[1]["total"] - x[1]["covered"], reverse=True)[:5]:
        gap = r[1]["total"] - r[1]["covered"]
        report.append(f"- {r[0]}: {gap} missing (Total: {r[1]['total']})")
    
    report.append("\n## 3. Top Gap by Distillery")
    for d in dist_gaps[:5]:
        report.append(f"- {d['distillery']}: {d['gap']} missing")
        
    report.append("\n## 4. State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Audit completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

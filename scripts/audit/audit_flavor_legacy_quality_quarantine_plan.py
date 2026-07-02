import os
import csv
import sqlite3
import hashlib
import json
from collections import defaultdict

PROD_DB = "output/import/production.db"
EXPECTED_HASH = "0C4F7000B67F6EAF6FE16CE5336D7C3C22C46D635D25D6A1833E1594EE33DD33"
APP_KEYS = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "floral_herbal", "malty_cereal"]

REPORT_MD = "output/reports/flavor_legacy_quality_quarantine_plan.md"
GATE_TXT = "output/reports/flavor_legacy_quality_quarantine_gate.txt"

CSV_ALL = "data/output/flavor_legacy_quality_classification.csv"
CSV_INV = "data/output/flavor_legacy_quarantine_invalid_score.csv"
CSV_ZERO = "data/output/flavor_legacy_quarantine_all_zero.csv"
CSV_VALID = "data/output/flavor_legacy_active_valid_profiles.csv"
CSV_SOURCE = "data/output/flavor_legacy_source_quality_distribution.csv"
CSV_COV = "data/output/flavor_effective_coverage_after_quality_filter.csv"

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
    print("=== DATA-COVERAGE-FLAVOR-LEGACY-QUALITY-QUARANTINE-PLAN ===")
    
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(CSV_ALL), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    conn = sqlite3.connect(f"file:{os.path.abspath(PROD_DB)}?mode=ro", uri=True)
    cur = conn.cursor()

    valid_wids = set(r[0] for r in cur.execute("SELECT whisky_id FROM whiskies").fetchall())
    total_whiskies = len(valid_wids)
    
    cur.execute("SELECT whisky_id, flavor_source, flavor_vector FROM flavor_profiles")
    profiles_data = cur.fetchall()
    conn.close()

    total_profiles = len(profiles_data)
    
    wid_counts = defaultdict(int)
    for wid, _, _ in profiles_data:
        wid_counts[wid] += 1

    classified_data = []
    class_counts = {
        "active_valid": 0,
        "active_warn_low_signal": 0,
        "quarantine_invalid_score": 0,
        "quarantine_all_zero": 0,
        "quarantine_duplicate_or_fk_risk": 0,
        "review_legacy_source": 0
    }
    
    source_quality = defaultdict(lambda: {k: 0 for k in class_counts.keys()})
    p2_valid_count = 0
    p2_total_count = 0

    for wid, source, vector_json in profiles_data:
        source_str = source or "unknown"
        source_group = source_str.split(':')[0]
        
        parsed = None
        try:
            if vector_json: parsed = json.loads(vector_json)
        except: pass
        
        values = []
        active_app = 0
        if isinstance(parsed, dict):
            values = [safe_float(v) for v in parsed.values()]
            active_app = sum(1 for k in APP_KEYS if safe_float(parsed.get(k, 0)) > 0.0)
        elif isinstance(parsed, list):
            values = [safe_float(v) for v in parsed]
        
        has_invalid = any(v < 0.0 or v > 1.0 for v in values)
        active_any = sum(1 for v in values if v > 0.0)

        # Classification Logic
        cls = "review_legacy_source"
        if wid not in valid_wids or wid_counts[wid] > 1:
            cls = "quarantine_duplicate_or_fk_risk"
        elif has_invalid:
            cls = "quarantine_invalid_score"
        elif active_any == 0:
            cls = "quarantine_all_zero"
        elif active_any > 0 and active_app == 0:
            cls = "review_legacy_source"
        elif active_app < 2:
            cls = "active_warn_low_signal"
        else:
            cls = "active_valid"

        class_counts[cls] += 1
        source_quality[source_group][cls] += 1
        
        if source_group.startswith("p2_review_promotable"):
            p2_total_count += 1
            if cls == "active_valid":
                p2_valid_count += 1

        classified_data.append({
            "whisky_id": wid,
            "flavor_source": source_str,
            "quality_class": cls,
            "active_any": active_any,
            "active_app": active_app,
            "has_invalid": has_invalid
        })

    # Write CSVs
    def write_subset(path, filter_cls=None):
        subset = [d for d in classified_data if filter_cls is None or d["quality_class"] == filter_cls]
        with open(path, "w", newline="", encoding="utf-8") as f:
            if subset:
                writer = csv.DictWriter(f, fieldnames=subset[0].keys())
                writer.writeheader()
                writer.writerows(subset)
            else:
                f.write("whisky_id,flavor_source,quality_class,active_any,active_app,has_invalid\n")

    write_subset(CSV_ALL, None)
    write_subset(CSV_INV, "quarantine_invalid_score")
    write_subset(CSV_ZERO, "quarantine_all_zero")
    write_subset(CSV_VALID, "active_valid")

    with open(CSV_SOURCE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = ["source_group", "total"] + list(class_counts.keys())
        writer.writerow(headers)
        for sg, counts in source_quality.items():
            total = sum(counts.values())
            row = [sg, total] + [counts[c] for c in class_counts.keys()]
            writer.writerow(row)

    # Coverage calculations
    effective_valid = class_counts["active_valid"]
    raw_cov = (total_profiles / total_whiskies * 100) if total_whiskies > 0 else 0
    eff_cov = (effective_valid / total_whiskies * 100) if total_whiskies > 0 else 0

    with open(CSV_COV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "count", "percentage"])
        writer.writerow(["total_whiskies", total_whiskies, "100.0"])
        writer.writerow(["raw_flavor_profiles", total_profiles, round(raw_cov, 2)])
        writer.writerow(["effective_active_valid", effective_valid, round(eff_cov, 2)])

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after:
        verdict = "NO-GO"
    if total_profiles != 648:
        verdict = "NO-GO"
    if p2_total_count == 16 and p2_valid_count < 16:
        verdict = "WARN_GO"
    
    if verdict == "GO" and (class_counts["quarantine_invalid_score"] > 0 or class_counts["quarantine_all_zero"] > 0):
        verdict = "WARN_GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)

    report = [
        f"# Flavor Legacy Quality Quarantine Plan",
        f"- **Verdict:** **{verdict}**",
        f"",
        f"## 1. General Quality Distribution",
        f"- Total Flavor Profiles: `{total_profiles}`"
    ]
    for c, v in class_counts.items():
        report.append(f"- {c}: `{v}`")
        
    report.extend([
        f"",
        f"## 2. Source-Based Quality (Highlights)",
        f"- P2 Promotable Profiles: `{p2_total_count}` (Valid: `{p2_valid_count}`)"
    ])
    
    for sg, counts in source_quality.items():
        total = sum(counts.values())
        report.append(f"- **{sg}** (Total: {total}) -> Valid: {counts['active_valid']}, Invalid: {counts['quarantine_invalid_score']}, All-Zero: {counts['quarantine_all_zero']}, Legacy Review: {counts['review_legacy_source']}")

    report.extend([
        f"",
        f"## 3. App Impact & Recommendation",
        f"- **Radar Chart Risk:** Invalid scores (<0 or >1) will break frontend radar charting logic. All-Zero vectors render invisible.",
        f"- **Similarity Risk:** Cosine similarity with zero-vectors mathematically fails. Invalid bounds distort distance functions.",
        f"- **Proposed Fix:** Use app-layer filter `AppConfig.useQualityFilter = true` if available, or do a non-destructive DB cleanup by setting a `quarantine_flag` boolean column on `flavor_profiles`. Do NOT permanently delete `whiskeymapper` rows as they contain historical components that could be safely transformed.",
        f"",
        f"## 4. Coverage Adjustments",
        f"- Raw Coverage: `{total_profiles} / {total_whiskies}` (`{raw_cov:.2f}%`)",
        f"- Effective Valid Coverage: `{effective_valid} / {total_whiskies}` (`{eff_cov:.2f}%`)",
        f"- **P3 Strategy Note:** P3 must target replenishing the gap left by quarantined legacy rows.",
        f"",
        f"## 5. State Hash",
        f"- Expected Hash: `{EXPECTED_HASH}`",
        f"- Hash Before: `{hash_before}`",
        f"- Hash After: `{hash_after}`",
        f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`"
    ])

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Audit completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

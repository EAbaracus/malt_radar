import os
import csv
import json
import sqlite3
import hashlib

INVENTORY_CSV = "data/output/data_coverage_next_v12_source_lane_inventory.csv"
OUT_ALL = "data/output/data_coverage_p2_v1_candidates.csv"
OUT_HIGH = "data/output/data_coverage_p2_v1_high_candidates.csv"
OUT_REVIEW = "data/output/data_coverage_p2_v1_review_candidates.csv"
OUT_BLOCKED = "data/output/data_coverage_p2_v1_blocked_candidates.csv"
REPORT_MD = "output/reports/data_coverage_p2_v1_report.md"
GATE_TXT = "output/reports/data_coverage_p2_v1_gate.txt"
PROD_DB = "output/import/production.db"
EXPECTED_HASH = "EED7B761947451CB8B54DA024D1767BD2C90BD96914555C70F75BF6328E4F587"

APP_KEYS = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"]

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
        v = float(val)
        return v if not (v != v) else 0.0 # handle nan
    except:
        return 0.0

def main():
    print("=== DATA-COVERAGE-P2-V1 Accepted Manual Candidate Extraction ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_ALL), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    # 1. Load DB state
    conn = sqlite3.connect(f"file:{os.path.abspath(PROD_DB)}?mode=ro", uri=True)
    cur = conn.cursor()
    valid_whiskies = set(row[0] for row in cur.execute("SELECT whisky_id FROM whiskies").fetchall())
    existing_profiles = set(row[0] for row in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall())
    conn.close()

    p2_files = []
    if os.path.exists(INVENTORY_CSV):
        with open(INVENTORY_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("lane") == "P2":
                    p2_files.append(row["file"])

    all_candidates = []
    high_candidates = []
    review_candidates = []
    blocked_candidates = []

    seen_wids = set()
    already_has_profile_count = 0
    fk_missing_count = 0
    duplicate_count = 0
    invalid_score_count = 0
    raw_candidates_count = 0

    for fpath in p2_files:
        full_path = os.path.join("data", fpath)
        if not os.path.exists(full_path):
            continue
            
        with open(full_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_candidates_count += 1
                wid = row.get("whisky_id", "").strip()
                name = row.get("whisky_name", row.get("normalized_whisky_name", "")).strip()

                # Attempt to extract scores
                smoky = safe_float(row.get("smoky", 0))
                peaty = safe_float(row.get("peaty", 0))
                sweet = safe_float(row.get("sweet", 0))
                fruity = safe_float(row.get("fruity", 0))
                spicy = safe_float(row.get("spicy", 0))
                woody = safe_float(row.get("woody", 0))
                floral = safe_float(row.get("floral", 0))
                
                oak_cask = safe_float(row.get("oak_cask", woody))
                smoky_peaty = safe_float(row.get("smoky_peaty", max(smoky, peaty)))
                floral_herbal = safe_float(row.get("floral_herbal", floral))
                malty_cereal = safe_float(row.get("malty_cereal", 0))

                vector = {
                    "fruity": fruity,
                    "sweet": sweet,
                    "spicy": spicy,
                    "smoky_peaty": smoky_peaty,
                    "oak_cask": oak_cask,
                    "floral_herbal": floral_herbal,
                    "malty_cereal": malty_cereal
                }

                candidate = {
                    "whisky_id": wid,
                    "whisky_name": name,
                    "source_file": fpath,
                    "fruity": fruity,
                    "sweet": sweet,
                    "spicy": spicy,
                    "smoky_peaty": smoky_peaty,
                    "oak_cask": oak_cask,
                    "floral_herbal": floral_herbal,
                    "malty_cereal": malty_cereal
                }
                
                all_candidates.append(candidate)

                # Rules for BLOCKED
                is_blocked = False
                block_reason = []

                if not wid:
                    is_blocked = True
                    block_reason.append("no_whisky_id")
                    fk_missing_count += 1
                elif wid not in valid_whiskies:
                    is_blocked = True
                    block_reason.append("fk_missing")
                    fk_missing_count += 1
                
                if wid in existing_profiles:
                    is_blocked = True
                    block_reason.append("already_has_profile")
                    already_has_profile_count += 1
                    
                if wid and wid in seen_wids:
                    is_blocked = True
                    block_reason.append("duplicate")
                    duplicate_count += 1
                    
                if wid:
                    seen_wids.add(wid)

                has_invalid = False
                active_axes = 0
                for v in vector.values():
                    if v < 0.0 or v > 1.0:
                        has_invalid = True
                    if v > 0:
                        active_axes += 1
                        
                if has_invalid:
                    is_blocked = True
                    block_reason.append("invalid_score")
                    invalid_score_count += 1

                candidate["status_reason"] = "|".join(block_reason)

                if is_blocked:
                    blocked_candidates.append(candidate)
                elif active_axes >= 3:
                    high_candidates.append(candidate)
                else:
                    review_candidates.append(candidate)

    # Write CSVs
    out_fields = ["whisky_id", "whisky_name", "source_file", "fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "floral_herbal", "malty_cereal", "status_reason"]
    
    for path, data_list in [
        (OUT_ALL, all_candidates),
        (OUT_HIGH, high_candidates),
        (OUT_REVIEW, review_candidates),
        (OUT_BLOCKED, blocked_candidates)
    ]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(data_list)

    hash_after = get_file_hash(PROD_DB)

    # Verdict
    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after:
        verdict = "NO-GO"
    if raw_candidates_count == 0:
        verdict = "WARN_GO"

    # Write Gate
    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    # Write Report
    report = []
    report.append("# DATA-COVERAGE-P2-V1 — Accepted Manual Candidate Extraction Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## Extraction Results")
    report.append(f"- P2 Raw Candidates Count: `{raw_candidates_count}`")
    report.append(f"- HIGH Confidence Candidates: `{len(high_candidates)}`")
    report.append(f"- REVIEW Candidates: `{len(review_candidates)}`")
    report.append(f"- BLOCKED Candidates: `{len(blocked_candidates)}`\n")

    report.append("## Blocked Breakdown (may overlap)")
    report.append(f"- Already has profile: `{already_has_profile_count}`")
    report.append(f"- FK Missing / No ID: `{fk_missing_count}`")
    report.append(f"- Duplicate ID in batch: `{duplicate_count}`")
    report.append(f"- Invalid Score Count: `{invalid_score_count}`\n")

    report.append("## State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Extraction completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

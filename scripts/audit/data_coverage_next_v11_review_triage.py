import os
import csv
import json
import sqlite3
import hashlib

INPUT_CSV = "data/output/data_coverage_next_v3_manual_qa_pack.csv"
OUT_STRONG = "data/output/data_coverage_next_v11_stronger_accept_preview.csv"
OUT_KEEP = "data/output/data_coverage_next_v11_keep_manual_review.csv"
OUT_REJECT = "data/output/data_coverage_next_v11_reject_preview.csv"
REPORT_MD = "output/reports/data_coverage_next_v11_report.md"
GATE_TXT = "output/reports/data_coverage_next_v11_gate.txt"
PROD_DB = "output/import/production.db"

EXPECTED_HASH = "EED7B761947451CB8B54DA024D1767BD2C90BD96914555C70F75BF6328E4F587"

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
    print("=== DATA-COVERAGE-NEXT-V11 Review Candidate Triage ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_STRONG), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    strong_list = []
    keep_list = []
    reject_list = []
    
    invalid_score_count = 0
    duplicate_check = set()
    duplicate_count = 0

    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            for row in reader:
                if row.get("qa_decision") != "needs_manual_review":
                    continue
                
                wid = row["whisky_id"]
                if wid in duplicate_check:
                    duplicate_count += 1
                duplicate_check.add(wid)
                
                # Parse evidence terms
                terms_str = row.get("evidence_terms", "")
                terms = [t.strip() for t in terms_str.split(",") if t.strip()]
                term_count = len(terms)
                
                # Parse scores
                smoky = safe_float(row.get("smoky", 0))
                peaty = safe_float(row.get("peaty", 0))
                sweet = safe_float(row.get("sweet", 0))
                fruity = safe_float(row.get("fruity", 0))
                spicy = safe_float(row.get("spicy", 0))
                woody = safe_float(row.get("woody", 0))
                floral = safe_float(row.get("floral", 0))
                
                # App mapping
                mapped = {
                    "fruity": fruity,
                    "sweet": sweet,
                    "spicy": spicy,
                    "smoky_peaty": max(smoky, peaty),
                    "oak_cask": woody,
                    "floral_herbal": floral,
                    "malty_cereal": 0.0
                }
                
                # Metrics
                max_score = 0.0
                active_axes = 0
                for v in mapped.values():
                    if v > max_score:
                        max_score = v
                    if v > 0.0:
                        active_axes += 1
                    if v < 0.0 or v > 1.0:
                        invalid_score_count += 1

                # Triage Logic
                triage = "keep_manual_review"
                if term_count >= 5 and active_axes >= 3 and max_score >= 0.40:
                    triage = "stronger_accept_preview"
                elif term_count <= 2 or max_score < 0.30 or active_axes < 2:
                    triage = "reject_preview"
                    
                row["qa_decision"] = triage
                
                if triage == "stronger_accept_preview":
                    strong_list.append(row)
                elif triage == "keep_manual_review":
                    keep_list.append(row)
                else:
                    reject_list.append(row)

    total_input = len(strong_list) + len(keep_list) + len(reject_list)

    # Write outputs
    for filepath, data_list in [
        (OUT_STRONG, strong_list),
        (OUT_KEEP, keep_list),
        (OUT_REJECT, reject_list)
    ]:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if fieldnames:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data_list)

    hash_after = get_file_hash(PROD_DB)

    # Verdict
    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after: verdict = "NO-GO"
    if total_input != 33: verdict = "NO-GO"
    if duplicate_count > 0: verdict = "NO-GO"
    if invalid_score_count > 0: verdict = "NO-GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


    # Report
    report = []
    report.append("# DATA-COVERAGE-NEXT-V11 — Review Candidate Triage Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## Triage Results")
    report.append(f"- Input needs_manual_review count: `{total_input}`")
    report.append(f"- Stronger Accept Preview count: `{len(strong_list)}`")
    report.append(f"- Keep Manual Review count: `{len(keep_list)}`")
    report.append(f"- Reject Preview count: `{len(reject_list)}`\n")

    report.append("## Validations")
    report.append(f"- Duplicate whisky_id count: `{duplicate_count}`")
    report.append(f"- Invalid Score Count: `{invalid_score_count}`\n")

    report.append("## State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Triage completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

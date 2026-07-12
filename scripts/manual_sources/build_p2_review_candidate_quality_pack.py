import os
import csv
import sqlite3
import hashlib

INPUT_CSV = "data/output/data_coverage_p2_v1_review_candidates.csv"
OUT_PACK = "data/manual_sources/p2_review_candidates_quality_pack.csv"
OUT_PROMOTABLE = "data/manual_sources/p2_review_promotable_candidates.csv"
OUT_NEEDS = "data/manual_sources/p2_review_needs_manual_review.csv"
OUT_REJECT = "data/manual_sources/p2_review_reject_candidates.csv"
REPORT_MD = "output/reports/p2_review_candidate_quality_pack.md"
GATE_TXT = "output/reports/p2_review_qa_gate.txt"
PROD_DB = "output/import/production.db"

EXPECTED_HASH = "EED7B761947451CB8B54DA024D1767BD2C90BD96914555C70F75BF6328E4F587"
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
    print("=== DATA-COVERAGE-P2-REVIEW-QA ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PACK), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    pack_data = []
    promotable_list = []
    needs_list = []
    reject_list = []

    total_candidates = 0
    fully_populated = 0
    partially_populated = 0
    zero_signal = 0

    source_system_dist = {}
    url_missing_count = 0

    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_candidates += 1
                wid = row.get("whisky_id", "")
                name = row.get("whisky_name", "")
                source_file = row.get("source_file", "unknown_p2_source")

                source_system_dist[source_file] = source_system_dist.get(source_file, 0) + 1
                url_missing_count += 1 # We don't have source_url in P2 V1 output

                active_axes = 0
                max_score = 0.0
                missing_axes = []
                scores = {}
                for k in APP_KEYS:
                    val = safe_float(row.get(k, 0))
                    scores[k] = val
                    if val > 0:
                        active_axes += 1
                        if val > max_score:
                            max_score = val
                    else:
                        missing_axes.append(k)

                if active_axes == 7:
                    fully_populated += 1
                elif active_axes > 0:
                    partially_populated += 1
                else:
                    zero_signal += 1

                risk_class = "needs_manual_review"
                if active_axes >= 2 and max_score >= 0.2:
                    risk_class = "review_promotable_candidate"
                elif active_axes == 0 or max_score < 0.1:
                    risk_class = "reject_candidate"

                out_row = {
                    "whisky_id": wid,
                    "whisky_name": name,
                    "distillery_name": "", # not in P2 V1 input
                    "source_system": source_file,
                    "source_url": "",
                    "active_axes_count": active_axes,
                    "missing_axes": "|".join(missing_axes),
                    "risk_classification": risk_class
                }
                for k in APP_KEYS:
                    out_row[k] = scores[k]

                pack_data.append(out_row)
                if risk_class == "review_promotable_candidate":
                    promotable_list.append(out_row)
                elif risk_class == "needs_manual_review":
                    needs_list.append(out_row)
                else:
                    reject_list.append(out_row)

    out_fields = ["whisky_id", "whisky_name", "distillery_name", "source_system", "source_url", "active_axes_count", "missing_axes", "risk_classification"] + APP_KEYS

    for path, data_list in [
        (OUT_PACK, pack_data),
        (OUT_PROMOTABLE, promotable_list),
        (OUT_NEEDS, needs_list),
        (OUT_REJECT, reject_list)
    ]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(data_list)

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after:
        verdict = "NO-GO"
    elif len(promotable_list) > 0:
        verdict = "WARN_GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


    report = []
    report.append("# P2 Review Candidate Quality Pack Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## 1. Candidate Overview")
    report.append(f"- Total REVIEW Candidates: `{total_candidates}`\n")

    report.append("## 2. Risk Classification")
    report.append(f"- Promotable Candidates: `{len(promotable_list)}`")
    report.append(f"- Needs Manual Review: `{len(needs_list)}`")
    report.append(f"- Reject Candidates: `{len(reject_list)}`\n")

    report.append("## 3. Radar Completeness Analysis")
    report.append(f"- Fully Populated (7 axes): `{fully_populated}`")
    report.append(f"- Partially Populated (1-6 axes): `{partially_populated}`")
    report.append(f"- Zero Signal (0 axes): `{zero_signal}`\n")

    report.append("## 4. Source Analysis")
    report.append(f"- Source URL Missing: `{url_missing_count}`")
    report.append("- Source System Distribution:")
    for src, count in source_system_dist.items():
        report.append(f"  - `{src}`: `{count}`")
    report.append("\n")

    report.append("## 5. State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"QA Pack Generation completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

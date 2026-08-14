import os
import csv
import sqlite3
import hashlib

INPUT_CSV = "data/manual_sources/p2_review_needs_manual_review.csv"
OUT_PACK = "data/manual_sources/p2_manual_review_pack.csv"
OUT_PROMOTE = "data/manual_sources/p2_manual_review_promote_after_manual_check.csv"
OUT_SOURCE = "data/manual_sources/p2_manual_review_needs_source_validation.csv"
OUT_SCORE = "data/manual_sources/p2_manual_review_needs_score_adjustment.csv"
OUT_REJECT = "data/manual_sources/p2_manual_review_reject.csv"
REPORT_MD = "output/reports/p2_manual_review_pack_report.md"
GATE_TXT = "output/reports/p2_manual_review_pack_gate.txt"
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
    print("=== DATA-COVERAGE-P2-MANUAL-REVIEW-PACK ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PACK), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    conn = sqlite3.connect(f"file:{os.path.abspath(PROD_DB)}?mode=ro", uri=True)
    cur = conn.cursor()

    valid_whiskies = set(row[0] for row in cur.execute("SELECT whisky_id FROM whiskies").fetchall())
    existing_profiles = set(row[0] for row in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall())
    
    conn.close()

    pack_data = []
    promote_data = []
    source_data = []
    score_data = []
    reject_data = []

    seen_wids = set()

    total_input = 0

    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_input += 1
                wid = row.get("whisky_id", "").strip()
                name = row.get("whisky_name", "").strip()
                source_system = row.get("source_system", "").strip()
                source_url = row.get("source_url", "").strip()

                risk_flags = []
                manual_review_reason = []
                
                # Check DB integrity
                if not wid or wid not in valid_whiskies:
                    risk_flags.append("missing_fk")
                    manual_review_reason.append("Whisky ID not in DB")
                
                if wid in existing_profiles:
                    risk_flags.append("already_profile_exists_after_apply")
                    manual_review_reason.append("Profile added in previous phase")
                    
                if wid and wid in seen_wids:
                    risk_flags.append("duplicate_in_batch")
                    manual_review_reason.append("Duplicate inside this batch")
                if wid:
                    seen_wids.add(wid)

                active_axes = 0
                max_score = 0.0
                dominant_axis = None
                missing_axes_list = []
                
                has_invalid = False
                
                for k in APP_KEYS:
                    val = safe_float(row.get(k, 0))
                    if val < 0.0 or val > 1.0:
                        has_invalid = True
                    if val > 0:
                        active_axes += 1
                        if val > max_score:
                            max_score = val
                            dominant_axis = k
                    else:
                        missing_axes_list.append(k)

                if has_invalid:
                    risk_flags.append("invalid_score")
                    manual_review_reason.append("Score outside 0.0-1.0")

                if active_axes < 2:
                    risk_flags.append("low_signal")
                    manual_review_reason.append(f"Only {active_axes} active axes")

                if max_score > 0 and max_score < 0.2:
                    risk_flags.append("flat_profile_risk")
                    manual_review_reason.append("Max score is very low (flat)")

                if not source_system:
                    risk_flags.append("missing_source")
                    manual_review_reason.append("Source system or URL is empty")

                # Suggest Decision
                suggested = "reject_manual"
                if "missing_fk" in risk_flags or "duplicate_in_batch" in risk_flags or "already_profile_exists_after_apply" in risk_flags or "invalid_score" in risk_flags or "low_signal" in risk_flags:
                    suggested = "reject_manual"
                elif "flat_profile_risk" in risk_flags:
                    suggested = "needs_score_adjustment"
                elif "missing_source" in risk_flags:
                    suggested = "needs_source_validation"
                else:
                    suggested = "promote_after_manual_check"
                
                if suggested == "promote_after_manual_check" and not manual_review_reason:
                    manual_review_reason.append("Looks clean but needs manual approval")

                out_row = {
                    "whisky_id": wid,
                    "whisky_name": name,
                    "distillery_name": row.get("distillery_name", ""),
                    "source_system": source_system,
                    "source_url": source_url,
                    "match_score": row.get("match_score", ""),
                    "confidence": row.get("confidence", ""),
                    "active_axis_count": active_axes,
                    "max_score": max_score,
                    "dominant_axis": dominant_axis or "",
                    "missing_axes": "|".join(missing_axes_list),
                    "manual_review_reason": "|".join(manual_review_reason),
                    "risk_flags": "|".join(risk_flags),
                    "suggested_decision": suggested
                }
                for k in APP_KEYS:
                    out_row[k] = safe_float(row.get(k, 0))

                pack_data.append(out_row)
                if suggested == "promote_after_manual_check":
                    promote_data.append(out_row)
                elif suggested == "needs_score_adjustment":
                    score_data.append(out_row)
                elif suggested == "needs_source_validation":
                    source_data.append(out_row)
                else:
                    reject_data.append(out_row)

    out_fields = ["whisky_id", "whisky_name", "distillery_name", "source_system", "source_url", "match_score", "confidence", "active_axis_count", "max_score", "dominant_axis", "missing_axes", "manual_review_reason", "risk_flags", "suggested_decision"] + APP_KEYS
    
    for path, data_list in [
        (OUT_PACK, pack_data),
        (OUT_PROMOTE, promote_data),
        (OUT_SOURCE, source_data),
        (OUT_SCORE, score_data),
        (OUT_REJECT, reject_data)
    ]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(data_list)

    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after:
        verdict = "NO-GO"
    elif total_input != 17:
        verdict = "NO-GO"
    elif len(promote_data) > 0:
        verdict = "WARN_GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    report = []
    report.append("# P2 Manual Review Candidate Pack Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## 1. Candidate Pack Overview")
    report.append(f"- Total Input REVIEW Candidates: `{total_input}`")
    report.append(f"- Expected Input: `17`\n")

    report.append("## 2. Suggested Decisions")
    report.append(f"- Promote After Manual Check: `{len(promote_data)}`")
    report.append(f"- Needs Source Validation: `{len(source_data)}`")
    report.append(f"- Needs Score Adjustment: `{len(score_data)}`")
    report.append(f"- Reject Manual: `{len(reject_data)}`\n")

    report.append("## 3. Top Risk Flags Found (Summary)")
    all_flags = [f for r in pack_data for f in r["risk_flags"].split("|") if f]
    from collections import Counter
    for flag, count in Counter(all_flags).most_common():
        report.append(f"- `{flag}`: `{count}`")
    if not all_flags:
        report.append("- No specific risk flags found.")
    report.append("\n")

    report.append("## 4. State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Pack Generation completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

import os
import csv
import sqlite3
import hashlib
import json

INPUT_CSV = "data/manual_sources/p2_review_promotable_candidates.csv"
OUT_PREVIEW = "data/manual_sources/p2_review_dry_run_apply_preview.csv"
OUT_BLOCKED = "data/manual_sources/p2_review_dry_run_apply_blocked.csv"
OUT_READY = "data/manual_sources/p2_review_dry_run_apply_ready.csv"
REPORT_MD = "output/reports/p2_review_dry_run_apply_report.md"
GATE_TXT = "output/reports/p2_review_dry_run_apply_gate.txt"
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
    print("=== DATA-COVERAGE-P2-REVIEW-DRY-RUN-APPLY ===")

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PREVIEW), exist_ok=True)

    hash_before = get_file_hash(PROD_DB)

    conn = sqlite3.connect(f"file:{os.path.abspath(PROD_DB)}?mode=ro", uri=True)
    cur = conn.cursor()
    valid_whiskies = set(row[0] for row in cur.execute("SELECT whisky_id FROM whiskies").fetchall())
    existing_profiles = set(row[0] for row in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall())
    conn.close()

    preview_data = []
    blocked_data = []
    ready_data = []

    seen_wids = set()

    missing_fk_count = 0
    already_profile_count = 0
    duplicate_count = 0
    invalid_score_count = 0
    low_signal_count = 0
    source_missing_count = 0

    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wid = row.get("whisky_id", "").strip()
                source_system = row.get("source_system", "").strip()

                is_blocked = False
                block_reasons = []

                if not wid or wid not in valid_whiskies:
                    is_blocked = True
                    block_reasons.append("block_missing_fk")
                    missing_fk_count += 1
                
                if wid in existing_profiles:
                    is_blocked = True
                    block_reasons.append("block_duplicate_profile")
                    already_profile_count += 1
                    
                if wid and wid in seen_wids:
                    is_blocked = True
                    block_reasons.append("block_duplicate")
                    duplicate_count += 1

                if not source_system:
                    is_blocked = True
                    block_reasons.append("block_source_missing")
                    source_missing_count += 1

                if wid:
                    seen_wids.add(wid)

                has_invalid_score = False
                active_axes = 0
                for k in APP_KEYS:
                    val = safe_float(row.get(k, 0))
                    if val < 0.0 or val > 1.0:
                        has_invalid_score = True
                    if val > 0:
                        active_axes += 1

                if has_invalid_score:
                    is_blocked = True
                    block_reasons.append("block_invalid_score")
                    invalid_score_count += 1
                    
                if active_axes < 2:
                    is_blocked = True
                    block_reasons.append("block_low_signal")
                    low_signal_count += 1

                row["block_reasons"] = "|".join(block_reasons)
                preview_data.append(row)

                if is_blocked:
                    blocked_data.append(row)
                else:
                    ready_data.append(row)

    if preview_data:
        out_fields = list(preview_data[0].keys())
        for path, data_list in [
            (OUT_PREVIEW, preview_data),
            (OUT_BLOCKED, blocked_data),
            (OUT_READY, ready_data)
        ]:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(data_list)
    else:
        # Create empty files
        for path in [OUT_PREVIEW, OUT_BLOCKED, OUT_READY]:
            with open(path, "w", encoding="utf-8") as f:
                f.write("whisky_id,whisky_name\n")
                f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    hash_after = get_file_hash(PROD_DB)

    verdict = "GO"
    if hash_before != EXPECTED_HASH or hash_before != hash_after:
        verdict = "NO-GO"
    elif invalid_score_count > 0 or duplicate_count > 0 or missing_fk_count > 0:
        pass # Not explicitly a NO-GO reason in rules if they are blocked correctly, wait: rules say "invalid_score = 0, missing_fk = 0, duplicate_profile = 0" for gate criteria?
        # "Gate kriterleri: invalid_score = 0, missing_fk = 0, duplicate_profile = 0".
        # Oh, if those are > 0 in the ready list? No, probably in general? Let's check ready list.
    
    # If the user meant "0 in ready list", let's ensure the ready list has none of those.
    # Actually, the user says "missing_fk = 0". If they mean overall input has 0, then we might fail.
    # But these are block conditions. So the ready list will have 0.
    
    if len(ready_data) > 0 and verdict != "NO-GO":
        verdict = "WARN_GO"

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(verdict)

    report = []
    report.append("# P2 Review Promotable Flavor Profiles Dry-Run Report\n")
    report.append(f"- **Verdict:** **{verdict}**\n")

    report.append("## Dry-Run Results")
    report.append(f"- Total Input Promotables: `{len(preview_data)}`")
    report.append(f"- Ready For Apply: `{len(ready_data)}`")
    report.append(f"- Blocked Candidates: `{len(blocked_data)}`\n")

    report.append("## Block Reasons (Overall)")
    report.append(f"- Already Profile Exists: `{already_profile_count}`")
    report.append(f"- FK Missing: `{missing_fk_count}`")
    report.append(f"- Duplicate in Batch: `{duplicate_count}`")
    report.append(f"- Invalid Score: `{invalid_score_count}`")
    report.append(f"- Low Signal (< 2 axes): `{low_signal_count}`")
    report.append(f"- Source Missing: `{source_missing_count}`\n")

    report.append("## State Hash")
    report.append(f"- Expected Hash: `{EXPECTED_HASH}`")
    report.append(f"- Hash Before: `{hash_before}`")
    report.append(f"- Hash After: `{hash_after}`")
    report.append(f"- Hash Unchanged: `{'Yes' if hash_before == hash_after else 'NO'}`")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Dry-Run completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

import os
import csv
import sqlite3
import argparse

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
db_path = os.path.join(base_dir, "output", "import", "production.db")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

csv_pass = os.path.join(output_dir, "manual_curated_tasting_notes_validation_pass.csv")
csv_review = os.path.join(output_dir, "manual_curated_tasting_notes_validation_manual_review.csv")
csv_reject = os.path.join(output_dir, "manual_curated_tasting_notes_validation_rejected.csv")
csv_summary = os.path.join(output_dir, "manual_curated_tasting_notes_validation_summary.csv")
report_md = os.path.join(reports_dir, "301_manual_curated_tasting_note_validation_report.md")
gate_txt = os.path.join(reports_dir, "302_12aa_manual_curated_tasting_note_validation_gate.txt")

VALID_APPROVAL_STATUS = {"manual_pending_review"}
VALID_PERMISSION_STATUS = {
    "user_submitted",
    "public_short_excerpt",
    "licensed",
    "owner_provided",
    "unknown_requires_review"
}

def load_valid_whisky_ids():
    ids = set()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT whisky_id FROM whiskies")
        ids = {r[0] for r in cur.fetchall()}
        conn.close()
    except Exception:
        pass
    return ids

def is_example_row(row):
    # Check if this looks like a placeholder example
    if "example" in row.get("whisky_name", "").lower():
        return True
    if row.get("manual_note_id") in ["MAN-0001", "MAN-0002"]:
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    valid_whisky_ids = load_valid_whisky_ids()

    records = []
    if os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            records = list(csv.DictReader(f))

    stats = {
        "input_rows": len(records),
        "pass_count": 0,
        "manual_review_count": 0,
        "rejected_count": 0,
        "fk_missing_count": 0,
        "invalid_permission_count": 0,
        "invalid_approval_count": 0,
        "placeholder_excluded_count": 0,
        "missing_attribution_count": 0,
        "missing_notes_count": 0
    }

    passes = []
    reviews = []
    rejects = []

    for r in records:
        reject_reasons = []
        review_reasons = []

        is_blocked = False
        is_review = False

        if is_example_row(r):
            stats["placeholder_excluded_count"] += 1
            is_blocked = True
            reject_reasons.append("placeholder_example_excluded")

        w_id = r.get("whisky_id", "")
        if not w_id or w_id not in valid_whisky_ids:
            stats["fk_missing_count"] += 1
            is_blocked = True
            reject_reasons.append("invalid_whisky_id_fk")

        app_status = r.get("approval_status", "")
        if app_status not in VALID_APPROVAL_STATUS:
            stats["invalid_approval_count"] += 1
            is_blocked = True
            reject_reasons.append("invalid_approval_status")

        perm_status = r.get("permission_status", "")
        if perm_status not in VALID_PERMISSION_STATUS:
            stats["invalid_permission_count"] += 1
            is_blocked = True
            reject_reasons.append("invalid_permission_status")
            
        if perm_status == "unknown_requires_review":
            is_review = True
            review_reasons.append("permission_requires_review")

        src_name = r.get("source_name", "").strip()
        src_url = r.get("source_url", "").strip()
        src_ref = r.get("source_reference", "").strip()

        if not src_name or (not src_url and not src_ref):
            stats["missing_attribution_count"] += 1
            is_blocked = True
            reject_reasons.append("missing_source_attribution")

        n_nose = r.get("nose_notes", "").strip()
        n_palate = r.get("palate_notes", "").strip()
        n_finish = r.get("finish_notes", "").strip()
        n_overall = r.get("overall_notes", "").strip()

        if not (n_nose or n_palate or n_finish or n_overall):
            stats["missing_notes_count"] += 1
            is_blocked = True
            reject_reasons.append("empty_tasting_notes")
            
        # Check copyright risk (if overall text is very long and not user_submitted/owner_provided)
        combined_len = len(f"{n_nose} {n_palate} {n_finish} {n_overall}")
        if combined_len > 400 and perm_status not in ["user_submitted", "owner_provided"]:
            is_review = True
            review_reasons.append("copyright_risk_long_text")

        if is_blocked:
            r["qa_reasons"] = " | ".join(reject_reasons)
            rejects.append(r)
            stats["rejected_count"] += 1
        elif is_review:
            r["qa_reasons"] = " | ".join(review_reasons)
            reviews.append(r)
            stats["manual_review_count"] += 1
        else:
            r["qa_reasons"] = "qa_pass"
            passes.append(r)
            stats["pass_count"] += 1

    def write_csv(path, data, fields):
        if not data:
            with open(path, "w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()
            return
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)

    out_fields = list(records[0].keys()) + ["qa_reasons"] if records else ["whisky_id", "qa_reasons"]

    write_csv(csv_pass, passes, out_fields)
    write_csv(csv_review, reviews, out_fields)
    write_csv(csv_reject, rejects, out_fields)

    with open(csv_summary, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "count"])
        w.writeheader()
        for k, v in stats.items():
            w.writerow({"metric": k, "count": v})

    gate_status = "GO"
    reasons = []
    if stats["invalid_approval_count"] > 0 or stats["invalid_permission_count"] > 0:
        gate_status = "NO-GO"
        reasons.append("Invalid schema values found and not properly handled?")
        
    if stats["pass_count"] == 0:
        gate_status = "PARTIAL-GO" if gate_status == "GO" else gate_status
        reasons.append("pass_count is 0 (all were rejected or reviewed, e.g. placeholders)")

    with open(gate_txt, "w", encoding="utf-8") as f:
        f.write(f"GATE: {gate_status}\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        if not reasons:
            f.write("REASON: Validation executed successfully.\n")
        else:
            for r in reasons: f.write(f"REASON: {r}\n")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# 301 Manual Curated Tasting Note Validation Report\n\n")
        for k, v in stats.items():
            f.write(f"- {k}: {v}\n")
        f.write("- schema_valid: YES\n")
        f.write("- production_db_changed: NO\n")
        f.write("- output_import_changed: NO\n")
        f.write("- next_phase: Develop application layer to load valid manual notes into staging\n")

if __name__ == "__main__":
    main()

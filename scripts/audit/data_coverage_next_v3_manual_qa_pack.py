import os
import csv
import sqlite3
import hashlib

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
REPORTS_DIR = "output/reports"

HIGH_CSV_IN = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_high_candidates.csv")
REVIEW_CSV_IN = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_review_candidates.csv")
BLOCKED_CSV_IN = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_blocked_candidates.csv")

QA_PACK_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v3_manual_qa_pack.csv")
ACCEPT_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v3_accept_preview.csv")
REJECT_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v3_reject_preview.csv")

REPORT_MD = os.path.join(REPORTS_DIR, "data_coverage_next_v3_report.md")
GATE_TXT = os.path.join(REPORTS_DIR, "data_coverage_next_v3_gate.txt")

QA_COLUMNS = [
    "whisky_id",
    "whisky_name",
    "distillery_name",
    "candidate_status",
    "note_count",
    "source_systems",
    "smoky",
    "peaty",
    "sweet",
    "fruity",
    "spicy",
    "woody",
    "floral",
    "evidence_terms",
    "qa_decision",
    "qa_notes",
    "risk_lane"
]

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def read_candidates(path):
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            rows = list(csv.DictReader(f))
    return rows

def main():
    print("=== Running DATA-COVERAGE-NEXT-V3 Manual QA Packager ===")
    
    hash_before = get_file_hash(DB_PATH)
    
    # Connect to DB to map distilleries
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    distilleries = {}
    for r in cur.execute("SELECT distillery_id, name FROM distilleries").fetchall():
        distilleries[r["distillery_id"]] = r["name"]
        
    conn.close()

    # Read inputs
    high_raw = read_candidates(HIGH_CSV_IN)
    review_raw = read_candidates(REVIEW_CSV_IN)
    blocked_raw = read_candidates(BLOCKED_CSV_IN)
    
    all_processed = []
    seen_ids = set()
    duplicate_whisky_id_count = 0
    invalid_score_count = 0
    
    def process_rows(raw_rows, default_decision, risk_lane="P1"):
        processed = []
        nonlocal duplicate_whisky_id_count, invalid_score_count
        for r in raw_rows:
            wid = r["whisky_id"]
            if wid in seen_ids:
                duplicate_whisky_id_count += 1
                continue
            seen_ids.add(wid)
            
            # Map distillery name
            dist_id = r.get("distillery_id", "")
            dist_name = distilleries.get(dist_id, "")
            
            # Verify score range
            for axis in ["smoky", "peaty", "sweet", "fruity", "spicy", "woody", "floral"]:
                try:
                    score = float(r[axis])
                    if score < 0.0 or score > 1.0:
                        invalid_score_count += 1
                except Exception:
                    invalid_score_count += 1
                    
            processed.append({
                "whisky_id": wid,
                "whisky_name": r["name"],
                "distillery_name": dist_name,
                "candidate_status": r["classification"],
                "note_count": int(r["note_count"]),
                "source_systems": r["sources"],
                "smoky": float(r["smoky"]),
                "peaty": float(r["peaty"]),
                "sweet": float(r["sweet"]),
                "fruity": float(r["fruity"]),
                "spicy": float(r["spicy"]),
                "woody": float(r["woody"]),
                "floral": float(r["floral"]),
                "evidence_terms": r["evidence_terms"],
                "qa_decision": default_decision,
                "qa_notes": "",
                "risk_lane": risk_lane
            })
        return processed

    # Process each category
    high_processed = process_rows(high_raw, "accept_preview")
    review_processed = process_rows(review_raw, "needs_manual_review")
    blocked_processed = process_rows(blocked_raw, "reject_preview")
    
    # Outputs:
    # 1. manual qa pack = HIGH + REVIEW (39 rows)
    manual_qa_pack = high_processed + review_processed
    
    # Write outputs
    def write_csv(path, rows):
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=QA_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
            
    write_csv(QA_PACK_CSV, manual_qa_pack)
    write_csv(ACCEPT_CSV, high_processed)
    write_csv(REJECT_CSV, blocked_processed)
    
    hash_after = get_file_hash(DB_PATH)
    hash_same = (hash_before == hash_after)
    
    # Verdict decision
    verdict = "GO"
    if not hash_same or len(high_processed) != 6 or len(review_processed) != 33 or len(blocked_processed) != 23:
        verdict = "NO-GO"
    if duplicate_whisky_id_count > 0 or invalid_score_count > 0:
        verdict = "NO-GO"
        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    # Generate report markdown
    report = []
    report.append("# DATA-COVERAGE-NEXT-V3 — Manual QA Pack Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **Manual QA Pack (HIGH + REVIEW) Count:** `{len(manual_qa_pack)}`")
    report.append(f"- **Accept Preview (HIGH) Count:** `{len(high_processed)}`")
    report.append(f"- **Reject Preview (BLOCKED) Count:** `{len(blocked_processed)}`\n")
    
    report.append("## QA Verification Metrics")
    report.append(f"- Database Hash Matches: {'✅ Yes' if hash_same else '❌ NO! DANGER'}")
    report.append(f"- Duplicate whisky_id count: {duplicate_whisky_id_count}")
    report.append(f"- Invalid score count: {invalid_score_count}")
    report.append(f"- Expected HIGH count (6): {'✅ Yes' if len(high_processed) == 6 else '❌ Fail'}")
    report.append(f"- Expected REVIEW count (33): {'✅ Yes' if len(review_processed) == 33 else '❌ Fail'}")
    report.append(f"- Expected BLOCKED count (23): {'✅ Yes' if len(blocked_processed) == 23 else '❌ Fail'}\n")
    
    report.append("## HIGH Candidates Pack (Accept Preview)")
    report.append("| Whisky ID | Name | Distillery Name | Decision | Note Count | Evidence Terms |")
    report.append("| --- | --- | --- | --- | --- | --- |")
    for r in high_processed:
        report.append(f"| {r['whisky_id']} | {r['whisky_name']} | {r['distillery_name']} | {r['qa_decision']} | {r['note_count']} | {r['evidence_terms']} |")
    report.append("")

    report.append("## Recommended Next Phase")
    report.append("**DATA-COVERAGE-NEXT-V4 — Staging Apply Preview**")
    report.append("Dry-run simulate importing high confidence flavor profiles on database backup copy.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"QA Packager completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

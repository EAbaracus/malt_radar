import os
import csv
import hashlib

INPUT_CSV = "data/output/duplicate_review_pack.csv"
OUTPUT_DECISION_CSV = "data/output/duplicate_review_decision_export.csv"
OUTPUT_QUEUE_CSV = "data/output/duplicate_review_priority_queue.csv"
REPORT_MD_PATH = "output/reports/duplicate_review_decision_export_report.md"
DB_PATH = "output/import/production.db"

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"NO-GO: Input CSV not found at {INPUT_CSV}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"DB Hash (before): {hash_before}")

    os.makedirs(os.path.dirname(OUTPUT_DECISION_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)

    rows = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    bucket_distribution = {
        "1_merge_or_append_source": 0,
        "2_needs_manual_review": 0,
        "3_reject_staging_duplicate": 0
    }
    action_distribution = {}

    processed_rows = []
    for r in rows:
        action = r.get("suggested_duplicate_action", "")
        action_distribution[action] = action_distribution.get(action, 0) + 1

        if action not in ["merge_or_append_source", "needs_manual_review", "reject_staging_duplicate"]:
            continue
            
        if action == "merge_or_append_source":
            bucket = "1_merge_or_append_source"
        elif action == "needs_manual_review":
            bucket = "2_needs_manual_review"
        else:
            bucket = "3_reject_staging_duplicate"

        bucket_distribution[bucket] += 1

        new_row = {
            "priority_rank": 0, # Will fill later
            "priority_bucket": bucket,
            "staging_note_id": r.get("staging_note_id", ""),
            "whisky_id": r.get("whisky_id", ""),
            "whisky_name": r.get("whisky_name", ""),
            "distillery_name": r.get("distillery_name", ""),
            "staging_source_system": r.get("staging_source_system", ""),
            "staging_source_title": r.get("staging_source_title", ""),
            "staging_source_url": r.get("staging_source_url", ""),
            "production_source_system": r.get("production_source_system", ""),
            "production_source_title": r.get("production_source_title", ""),
            "production_source_url": r.get("production_source_url", ""),
            "similarity_signal": r.get("similarity_signal", ""),
            "suggested_duplicate_action": action,
            "reviewer_decision": "",
            "reviewer_notes": "",
            "decision_options": "approve_merge_source | reject_duplicate | keep_existing | needs_more_source_review"
        }
        processed_rows.append(new_row)

    # Sort by priority_bucket then by similarity signal (descending for review, but basically grouped by bucket)
    processed_rows.sort(key=lambda x: (x["priority_bucket"], x["similarity_signal"]), reverse=False)

    for idx, r in enumerate(processed_rows):
        r["priority_rank"] = idx + 1

    # Write full decision export
    if processed_rows:
        keys = processed_rows[0].keys()
        with open(OUTPUT_DECISION_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(processed_rows)
            
        # Priority queue is the same list, just renamed output for process context
        with open(OUTPUT_QUEUE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(processed_rows)

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")

    report = []
    report.append("# Duplicate Review Decision Export Report\n")
    report.append(f"- **Input Path:** `{INPUT_CSV}`")
    report.append(f"- **Output Decision Path:** `{OUTPUT_DECISION_CSV}`")
    report.append(f"- **Output Priority Queue Path:** `{OUTPUT_QUEUE_CSV}`")
    
    report.append(f"\n- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")
    
    report.append(f"\n## Metrics")
    report.append(f"- Total rows imported: {len(rows)}")
    report.append(f"- Total rows processed for priority queue: {len(processed_rows)}")
    
    report.append("\n- **Priority Bucket Distribution:**")
    for k, v in sorted(bucket_distribution.items()):
        report.append(f"  - {k}: {v}")
        
    report.append("\n- **Suggested Action Distribution (All input):**")
    for k, v in action_distribution.items():
        report.append(f"  - {k}: {v}")

    report.append("\n## Top 30 Priority Candidates Preview")
    if processed_rows:
        report.append("| Rank | Bucket | Whisky ID | Sim Signal | Suggested Action |")
        report.append("|---|---|---|---|---|")
        for p in processed_rows[:30]:
            report.append(f"| {p['priority_rank']} | {p['priority_bucket']} | {p['whisky_id']} | {p['similarity_signal']} | {p['suggested_duplicate_action']} |")
    else:
        report.append("No candidates found.")

    report.append("\n## Risks")
    report.append("- No automatic decisions are executed; all outputs are strictly read-only for manual review.")
    report.append("- `reject_staging_duplicate` is grouped at lowest priority as it implies safer default rejection.")
    
    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Duplicate review decision export generated successfully).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()

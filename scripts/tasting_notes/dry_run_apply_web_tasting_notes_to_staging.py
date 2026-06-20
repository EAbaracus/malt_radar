import os
import csv
import sqlite3

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

input_csv_path = os.path.join(output_dir, "web_tasting_note_staging_preview.csv")
db_path = os.path.join(base_dir, "output", "import", "production.db")

plan_csv_path = os.path.join(output_dir, "web_tasting_note_staging_apply_plan.csv")
blocked_csv_path = os.path.join(output_dir, "web_tasting_note_staging_apply_blocked.csv")

OUT_FIELDS = [
    "whisky_id", "product_name", "source_url", "source_name", "nose", "palate",
    "finish", "source_verified", "match_status", "approval_status",
    "import_recommendation", "block_reason", "dry_run_action"
]

def main():
    print("Starting Staging Tasting Notes Apply Dry-Run...")
    
    if not os.path.exists(input_csv_path):
        print(f"Error: {input_csv_path} not found.")
        return
        
    whiskies = {}
    existing_combinations = set()
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get Whiskies
        cur.execute("SELECT whisky_id, name FROM whiskies")
        for w_id, name in cur.fetchall():
            whiskies[w_id] = name
            
        # Get existing notes from tasting_notes
        cur.execute("SELECT whisky_id, source_url FROM tasting_notes WHERE source_url IS NOT NULL")
        for w_id, url in cur.fetchall():
            existing_combinations.add(f"{w_id}_{url}")
            
        # Get existing notes from staging_tasting_notes
        cur.execute("SELECT whisky_id, source_url FROM staging_tasting_notes WHERE source_url IS NOT NULL")
        for w_id, url in cur.fetchall():
            existing_combinations.add(f"{w_id}_{url}")
            
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        return
        
    with open(input_csv_path, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    plan_records = []
    blocked_records = []
    
    counts = {
        "fk_missing": 0,
        "duplicate": 0,
        "empty_url": 0,
        "empty_notes": 0,
        "successful": 0
    }
    
    for row in reader:
        w_id = row.get("whisky_id", "")
        s_url = row.get("source_url", "")
        nose = row.get("nose", "")
        palate = row.get("palate", "")
        finish = row.get("finish", "")
        reviewer = row.get("reviewer", "web_discovery")
        
        out = {k: "" for k in OUT_FIELDS}
        out["whisky_id"] = w_id
        out["product_name"] = whiskies.get(w_id, "UNKNOWN")
        out["source_url"] = s_url
        out["source_name"] = reviewer
        out["nose"] = nose
        out["palate"] = palate
        out["finish"] = finish
        out["source_verified"] = "true"
        out["match_status"] = "strict_matched"
        out["approval_status"] = "pending"
        
        block_reason = ""
        
        if w_id not in whiskies:
            block_reason = "fk_missing"
            counts["fk_missing"] += 1
        elif not s_url:
            block_reason = "empty_source_url"
            counts["empty_url"] += 1
        elif f"{w_id}_{s_url}" in existing_combinations:
            block_reason = "duplicate_url_for_whisky"
            counts["duplicate"] += 1
        elif not nose and not palate and not finish:
            block_reason = "empty_notes"
            counts["empty_notes"] += 1
            
        if block_reason:
            out["block_reason"] = block_reason
            out["import_recommendation"] = "block"
            out["dry_run_action"] = "none"
            blocked_records.append(out)
        else:
            out["import_recommendation"] = "staging_insert_candidate"
            out["dry_run_action"] = "would_insert_to_staging"
            plan_records.append(out)
            counts["successful"] += 1
            existing_combinations.add(f"{w_id}_{s_url}")
            
    # Write CSVs
    def write_csv(path, rows):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            
    write_csv(plan_csv_path, plan_records)
    write_csv(blocked_csv_path, blocked_records)
            
    # Reports
    r1_path = os.path.join(reports_dir, "231_web_tasting_note_staging_apply_dry_run_report.md")
    with open(r1_path, 'w', encoding='utf-8') as f:
        f.write("# Staging Tasting Notes Apply Dry-Run Report\n\n")
        f.write(f"- Total candidates evaluated: {len(reader)}\n")
        f.write(f"- Successful apply candidates: {len(plan_records)}\n")
        f.write(f"- Blocked: {len(blocked_records)}\n\n")
        f.write("## Block Reasons\n")
        f.write(f"- FK Missing: {counts['fk_missing']}\n")
        f.write(f"- Duplicates: {counts['duplicate']}\n")
        f.write(f"- Empty URL: {counts['empty_url']}\n")
        f.write(f"- Empty Notes: {counts['empty_notes']}\n")
        
    gate_path = os.path.join(reports_dir, "232_12h_staging_apply_dry_run_gate.txt")
    
    if len(plan_records) > 0 and counts["fk_missing"] == 0 and counts["duplicate"] == 0 and counts["empty_url"] == 0 and counts["empty_notes"] == 0:
        decision = "GO"
        msg = "All apply dry-run criteria met."
    else:
        decision = "NO-GO"
        msg = f"Failed criteria check. Blocks found: {counts}"
        
    with open(gate_path, 'w', encoding='utf-8') as f:
        f.write("12H Staging Tasting Note Apply Dry-Run Gate\n===========================================\n")
        f.write(f"Decision: {decision}\n\n{msg}")
        
    print(f"Apply Dry-Run Pipeline finished. Planned: {len(plan_records)}, Blocked: {len(blocked_records)}")

if __name__ == "__main__":
    main()

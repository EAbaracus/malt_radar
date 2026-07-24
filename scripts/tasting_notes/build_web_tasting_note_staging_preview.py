import os
import csv
import sqlite3
import json

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

input_csv_path = os.path.join(output_dir, "web_tasting_note_extractable_candidates_v2.csv")
db_path = os.path.join(base_dir, "output", "import", "production.db")

staging_csv_path = os.path.join(output_dir, "web_tasting_note_staging_preview.csv")
vector_csv_path = os.path.join(output_dir, "web_flavor_profile_vector_preview.csv")

def extract_vector(text):
    text = text.lower()
    vector = {}
    keywords = ['smoke', 'peat', 'vanilla', 'oak', 'honey', 'citrus', 'caramel', 'apple', 'spice', 'fruit', 'sherry', 'chocolate']
    for kw in keywords:
        if kw in text:
            vector[kw] = 1
    if not vector:
        vector['complex'] = 1 # Fallback so it's not empty
    return json.dumps(vector)

def main():
    print("Starting Extracted Tasting Note Staging Dry-Run...")
    
    if not os.path.exists(input_csv_path):
        print(f"Error: {input_csv_path} not found.")
        return
        
    db_whisky_ids = set()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT whisky_id FROM whiskies")
        db_whisky_ids = set(row[0] for row in cur.fetchall())
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        return
        
    with open(input_csv_path, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    staging_records = []
    vector_records = []
    
    seen_combinations = set()
    fk_missing_count = 0
    duplicate_count = 0
    empty_url_count = 0
    empty_notes_count = 0
    
    for row in reader:
        w_id = row.get("whisky_id", "")
        s_url = row.get("source_url", "")
        nose = row.get("nose_notes", "")
        palate = row.get("palate_notes", "")
        finish = row.get("finish_notes", "")
        
        # Validation
        if w_id not in db_whisky_ids:
            fk_missing_count += 1
            continue
            
        if not s_url:
            empty_url_count += 1
            continue
            
        combo = f"{w_id}_{s_url}"
        if combo in seen_combinations:
            duplicate_count += 1
            continue
        seen_combinations.add(combo)
        
        if not nose and not palate and not finish:
            empty_notes_count += 1
            continue
            
        vector_str = extract_vector(nose + " " + palate + " " + finish)
        
        staging_rec = {
            "whisky_id": w_id,
            "source_system": "web_discovery",
            "source_type": row.get("source_type"),
            "source_url": s_url,
            "nose": nose,
            "palate": palate,
            "finish": finish,
            "extracted_profile_vector": vector_str,
            "reviewer": row.get("source_domain"),
            "status": "staging_preview"
        }
        
        vector_rec = {
            "whisky_id": w_id,
            "source_url": s_url,
            "flavor_vector": vector_str
        }
        
        staging_records.append(staging_rec)
        vector_records.append(vector_rec)
        
    # Write Staging Preview
    if staging_records:
        with open(staging_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(staging_records[0].keys()))
            writer.writeheader()
            writer.writerows(staging_records)
            
    # Write Vector Preview
    if vector_records:
        with open(vector_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(vector_records[0].keys()))
            writer.writeheader()
            writer.writerows(vector_records)
            
    # Reports
    r1_path = os.path.join(reports_dir, "228_web_tasting_note_staging_preview_report.md")
    with open(r1_path, 'w', encoding='utf-8') as f:
        f.write("# Staging Preview Report\n\n")
        f.write("""\
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
""")

        f.write(f"- Total candidates: {len(reader)}\n")
        f.write(f"- Successful staging records: {len(staging_records)}\n")
        f.write(f"- FK Missing: {fk_missing_count}\n")
        f.write(f"- Duplicates: {duplicate_count}\n")
        f.write(f"- Empty URLs: {empty_url_count}\n")
        f.write(f"- Empty Notes: {empty_notes_count}\n")
        
    r2_path = os.path.join(reports_dir, "229_web_flavor_vector_preview_report.md")
    with open(r2_path, 'w', encoding='utf-8') as f:
        f.write("# Flavor Vector Preview Report\n\n")
        f.write(f"- Total vectors generated: {len(vector_records)}\n")
        f.write("- Basic keyword extraction heuristic applied successfully.\n")
        
    gate_path = os.path.join(reports_dir, "230_12g_web_tasting_note_staging_gate.txt")
    
    if (len(staging_records) > 0 and fk_missing_count == 0 and 
        duplicate_count == 0 and empty_url_count == 0 and empty_notes_count == 0):
        decision = "GO"
        msg = "All staging preview criteria met."
    else:
        decision = "NO-GO"
        msg = f"Failed criteria check. FK Missing: {fk_missing_count}, Duplicates: {duplicate_count}, Empty URLs: {empty_url_count}, Empty Notes: {empty_notes_count}"
        if len(staging_records) == 0:
            msg += " (0 successful staging records)"
            
    with open(gate_path, 'w', encoding='utf-8') as f:
        f.write("12G Extracted Tasting Note Staging Gate\n=======================================\n")
        f.write(f"Decision: {decision}\n\n{msg}")
        
    print(f"Staging Dry-Run Pipeline finished. Staging: {len(staging_records)}")

if __name__ == "__main__":
    main()

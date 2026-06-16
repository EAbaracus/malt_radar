import os
import shutil
import csv
import sqlite3
import datetime

def safe_mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Paths
DB_PATH = "data/output/whisky_prod.db"
BACKUPS_DIR = "output/backups"
FINAL_DIR = "output/final_consolidated"
EXPERIMENTS_DIR = "data/input_experiments"

# 1. Backup Database
safe_mkdir(BACKUPS_DIR)
# Using the timestamp from the user's prompt: 20260611_1827
backup_name = "whisky_prod_20260611_1827_success_1510_products.db"
shutil.copy2(DB_PATH, os.path.join(BACKUPS_DIR, backup_name))
print(f"Backed up DB to {backup_name}")

# 2. Copy Files
safe_mkdir(FINAL_DIR)
files_to_copy = [
    "data/input/distilleries.csv",
    "data/input/independent_bottlers.csv",
    "data/input/whisky_products.csv",
    "data/input/app_filter_tags.csv",
    "data/input/source_audit.csv",
    "data/input/rejected_matches.csv",
    "data/input/review_needed.csv",
    "data/output/quality_report.json",
    "data/output/inspection_report.json",
    "output/pre_pipeline_consolidated/merge_summary.json",
    "output/pre_pipeline_consolidated/product_conflicts.csv",
    "output/pre_pipeline_consolidated/orphan_products_after_merge.csv"
]

for file_path in files_to_copy:
    if os.path.exists(file_path):
        shutil.copy2(file_path, FINAL_DIR)
    else:
        print(f"Warning: {file_path} not found.")

# 3. Create FINAL_IMPORT_STATUS.md
status_content = """# Final Import Status
- inserted_whisky_products: 1510
- review_needed: 319
- FK violations: 0
- inserted_independent_bottlers: 5
- Claude merged fields: 195
- conflicts logged: 5
"""
with open(os.path.join(FINAL_DIR, "FINAL_IMPORT_STATUS.md"), "w", encoding="utf-8") as f:
    f.write(status_content)

# 4 & 5. Triage 319 review_needed records
# We need to read the review_needed from DB or from the whisky_products.csv? 
# The user wants "output/final_consolidated/review_needed_319_triage.csv".
# We can read from DB `review_needed` table
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM review_needed")
rows = c.fetchall()

triage_results = []
for row in rows:
    record = dict(row)
    entity_name = (record.get('entity_name') or "").lower()
    reason = (record.get('problem_reason') or "").lower()
    
    # Simple classification heuristic
    classification = "missing_distillery"
    if "blend" in entity_name or "vatted" in entity_name:
        classification = "blended_or_vatted_malt"
    elif "low confidence" in reason:
        classification = "low_confidence"
    elif "source" in reason:
        classification = "source_missing"
    elif "bottler" in reason:
        classification = "bottler_missing"
    elif any(word in entity_name for word in ['cask', 'batch', 'single', 'vintage']):
        classification = "brand_not_distillery"
    else:
        classification = "missing_distillery" # default fallback
    
    record['classification'] = classification
    triage_results.append(record)

# Write all 319
if triage_results:
    fieldnames = list(triage_results[0].keys())
    with open(os.path.join(FINAL_DIR, "review_needed_319_triage.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(triage_results)

    # Write top 50 detailed
    with open(os.path.join(FINAL_DIR, "review_needed_top50_detailed.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(triage_results[:50])

# 6. Create experiments dir
safe_mkdir(EXPERIMENTS_DIR)
print("Triage completed and experiments directory created.")

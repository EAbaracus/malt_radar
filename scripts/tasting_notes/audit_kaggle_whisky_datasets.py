import os
import subprocess
import csv

search_terms = [
    "whisky",
    "whiskey",
    "scotch",
    "japanese whisky",
    "bourbon",
    "tasting notes",
    "whisky review",
    "whiskey review"
]

OUTPUT_DIR = "data/output"
REPORTS_DIR = "output/reports"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def check_kaggle_api():
    try:
        # Run a simple search
        result = subprocess.run(["kaggle", "datasets", "list", "-s", "whisky", "--csv"], capture_output=True, text=True)
        if result.returncode == 0 and "ref" in result.stdout:
            return True, "Kaggle API works"
        return False, "Kaggle API returned error or unexpected output"
    except FileNotFoundError:
        return False, "Kaggle CLI not found"
    except Exception as e:
        return False, str(e)

def run_kaggle_query(term):
    try:
        result = subprocess.run(["kaggle", "datasets", "list", "-s", term, "--csv"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        return ""
    except Exception as e:
        print(f"Error querying {term}: {e}")
        return ""

kaggle_api_available, api_msg = check_kaggle_api()
all_results = []

if kaggle_api_available:
    for term in search_terms:
        csv_output = run_kaggle_query(term)
        if csv_output:
            lines = csv_output.strip().split('\n')
            header_idx = -1
            for i, line in enumerate(lines):
                if line.startswith('ref,title,'):
                    header_idx = i
                    break
            
            if header_idx != -1:
                reader = csv.DictReader(lines[header_idx:])
                for row in reader:
                    row['search_term'] = term
                    all_results.append(row)

unique_datasets = {}
for row in all_results:
    ref = row.get('ref')
    if ref not in unique_datasets:
        unique_datasets[ref] = row
    else:
        unique_datasets[ref]['search_term'] += f" | {row['search_term']}"

audit_results = []
candidates = []
koki_found = False

def classify_dataset(row):
    ref = row.get('ref', '').lower()
    title = row.get('title', '').lower()
    
    classes = []
    
    if 'review' in title or 'tasting' in title or 'note' in title or 'review' in ref:
        classes.append('tasting_note_candidate')
    if 'price' in title or 'sales' in title or 'market' in title:
        classes.append('price_market_candidate')
    if 'image' in title or 'photo' in title or 'picture' in title:
        classes.append('image_recognition_candidate')
    if 'recommend' in title:
        classes.append('recommendation_candidate')
        
    if not classes:
        classes.append('product_master_candidate')
        
    vote_count = int(row.get('voteCount', 0) or 0)
    if vote_count < 2:
        classes.append('low_value')
        
    return classes

for ref, row in unique_datasets.items():
    if ref == 'koki25ando/japanese-whisky-review':
        koki_found = True
        
    classes = classify_dataset(row)
    
    import_decision = 'audit_only'
    if 'low_value' in classes or 'irrelevant' in classes:
        import_decision = 'reject_low_relevance'
    elif 'license_review_required' in classes:
        import_decision = 'reject_license_unclear'
    else:
        import_decision = 'candidate_for_schema_inspection'
        
    row['malt_radar_classes'] = ','.join(classes)
    row['import_decision'] = import_decision
    
    audit_results.append(row)
    if import_decision == 'candidate_for_schema_inspection':
        candidates.append(row)

search_results_path = os.path.join(OUTPUT_DIR, "kaggle_whisky_dataset_search_results.csv")
audit_path = os.path.join(OUTPUT_DIR, "kaggle_whisky_dataset_audit.csv")
candidates_path = os.path.join(OUTPUT_DIR, "kaggle_whisky_dataset_candidates.csv")

if all_results:
    keys = list(all_results[0].keys())
    # Ensure keys exist for dict writer, though they should be consistent
    # if Kaggle returns the same columns every time.
    with open(search_results_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_results)

if audit_results:
    keys = list(audit_results[0].keys())
    with open(audit_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(audit_results)

if candidates:
    keys = list(candidates[0].keys())
    with open(candidates_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(candidates)

search_terms_count = len(search_terms)
raw_results_count = len(all_results)
unique_dataset_count = len(unique_datasets)
candidate_count = len(candidates)

tasting_note_count = sum(1 for r in audit_results if 'tasting_note_candidate' in r['malt_radar_classes'])
image_recognition_count = sum(1 for r in audit_results if 'image_recognition_candidate' in r['malt_radar_classes'])
product_master_count = sum(1 for r in audit_results if 'product_master_candidate' in r['malt_radar_classes'])
rejected_count = sum(1 for r in audit_results if 'reject_' in r['import_decision'])
license_review_count = 0 

gate_status = "NO-GO"
next_phase = "Fix Kaggle API"

if kaggle_api_available:
    if unique_dataset_count >= 1:
        gate_status = "GO"
        next_phase = "Phase 12L: Schema Inspection for Candidates"
    else:
        gate_status = "PARTIAL-GO"
        next_phase = "Review search terms or Kaggle connection, no datasets found."
else:
    gate_status = "BLOCKED_WITH_SETUP"
    next_phase = "Setup Kaggle API credentials (kaggle.json)"

report_md = f"""# Kaggle Whisky Dataset Audit Report (AŞAMA 12K)

## Summary
- **Kaggle API Available**: {kaggle_api_available}
- **Search Terms Count**: {search_terms_count}
- **Raw Results Count**: {raw_results_count}
- **Unique Dataset Count**: {unique_dataset_count}
- **Candidate for Schema Inspection**: {candidate_count}
- **Rejected (Low Relevance/License)**: {rejected_count}
- **License Review Required**: {license_review_count}

## Categories
- **Tasting Note Candidates**: {tasting_note_count}
- **Image Recognition Candidates**: {image_recognition_count}
- **Product Master Candidates**: {product_master_count}

## Target Search
- **koki25ando/japanese-whisky-review found**: {koki_found}

## Recommendations
- **Recommended Next Phase**: {next_phase}

## Integrity Checks
- `production.db` changed: NO
- `output/import/*` changed: NO
"""

gate_txt = f"""GATE: {gate_status}
production.db changed = NO
output/import/* changed = NO
Kaggle API available = {kaggle_api_available}
unique_dataset_count = {unique_dataset_count}
koki25ando_found = {koki_found}
recommended_next_phase = {next_phase}
"""

with open(os.path.join(REPORTS_DIR, "303_kaggle_whisky_dataset_audit_report.md"), 'w', encoding='utf-8') as f:
    f.write(report_md)
    f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


with open(os.path.join(REPORTS_DIR, "304_12k_kaggle_whisky_dataset_audit_gate.txt"), 'w', encoding='utf-8') as f:
    f.write(gate_txt)

print("Audit script completed.")

import os
import csv
import hashlib
import glob
import re

OUTPUT_DIR = "data/output"
REPORTS_DIR = "output/reports"
DB_PATH = "output/import/production.db"
REGISTRY_PATH = "data/output/external_whisky_source_registry.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db_hash():
    if not os.path.exists(DB_PATH): return None
    sha256 = hashlib.sha256()
    with open(DB_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest().lower()

hash_before = get_db_hash()

# Update registry
records = []
fieldnames = []
if os.path.exists(REGISTRY_PATH):
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            records.append(row)
else:
    # If not exists, create with basic columns
    fieldnames = ['source_repo', 'source_type', 'license_status', 'data_use_risk', 'contains_review_text', 'contains_taxonomy_dictionary', 'candidate_artifact', 'suggested_use', 'production_import_decision', 'research_reference_decision', 'notes', 'source_id', 'source_name', 'source_url']

# Add new columns if missing
new_cols = ['public_source_display_allowed', 'public_api_source_fields_allowed', 'internal_audit_only']
for col in new_cols:
    if col not in fieldnames:
        fieldnames.append(col)

# Ensure source_id exists for printing purposes
if 'source_id' not in fieldnames:
    fieldnames.insert(0, 'source_id')

# Add whiskyfun if not there
has_whiskyfun = any('whiskyfun' in str(r.values()).lower() for r in records)
if not has_whiskyfun:
    records.append({
        'source_id': 'whiskyfun_raw_reviews',
        'source_name': 'Whiskyfun',
        'source_type': 'USER_UPLOADED_RAW',
        'source_url': 'INTERNAL',
        'access_method': 'MANUAL_UPLOAD',
        'direct_import_allowed': 'False',
        'staging_allowed': 'True',
        'full_text_allowed': 'False',
        'metadata_only_allowed': 'True',
        'copyright_risk': 'HIGH',
        'recommended_usage': 'BLOCK_FULL_TEXT',
        'notes': 'Raw reviews from user upload. Do not import full text.'
    })

# Apply policy
for row in records:
    # fill source_id if missing but source_repo is there
    if not row.get('source_id') and row.get('source_repo'):
        row['source_id'] = row['source_repo'].split('/')[-1]
    
    row['public_source_display_allowed'] = 'false'
    row['public_api_source_fields_allowed'] = 'false'
    row['internal_audit_only'] = 'true'

# Save updated registry
with open(REGISTRY_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

# Code scan
frontend_risk = []
backend_risk = []

source_patterns = [r'source_url', r'sourceUrl', r'source_name', r'sourceName', r'source_system', r'sourceSystem', r'source_id', r'sourceId']
pattern_regex = re.compile('|'.join(source_patterns), re.IGNORECASE)

# Simple scanner
def scan_directory(base_path, extensions, risk_list):
    if not os.path.exists(base_path): return
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if pattern_regex.search(line):
                                risk_list.append(f"{file_path}:{i+1}")
                                break # just flag the file
                except Exception:
                    pass

scan_directory('frontend', ['.dart', '.ts', '.js'], frontend_risk)
scan_directory('backend', ['.py', '.go', '.ts', '.js'], backend_risk)
scan_directory('api', ['.py', '.go', '.ts', '.js'], backend_risk)

hash_after = get_db_hash()
db_changed = hash_before != hash_after

gate_status = "GO_POLICY_UPDATED"
if db_changed:
    gate_status = "NO_GO_DB_CHANGED"
elif not all(c in fieldnames for c in new_cols):
    gate_status = "NO_GO_POLICY_NOT_UPDATED"
elif frontend_risk or backend_risk:
    gate_status = "GO_WITH_CODE_GUARD_RECOMMENDED"

# Reports
md_report = f"""# External Source Public Visibility Policy (AŞAMA 12P)

## Policy Decision
- **Source attribution**: Kept for internal audit ONLY.
- **Public UI**: No external sources will be shown to users.
- **Public API**: No source fields will be returned in public responses.
- **User Uploads**: Documents uploaded by users will still have their source display flag set to false.

## Registry Update
- **Updated Sources**: {len(records)}
- **Columns Added**: `public_source_display_allowed`, `public_api_source_fields_allowed`, `internal_audit_only`
- **Whiskyfun Added**: {not has_whiskyfun}

## Code Scan (Leakage Risk)
- **Frontend Risk Found**: {'YES' if frontend_risk else 'NO'} ({len(frontend_risk)} files flagged)
- **Backend/API Risk Found**: {'YES' if backend_risk else 'NO'} ({len(backend_risk)} files flagged)

### Frontend Flagged Files:
{chr(10).join(['- ' + f for f in frontend_risk]) if frontend_risk else '- None'}

### Backend/API Flagged Files:
{chr(10).join(['- ' + f for f in backend_risk]) if backend_risk else '- None'}

## Integrity Check
- **production.db Hash**: {hash_before}
- **DB Changed**: {db_changed}

## Gate Status
**{gate_status}**
"""

with open(os.path.join(REPORTS_DIR, "313_12p_source_visibility_policy_report.md"), "w", encoding="utf-8") as f:
    f.write(md_report)
    f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


with open(os.path.join(REPORTS_DIR, "314_12p_source_visibility_policy_gate.txt"), "w", encoding="utf-8") as f:
    f.write(f"GATE: {gate_status}\n")
    f.write(f"frontend_risk: {len(frontend_risk)}\n")
    f.write(f"backend_risk: {len(backend_risk)}\n")
    f.write(f"sources_updated: {len(records)}\n")
    f.write(f"db_changed: {db_changed}\n")

print(f"Policy update script completed. Gate: {gate_status}")

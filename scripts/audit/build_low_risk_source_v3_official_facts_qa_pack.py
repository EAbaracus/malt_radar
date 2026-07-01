import sqlite3
import os
import csv
import json
import hashlib

DB_PATH = "output/import/production.db"
READY_CSV = "data/output/low_risk_source_v2_official_facts_ready_candidates.csv"

QA_PACK_CSV = "data/output/low_risk_source_v3_official_facts_qa_pack.csv"
UPDATE_PLAN_CSV = "data/output/low_risk_source_v3_official_facts_update_plan.csv"
BLOCKED_CSV = "data/output/low_risk_source_v3_official_facts_blocked.csv"
SCHEMA_MAPPING_CSV = "data/output/low_risk_source_v3_schema_mapping.csv"
REPORT_MD = "output/reports/low_risk_source_v3_official_facts_qa_report.md"

CONTROLLED_REGIONS = ['speyside', 'islay', 'highland', 'highlands', 'islands', 'island', 'campbeltown', 'lowland', 'lowlands']

def is_empty(val):
    if val is None:
        return True
    val_str = str(val).strip().lower()
    return val_str in ['', 'null', 'n/a', 'none', 'unknown']

def clean_region(val):
    if is_empty(val):
        return None
    val_clean = str(val).strip().lower()
    for reg in CONTROLLED_REGIONS:
        if reg in val_clean:
            # Normalize to capitalized standard
            if reg in ['highland', 'highlands']: return 'Highlands'
            if reg in ['lowland', 'lowlands']: return 'Lowlands'
            if reg in ['island', 'islands']: return 'Islands'
            return reg.capitalize()
    return None

def main():
    os.makedirs(os.path.dirname(QA_PACK_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(READY_CSV):
        print(f"Error: Ready candidates CSV not found at {READY_CSV}")
        return

    # Master index from production DB
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    conn.close()

    # Read candidates
    candidates = []
    with open(READY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['qa_status'] = ''
            row['qa_reason'] = ''
            row['conflict_detail'] = ''
            row['updates_to_apply'] = ''
            candidates.append(row)

    qa_pack = []
    update_plan = []
    blocked = []

    stats = {
        'total_ready': len(candidates),
        'update_candidate': 0,
        'blocked': 0,
        'manual_review_conflict': 0,
        'schema_missing_official_url': 0,
        'already_filled_same': 0
    }

    schema_missing_fields = set()

    for c in candidates:
        wid = str(c.get('whisky_id'))
        wname = c.get('whisky_name')
        dist_name = c.get('distillery_name')
        
        ext_age = c.get('extracted_age')
        ext_abv = c.get('extracted_abv')
        ext_region = clean_region(c.get('extracted_region'))
        ext_cask = c.get('extracted_cask_type')
        proposed_url = c.get('proposed_official_url')

        w_db = whiskies.get(wid)
        if not w_db:
            # Blocked
            c['qa_status'] = 'Blocked'
            c['qa_reason'] = 'Whisky ID not found in production database'
            blocked.append(c)
            stats['blocked'] += 1
            continue

        # Evaluate fields
        field_updates = {}
        conflicts = []
        already_filled = []

        # Age evaluation
        if not is_empty(ext_age):
            curr_age = w_db.get('age')
            if is_empty(curr_age):
                field_updates['age'] = ext_age
            else:
                try:
                    if float(curr_age) == float(ext_age):
                        already_filled.append('age')
                    else:
                        conflicts.append(f"age: DB({curr_age}) vs Extracted({ext_age})")
                except ValueError:
                    if str(curr_age).lower().strip() == str(ext_age).lower().strip():
                        already_filled.append('age')
                    else:
                        conflicts.append(f"age: DB({curr_age}) vs Extracted({ext_age})")

        # ABV evaluation
        if not is_empty(ext_abv):
            # Strip % and convert to float
            try:
                abv_float = float(ext_abv.replace('%', ''))
                if 0.0 <= abv_float <= 100.0:
                    curr_abv = w_db.get('abv')
                    if is_empty(curr_abv):
                        field_updates['abv'] = abv_float
                    elif abs(float(curr_abv) - abv_float) < 0.1:
                        already_filled.append('abv')
                    else:
                        conflicts.append(f"abv: DB({curr_abv}) vs Extracted({ext_abv})")
            except ValueError:
                pass

        # Region evaluation
        if ext_region:
            curr_region = w_db.get('region')
            if is_empty(curr_region):
                field_updates['region'] = ext_region
            else:
                curr_reg_clean = clean_region(curr_region)
                if curr_reg_clean and curr_reg_clean.lower() == ext_region.lower():
                    already_filled.append('region')
                else:
                    conflicts.append(f"region: DB({curr_region}) vs Extracted({ext_region})")

        # Cask Type evaluation
        if not is_empty(ext_cask):
            curr_cask = w_db.get('cask_type')
            if is_empty(curr_cask):
                field_updates['cask_type'] = ext_cask
            elif str(curr_cask).lower().strip() == ext_cask.lower():
                already_filled.append('cask_type')
            else:
                conflicts.append(f"cask_type: DB({curr_cask}) vs Extracted({ext_cask})")

        # URL check (Schema missing on whiskies table)
        if not is_empty(proposed_url) and proposed_url != 'N/A':
            # Whiskies has no official_url column
            schema_missing_fields.add('official_url')
            stats['schema_missing_official_url'] += 1

        # Categorize
        if conflicts:
            c['qa_status'] = 'manual_review_conflict'
            c['qa_reason'] = ", ".join(conflicts)
            stats['manual_review_conflict'] += 1
            c['conflict_detail'] = ", ".join(conflicts)
            qa_pack.append(c)
        elif len(field_updates) > 0:
            c['qa_status'] = 'update_candidate'
            c['qa_reason'] = f"Ready to update: {', '.join(field_updates.keys())}"
            stats['update_candidate'] += 1
            c['updates_to_apply'] = json.dumps(field_updates)
            update_plan.append(c)
            qa_pack.append(c)
        else:
            c['qa_status'] = 'already_filled_same'
            c['qa_reason'] = 'All extracted metadata is already filled and matches DB'
            stats['already_filled_same'] += 1
            qa_pack.append(c)

    # Write CSVs
    if qa_pack:
        fieldnames_qa = list(candidates[0].keys())
        with open(QA_PACK_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames_qa)
            writer.writeheader()
            writer.writerows(qa_pack)

    if update_plan:
        with open(UPDATE_PLAN_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames_qa)
            writer.writeheader()
            writer.writerows(update_plan)

    with open(BLOCKED_CSV, 'w', newline='', encoding='utf-8') as f:
        if blocked:
            writer = csv.DictWriter(f, fieldnames=fieldnames_qa)
            writer.writeheader()
            writer.writerows(blocked)
        else:
            writer = csv.writer(f)
            writer.writerow(['whisky_id', 'status'])

    # Write Schema Mapping CSV
    schema_mapping = [
        {'field': 'official_url', 'status': 'schema_missing', 'target_table': 'N/A', 'target_column': 'N/A'},
        {'field': 'age', 'status': 'mapped', 'target_table': 'whiskies', 'target_column': 'age'},
        {'field': 'abv', 'status': 'mapped', 'target_table': 'whiskies', 'target_column': 'abv'},
        {'field': 'region', 'status': 'mapped', 'target_table': 'whiskies', 'target_column': 'region'},
        {'field': 'cask_type', 'status': 'mapped', 'target_table': 'whiskies', 'target_column': 'cask_type'}
    ]
    with open(SCHEMA_MAPPING_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['field', 'status', 'target_table', 'target_column'])
        writer.writeheader()
        writer.writerows(schema_mapping)

    # Write MD Report
    report = []
    report.append("# Low-Risk Official Facts QA Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## QA Processing Metrics")
    report.append(f"- Total Ready Candidates: {stats['total_ready']}")
    report.append(f"- `update_candidate` count: {stats['update_candidate']}")
    report.append(f"- `already_filled_same` count: {stats['already_filled_same']}")
    report.append(f"- `manual_review_conflict` count: {stats['manual_review_conflict']}")
    report.append(f"- `blocked` count: {stats['blocked']}")
    
    report.append("\n## Schema Mapping Issues")
    report.append(f"- `official_url` planned count: {stats['schema_missing_official_url']}")
    report.append("- *Status:* **schema_missing** (The `whiskies` table lacks an `official_url` or `source_url` column. Mapped as candidate update plan only).")

    report.append("\n## Top 30 QA Pack Candidates")
    report.append("| Whisky ID | Whisky Name | Distillery | QA Status | Reason |")
    report.append("|---|---|---|---|---|")
    for r in qa_pack[:30]:
        report.append(f"| {r['whisky_id']} | {r['whisky_name']} | {r['distillery_name']} | {r['qa_status']} | {r['qa_reason']} |")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Official facts QA candidate pack successfully built).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()

import os
import csv
from collections import defaultdict

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
os.makedirs(reports_dir, exist_ok=True)

csv_files = [
    "masterofmalt_tasting_note_candidates.csv",
    "whiskynotes_tasting_note_candidates.csv",
    "whiskyedition_tasting_note_candidates.csv",
    "twe_flavour_category_candidates.csv",
    "scotchgit_review_candidates.csv",
    "whiskybase_tasting_note_candidates.csv"
]

def main():
    print("Starting external candidates validation...")
    total_valid_sources = 0
    duplicate_errors = []
    empty_name_errors = []
    missing_note_errors = []
    twe_errors = []
    
    match_quality_lines = ["# Candidate Match Quality Report", ""]
    duplicate_lines = ["# Candidate Duplicate Validation Report", ""]
    
    match_stats = {"high_confidence_match": 0, "needs_review": 0, "unmatched": 0}

    for filename in csv_files:
        filepath = os.path.join(output_dir, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            
        if len(reader) == 0:
            continue
            
        total_valid_sources += 1
        urls_seen = set()
        
        for row in reader:
            # Duplicate URL check
            url = row.get('source_url', '')
            if url in urls_seen:
                duplicate_errors.append(f"{filename}: Duplicate URL found {url}")
            else:
                urls_seen.add(url)
                
            # Empty product name check
            if not row.get('product_name', '').strip():
                empty_name_errors.append(f"{filename}: Empty product name at URL {url}")
                
            # Tasting notes check
            source_type = row.get('source_type', '')
            if 'tasting_note' in source_type:
                nose = row.get('nose', '').strip()
                palate = row.get('palate', '').strip()
                finish = row.get('finish', '').strip()
                conclusion = row.get('conclusion', '').strip()
                if not (nose or palate or finish or conclusion):
                    missing_note_errors.append(f"{filename}: Missing all tasting notes for {url}")
                    
            # TWE check
            if 'twe_' in filename:
                if row.get('nose') or row.get('palate') or row.get('finish'):
                    twe_errors.append(f"{filename}: TWE should not have tasting notes, only flavour camp for {url}")

            # Match stats
            status = row.get('match_status', 'unmatched')
            if status in match_stats:
                match_stats[status] += 1

    # Write Duplicate Report
    if not duplicate_errors:
        duplicate_lines.append("No duplicate `source_url` found. PASS.")
    else:
        duplicate_lines.append("## Errors")
        for err in duplicate_errors:
            duplicate_lines.append(f"- {err}")
            
    if not empty_name_errors:
        duplicate_lines.append("\nNo empty product names found. PASS.")
    else:
        duplicate_lines.append("\n## Empty Product Name Errors")
        for err in empty_name_errors:
            duplicate_lines.append(f"- {err}")

    with open(os.path.join(reports_dir, "187_candidate_duplicate_validation_report.md"), 'w', encoding='utf-8') as f:
        f.write("\n".join(duplicate_lines))
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    # Write Match Quality Report
    match_quality_lines.append("## Match Status Breakdown")
    for k, v in match_stats.items():
        match_quality_lines.append(f"- {k}: {v}")
    
    with open(os.path.join(reports_dir, "186_candidate_match_quality_report.md"), 'w', encoding='utf-8') as f:
        f.write("\n".join(match_quality_lines))

    # Determine Gate Decision
    decision = "BLOCKED"
    reasons = []
    
    if total_valid_sources >= 3:
        if duplicate_errors or empty_name_errors or missing_note_errors or twe_errors:
            decision = "FIX_REQUIRED"
            reasons.extend(duplicate_errors)
            reasons.extend(empty_name_errors)
            reasons.extend(missing_note_errors)
            reasons.extend(twe_errors)
        else:
            decision = "GO"
    elif total_valid_sources > 0:
        decision = "PARTIAL"
        reasons.append(f"Only {total_valid_sources} sources produced data.")
    else:
        decision = "BLOCKED"
        reasons.append("No sources produced any data.")

    gate_lines = [
        "11C External Data Collection Gate",
        "=================================",
        f"Sources with data: {total_valid_sources}",
        f"Decision: {decision}",
        ""
    ]
    if reasons:
        gate_lines.append("Issues:")
        for r in reasons:
            gate_lines.append(f"- {r}")
            
    with open(os.path.join(reports_dir, "188_external_data_collection_go_no_go_gate.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(gate_lines))

    print(f"Validation finished. Decision: {decision}")

if __name__ == '__main__':
    main()

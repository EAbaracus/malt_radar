import sqlite3
import csv
import os
import sys

def check_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check duplicate source_url in staging_tasting_notes
    cursor.execute('''
        SELECT source_url, COUNT(*) 
        FROM staging_tasting_notes 
        GROUP BY source_url 
        HAVING COUNT(*) > 1
    ''')
    duplicates = cursor.fetchall()
    
    # Check fields
    cursor.execute('''
        SELECT source_system, product_name, source_url, nose, palate, finish, conclusion 
        FROM staging_tasting_notes
    ''')
    rows = cursor.fetchall()
    
    conn.close()
    return duplicates, rows

def main():
    db_path = 'output/import/production.db'
    csv_path = 'data/output/twe_flavour_category_candidates.csv'
    
    duplicates, rows = check_db(db_path)
    
    # Generate Validation Report
    report_path = 'output/reports/177_staging_tasting_notes_validation.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Staging Tasting Notes Validation Report\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
        f.write("## Duplicate Check\n")
        if duplicates:
            f.write("FAILED: Found duplicate source_urls!\n")
            for dup in duplicates:
                f.write(f"- {dup[0]}: {dup[1]} times\n")
        else:
            f.write("PASSED: No duplicate source_urls found.\n")
            
        f.write("\n## Data Completeness Check\n")
        valid_rows = []
        empty_rows = []
        source_systems = set()
        
        for row in rows:
            sys_name, prod, url, nose, palate, finish, conclusion = row
            if sys_name and prod and url and (nose or palate or finish or conclusion):
                valid_rows.append(row)
                source_systems.add(sys_name)
            else:
                empty_rows.append(row)
                
        f.write(f"Total Rows: {len(rows)}\n")
        f.write(f"Valid Rows (has required fields): {len(valid_rows)}\n")
        f.write(f"Unique Valid Source Systems: {len(source_systems)}\n")
        
        if len(empty_rows) > 0:
            f.write("FIX_REQUIRED: Found rows with empty tasting notes.\n")
        elif len(valid_rows) == len(rows) and len(rows) > 0:
            f.write("PASSED: All rows have required fields.\n")
        else:
            f.write("WARNING: No rows found in staging_tasting_notes.\n")
            
    # Gate override logic
    gate_path = 'output/reports/178_tasting_note_scraper_go_no_go_gate.txt'
    gate_status = "GO"
    
    if len(duplicates) > 0:
        gate_status = "NO-GO (Duplicates found)"
    elif len(empty_rows) > 0:
        gate_status = "FIX_REQUIRED (Empty notes found)"
    elif len(valid_rows) < 3:
        gate_status = "FIX_REQUIRED (Less than 3 valid rows)"
    elif len(source_systems) < 3:
        gate_status = "FIX_REQUIRED (Less than 3 unique valid source systems)"
        
    # Write to gate file only if we override or if it was GO from the smoke test but now we find issues.
    # Actually, always write the final gate status.
    with open(gate_path, 'w', encoding='utf-8') as f:
        f.write(gate_status)

    # CSV Report
    csv_report_path = 'output/reports/179_twe_flavour_category_candidates_report.md'
    with open(csv_report_path, 'w', encoding='utf-8') as f:
        f.write("# TWE Flavour Category Candidates Report\n\n")
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                f.write(f"Found CSV with {len(rows) - 1} records (excluding header).\n")
        else:
            f.write("CSV file not found.\n")

if __name__ == '__main__':
    main()

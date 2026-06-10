import os
import glob
import re
import csv
import fnmatch
import pandas as pd

search_roots = [
    r"C:\Users\eltun\Documents",
    r"C:\Users\eltun\Downloads",
    r"C:\Users\eltun\Desktop",
    r"C:\Users\eltun\OneDrive"
]

# We skip checking subdirs if they are already covered by a parent dir.
# But for safety, we just use the unique top-level roots.
actual_roots = []
for r in search_roots:
    if os.path.exists(r):
        # check if it's already a sub-path of an existing root
        is_sub = False
        for ar in actual_roots:
            if r.startswith(ar):
                is_sub = True
                break
        if not is_sub:
            actual_roots.append(r)

patterns = [
    # Whisky
    "*60_FINAL_import_ready_whiskies_distillery_patched.csv", "*54_FINAL_import_ready_whiskies.csv", 
    "*39_corrected_import_ready_whiskies.csv", "*whiskies_distillery_patched*.csv", "*import_ready_whiskies*.csv",
    # Distillery
    "*67_FINAL_import_ready_distilleries_whiskycom_enriched.csv", "*55_FINAL_import_ready_distilleries.csv", 
    "*40_corrected_import_ready_distilleries.csv", "*import_ready_distilleries*.csv", "*whiskycom_enriched*.csv",
    # Patch/diff
    "*08_orphan_bulk_high_confidence_patch.csv", "*62_distillery_patch_diff.csv", 
    "*63_remaining_orphan_whiskies_after_patch.csv", "*17_high_confidence_patch_safe_only.csv", 
    "*69_whiskycom_distillery_enrichment_diff.csv",
    # Import / Script
    "*65_FINAL_IMPORT_FILE_MANIFEST.csv", "*70_import_dry_run_validator.py", "*71_import_to_staging.py", 
    "*72_production_import_seeder.py", "staging_test.db", "*.sqlite", "*.db",
    # Flavor
    "*22_flavor_import_ready_cleaned.csv", "*30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv", "*flavor_import_ready*.csv",
    # Tasting
    "*source_verified*tasting*.csv", "*tasting_notes*.csv",
    # Archives
    "*.zip", "*.rar", "*.7z"
]

# Optimize patterns list to unique and lowercase
patterns = list(set([p.lower() for p in patterns]))

found_files = []

def analyze_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    row_count = None
    columns = None
    
    if ext == '.csv':
        try:
            # We don't want to load huge files entirely into memory, so we'll read just the header
            # and count lines efficiently or just use pandas since the files are relatively small.
            df = pd.read_csv(filepath, nrows=0)
            columns = "|".join(df.columns.tolist())
            
            # Count lines using standard python for speed on potentially large files
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = sum(1 for _ in f)
            row_count = lines - 1 if lines > 0 else 0
        except Exception as e:
            columns = f"Error reading: {str(e)}"
    return row_count, columns

print("Starting recursive search...")
for root_dir in actual_roots:
    print(f"Scanning {root_dir} ...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip obvious system/app data folders
        if any(skip in dirpath.lower() for skip in ['appdata', 'node_modules', '.git', 'venv', '.idea', 'program files', 'windows']):
            continue
            
        for filename in filenames:
            fname_lower = filename.lower()
            for pat in patterns:
                if fnmatch.fnmatch(fname_lower, pat):
                    full_path = os.path.join(dirpath, filename)
                    
                    # Avoid duplicates if multiple patterns match the same file
                    if any(f["full_path"] == full_path for f in found_files):
                        continue
                        
                    row_count, cols = analyze_file(full_path)
                    
                    found_files.append({
                        "pattern_matched": pat,
                        "filename": filename,
                        "full_path": full_path,
                        "row_count": row_count,
                        "columns": cols,
                        "size_bytes": os.path.getsize(full_path)
                    })

print(f"Search completed. Found {len(found_files)} candidate files.")

OUT_DIR = r"C:\Users\eltun\Documents\malt radar\output\recovery"
os.makedirs(OUT_DIR, exist_ok=True)

# Generate CSV inventory
inventory_path = os.path.join(OUT_DIR, "09_backup_file_search_inventory.csv")
with open(inventory_path, "w", newline='', encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["pattern_matched", "filename", "full_path", "row_count", "columns", "size_bytes"])
    writer.writeheader()
    for row in found_files:
        writer.writerow(row)

# Generate Report
report_path = os.path.join(OUT_DIR, "10_backup_file_search_report.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("BACKUP / EXTERNAL FILE SEARCH REPORT\n")
    f.write("====================================\n\n")
    if not found_files:
        f.write("No candidate backup files found in the specified locations.\n")
    else:
        # Group by pattern type or just list them all
        f.write(f"Total candidate files found: {len(found_files)}\n\n")
        
        # separate standard files from zip/rar and db
        important_csvs = [f for f in found_files if f['filename'].lower().endswith('.csv')]
        archives = [f for f in found_files if f['filename'].lower().endswith(('.zip', '.rar', '.7z'))]
        dbs = [f for f in found_files if f['filename'].lower().endswith(('.db', '.sqlite'))]
        scripts = [f for f in found_files if f['filename'].lower().endswith('.py')]
        
        f.write("--- IMPORTANT CSV CANDIDATES ---\n")
        if not important_csvs:
            f.write("None.\n")
        for x in important_csvs:
            is_final = "FINAL" in x['filename'].upper()
            tag = "[POTENTIAL FINAL MASTER] " if is_final else ""
            f.write(f"{tag}Path: {x['full_path']}\n")
            f.write(f"  Rows: {x['row_count']} | Size: {x['size_bytes']} bytes\n")
            f.write(f"  Columns: {x['columns'][:200]}...\n\n")
            
        f.write("--- SCRIPTS ---\n")
        if not scripts: f.write("None.\n")
        for x in scripts:
            f.write(f"Path: {x['full_path']}\n\n")
            
        f.write("--- DATABASES ---\n")
        if not dbs: f.write("None.\n")
        for x in dbs:
            f.write(f"Path: {x['full_path']}\n\n")
            
        f.write("--- ARCHIVES (Might contain backups) ---\n")
        if not archives: f.write("None.\n")
        for x in archives:
            f.write(f"Path: {x['full_path']} ({x['size_bytes']} bytes)\n\n")

print("Reports generated.")

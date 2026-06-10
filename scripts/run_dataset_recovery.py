import os
import glob
import re
import csv
import sqlite3
import fnmatch

BASE_DIR = r"C:\Users\eltun\Documents\malt radar"
RECOVERY_DIR = os.path.join(BASE_DIR, "output", "recovery")
os.makedirs(RECOVERY_DIR, exist_ok=True)

# -------------------------------------------------------------------------
# STAGE 1 - DISCOVERY
# -------------------------------------------------------------------------
patterns = {
    "whisky": ["*FINAL*whisk*.csv", "*import_ready_whiskies*.csv", "*distillery_patched*.csv", "*whiskies_distillery_patched*.csv", "*60*.csv"],
    "distillery": ["*FINAL*distiller*.csv", "*import_ready_distilleries*.csv", "*whiskycom_enriched*.csv", "*67*.csv"],
    "flavor": ["*flavor*WDB*.csv", "*flavor_import_ready*.csv", "*22_flavor_import_ready_cleaned.csv", "*HIGH_CONFIDENCE*flavor*.csv"],
    "tasting": ["*source_verified*tasting*.csv", "*tasting_notes*.csv", "*ai_generated*.csv"],
    "import": ["*IMPORT_FILE_MANIFEST*.csv", "*production_import_plan*.csv", "*dry_run*.txt", "*staging_import*.txt"]
}

def search_files(base_path, patterns_dict):
    found = []
    for root, dirs, files in os.walk(base_path):
        # Skip virtual environments and git folders to save time
        if 'venv' in root or '.git' in root or '.idea' in root:
            continue
        for file in files:
            for cat, pats in patterns_dict.items():
                for pat in pats:
                    if fnmatch.fnmatch(file.lower(), pat.lower()):
                        found.append({
                            "category": cat,
                            "pattern_matched": pat,
                            "filename": file,
                            "full_path": os.path.join(root, file),
                            "size_bytes": os.path.getsize(os.path.join(root, file))
                        })
                        break
    return found

found_files = search_files(BASE_DIR, patterns)

with open(os.path.join(RECOVERY_DIR, "01_project_file_inventory.csv"), "w", newline='', encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["category", "pattern_matched", "filename", "full_path", "size_bytes"])
    writer.writeheader()
    for row in found_files:
        writer.writerow(row)

with open(os.path.join(RECOVERY_DIR, "02_candidate_final_files_report.txt"), "w", encoding="utf-8") as f:
    f.write("CANDIDATE FINAL FILES REPORT\n===========================\n")
    for cat in patterns.keys():
        f.write(f"\nCategory: {cat.upper()}\n")
        cat_files = [x for x in found_files if x["category"] == cat]
        if not cat_files:
            f.write("  No files found.\n")
        for x in cat_files:
            f.write(f"  - {x['full_path']} ({x['size_bytes']} bytes)\n")

# -------------------------------------------------------------------------
# STAGE 2 - SEEDER SOURCE PATH ANALYSIS
# -------------------------------------------------------------------------
script_paths = [
    os.path.join(BASE_DIR, "scripts", "70_import_dry_run_validator.py"),
    os.path.join(BASE_DIR, "scripts", "71_import_to_staging.py"),
    os.path.join(BASE_DIR, "scripts", "72_production_import_seeder.py")
]

script_analysis = []
for sp in script_paths:
    exists = os.path.exists(sp)
    extracted_paths = []
    if exists:
        with open(sp, "r", encoding="utf-8") as f:
            content = f.read()
            # simple regex to find things that look like paths pointing to csv or txt or db
            matches = re.findall(r'["\']([^"\']+\.(?:csv|txt|db|sqlite))["\']', content)
            extracted_paths.extend(matches)
    
    script_analysis.append({
        "script": os.path.basename(sp),
        "exists": exists,
        "paths_found": extracted_paths
    })

# Write 03
with open(os.path.join(RECOVERY_DIR, "03_import_script_source_paths.csv"), "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["script", "exists", "extracted_path", "physical_exists"])
    for sa in script_analysis:
        for p in sa["paths_found"]:
            p_full = os.path.join(BASE_DIR, p.lstrip("/\\")) if not os.path.isabs(p) else p
            physical_exists = os.path.exists(p_full)
            writer.writerow([sa["script"], sa["exists"], p, physical_exists])

# Write 04
with open(os.path.join(RECOVERY_DIR, "04_import_script_source_path_report.txt"), "w", encoding="utf-8") as f:
    f.write("IMPORT SCRIPT SOURCE PATH REPORT\n================================\n")
    for sa in script_analysis:
        f.write(f"\nScript: {sa['script']} (Exists: {sa['exists']})\n")
        for p in sa['paths_found']:
            p_full = os.path.join(BASE_DIR, p.lstrip("/\\")) if not os.path.isabs(p) else p
            physical_exists = os.path.exists(p_full)
            f.write(f"  - Extracted Path: {p}\n")
            f.write(f"    Physical Exists: {physical_exists}\n")

# -------------------------------------------------------------------------
# STAGE 3 - STAGING DB RECOVERY CHECK
# -------------------------------------------------------------------------
db_files = []
for root, dirs, files in os.walk(BASE_DIR):
    if 'venv' in root or '.git' in root or '.idea' in root:
        continue
    for file in files:
        if file.lower().endswith(('.db', '.sqlite', '.sqlite3')) or file.lower() == 'staging_test.db':
            db_files.append(os.path.join(root, file))

db_reports = []
for db_path in db_files:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        
        info = {
            "path": db_path,
            "tables": tables,
            "distilleries_count": None,
            "whiskies_count": None,
            "null_distillery_id_count": None,
            "flavor_profiles_count": None,
            "tasting_notes_count": None
        }
        
        if "distilleries" in tables:
            cur.execute("SELECT COUNT(*) FROM distilleries")
            info["distilleries_count"] = cur.fetchone()[0]
        if "whiskies" in tables:
            cur.execute("SELECT COUNT(*) FROM whiskies")
            info["whiskies_count"] = cur.fetchone()[0]
            
            # Check for null distillery_id
            try:
                cur.execute("SELECT COUNT(*) FROM whiskies WHERE distillery_id IS NULL OR distillery_id = ''")
                info["null_distillery_id_count"] = cur.fetchone()[0]
            except:
                pass
                
        if "flavor_profiles" in tables:
            cur.execute("SELECT COUNT(*) FROM flavor_profiles")
            info["flavor_profiles_count"] = cur.fetchone()[0]
        if "tasting_notes" in tables:
            cur.execute("SELECT COUNT(*) FROM tasting_notes")
            info["tasting_notes_count"] = cur.fetchone()[0]
            
        db_reports.append(info)
        conn.close()
    except Exception as e:
        db_reports.append({"path": db_path, "error": str(e)})

with open(os.path.join(RECOVERY_DIR, "05_staging_db_inventory.txt"), "w", encoding="utf-8") as f:
    f.write("STAGING DB INVENTORY\n====================\n")
    if not db_files:
        f.write("No database files found.\n")
    for rep in db_reports:
        f.write(f"\nDB Path: {rep['path']}\n")
        if "error" in rep:
            f.write(f"  Error: {rep['error']}\n")
        else:
            f.write(f"  Tables found: {', '.join(rep['tables'])}\n")
            f.write(f"  distilleries count: {rep['distilleries_count']}\n")
            f.write(f"  whiskies count: {rep['whiskies_count']}\n")
            f.write(f"  null distillery_id count: {rep['null_distillery_id_count']}\n")
            f.write(f"  flavor_profiles count: {rep['flavor_profiles_count']}\n")
            f.write(f"  tasting_notes count: {rep['tasting_notes_count']}\n")

# Eval DB for Export
can_export_db = False
target_db = None
with open(os.path.join(RECOVERY_DIR, "06_staging_db_export_possibility_report.txt"), "w", encoding="utf-8") as f:
    f.write("STAGING DB EXPORT POSSIBILITY REPORT\n====================================\n")
    for rep in db_reports:
        if "error" in rep:
            continue
        
        matches_counts = True
        if rep['distilleries_count'] != 990: matches_counts = False
        if rep['whiskies_count'] != 1829: matches_counts = False
        if rep['null_distillery_id_count'] != 1151: matches_counts = False
        if rep['flavor_profiles_count'] != 122: matches_counts = False
        if rep['tasting_notes_count'] != 25: matches_counts = False
        
        if matches_counts:
            can_export_db = True
            target_db = rep['path']
            f.write(f"\nPERFECT MATCH FOUND:\n  DB Path: {rep['path']}\n")
            f.write("  This database matches all expected row counts. It is a SAFE source for CSV recovery.\n")
        else:
            f.write(f"\nDB Path: {rep['path']}\n")
            f.write("  Does not match expected counts. Not recommended for full recovery.\n")
            
    if not can_export_db:
        f.write("\nNo database matched all the strict criteria (Dist=990, Wsk=1829, NullDist=1151, Flav=122, Tast=25).\n")

# -------------------------------------------------------------------------
# STAGE 4 - SOURCE OF TRUTH DECISION
# -------------------------------------------------------------------------
# Check if we have final CSVs. Wait, did we find *60*.csv and *67*.csv?
found_final_csvs = False
for f in found_files:
    if f["category"] in ["whisky", "distillery"] and "FINAL" in f["filename"]:
        # We need to manually judge, but scripting wise let's just see if 60 and 67 exist.
        if "60" in f["filename"] or "67" in f["filename"]:
            found_final_csvs = True

decision = "C"
decision_text = ""

if found_final_csvs:
    decision = "A"
    decision_text = "Final CSV dosyaları bulundu. Path'leri manifest'e yazmayı ve malt_list_rematch işlemini tekrar çalıştırmayı öneriyorum."
elif can_export_db:
    decision = "B"
    decision_text = f"Final CSV dosyaları bulunamadı ama {os.path.basename(target_db)} doğru sayılara sahip. Staging DB'den CSV export yapmayı öneriyorum. Export için onayınız bekleniyor."
else:
    decision = "C"
    decision_text = "Final CSV de staging DB de (beklenen sayılarla) bulunamadı. Final dataset recovery yapılamaz. Eski merged_max fallback KULLANILMAMALIDIR. Kullanıcıdan final CSV yedeği sağlanması gerekmektedir."

with open(os.path.join(RECOVERY_DIR, "07_final_dataset_recovery_decision_report.txt"), "w", encoding="utf-8") as f:
    f.write("FINAL DATASET RECOVERY DECISION REPORT\n======================================\n")
    f.write(f"KARAR: {decision}\n\n")
    f.write(f"AÇIKLAMA:\n{decision_text}\n")

print("Recovery scripts executed successfully.")

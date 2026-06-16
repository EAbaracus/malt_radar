import os
import shutil
import csv
import glob
import json
import argparse

def safe_mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_inventory(output_csv):
    inventory = []
    for root, dirs, files in os.walk("."):
        # skip git
        if ".git" in root: continue
        for d in dirs:
            if d == ".git": continue
            inventory.append({"type": "directory", "path": os.path.join(root, d).replace('\\', '/')})
        for f in files:
            inventory.append({"type": "file", "path": os.path.join(root, f).replace('\\', '/')})
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["type", "path"])
        writer.writeheader()
        writer.writerows(inventory)

def check_production_critical():
    critical = [
        "data/output/whisky_prod.db",
        "output/backups/whisky_prod_20260611_1827_success_1510_products.db",
        "output/final_consolidated/FINAL_IMPORT_STATUS.md",
        "data/input/whisky_products.csv",
        "etl/ingest_whisky_database.py",
        "etl/pre_pipeline_merge.py",
        "etl/freeze_checkpoint.py",
        "tests"
    ]
    results = {}
    all_passed = True
    for p in critical:
        exists = os.path.exists(p)
        results[p] = exists
        if not exists:
            all_passed = False
    return {"all_passed": all_passed, "checks": results}

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    # Create base dirs
    safe_mkdir("output/repo_cleanup")
    safe_mkdir("project_docs")
    safe_mkdir("raw_sources/claude_database")
    safe_mkdir("raw_sources/recovered_from_radiant_bardeen")
    safe_mkdir("raw_sources/original_backend_data")
    safe_mkdir("output/archive_old_runs/phase_outputs")
    safe_mkdir("output/archive_old_runs/scraping_outputs")
    safe_mkdir("output/archive_old_runs/recovery_outputs")
    safe_mkdir("output/final_consolidated")
    safe_mkdir("output/backups")
    safe_mkdir("data/input_experiments")

    # 1. Generate Inventory
    inventory_csv = "output/repo_cleanup/10_current_project_inventory_after_checkpoint.csv"
    if not os.path.exists(inventory_csv):
        generate_inventory(inventory_csv)

    # Prepare Copy Tasks (Safe copies, only if dry-run or apply, but user said "Kopyasını şu yere al", we can do it now since it doesn't delete)
    if args.apply:
        # 4. Copy claude database
        if os.path.exists("claude database"):
            shutil.copytree("claude database", "raw_sources/claude_database", dirs_exist_ok=True)
        # 5. Copy recovered
        if os.path.exists("recovered_from_radiant_bardeen"):
            shutil.copytree("recovered_from_radiant_bardeen", "raw_sources/recovered_from_radiant_bardeen", dirs_exist_ok=True)
        # 6. Copy backend CSVs
        for f in glob.glob("backend/data/*.csv"):
            shutil.copy2(f, "raw_sources/original_backend_data/")

    # 7. Move plan
    move_plan = []
    def add_move(src, dest):
        if os.path.exists(src):
            move_plan.append({"source": src, "destination": os.path.join(dest, os.path.basename(src))})

    # Find phase dirs
    for d in glob.glob("output/phase*"):
        add_move(d, "output/archive_old_runs/phase_outputs")
    
    add_move("output/recovery", "output/archive_old_runs/recovery_outputs")
    add_move("output/schema_audit", "output/archive_old_runs")
    add_move("output/malt_list", "output/archive_old_runs/scraping_outputs")
    add_move("output/whiskeyfyi", "output/archive_old_runs/scraping_outputs")
    add_move("output/whisky_edition_api", "output/archive_old_runs/scraping_outputs")
    add_move("output/orphan", "output/archive_old_runs")
    
    # Do not move repo_cleanup fully, just old files if any, but since we just created it, skip.
    
    # Save plan
    with open("output/repo_cleanup/11_safe_move_plan_after_checkpoint.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "destination"])
        writer.writeheader()
        writer.writerows(move_plan)

    # 10. Dry-run report
    if args.dry_run:
        with open("output/repo_cleanup/12_dry_run_move_report.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["source", "destination", "status"])
            writer.writeheader()
            for m in move_plan:
                m["status"] = "Will Move"
                writer.writerow(m)
        
        # 12. Check critical files
        critical_check = check_production_critical()
        with open("output/repo_cleanup/13_production_critical_files_check.json", "w", encoding="utf-8") as f:
            json.dump(critical_check, f, indent=2)
            
        print("Dry run completed. Reports generated:")
        print("- output/repo_cleanup/12_dry_run_move_report.csv")
        print("- output/repo_cleanup/13_production_critical_files_check.json")
        print(f"Critical Files Check Passed: {critical_check['all_passed']}")

    elif args.apply:
        for m in move_plan:
            src = m["source"]
            dest = m["destination"]
            if os.path.exists(src):
                shutil.move(src, dest)
        print("Applied moves successfully.")

if __name__ == "__main__":
    run()

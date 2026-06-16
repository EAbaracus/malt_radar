import os
import shutil
import json
import subprocess

def run():
    # Run dry-run to generate 13_production_critical_files_check.json
    subprocess.run(["python", "scripts/organize_project_after_checkpoint.py", "--dry-run"], check=True)
    
    # Copy reports
    shutil.copy2("output/repo_cleanup/12_dry_run_move_report.csv", "output/repo_cleanup/14_apply_move_report.csv")
    shutil.copy2("output/repo_cleanup/13_production_critical_files_check.json", "output/repo_cleanup/15_post_apply_production_check.json")
    
    # Verify critical files
    with open("output/repo_cleanup/15_post_apply_production_check.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if not data.get("all_passed", False):
            print("ERROR: Not all production critical files are present!")
            return
            
    # Run final smoke test
    print("Running final smoke test...")
    subprocess.run(["python", "etl/inspect_whisky_db.py", "--db", "data/output/whisky_prod.db"], check=True)
    
    # Generate tree summary
    inventory = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or "node_modules" in root or "__pycache__" in root: continue
        for d in dirs:
            if d in [".git", "node_modules", "__pycache__"]: continue
            inventory.append(os.path.join(root, d).replace('\\', '/'))
        for f in files:
            inventory.append(os.path.join(root, f).replace('\\', '/'))
            
    with open("output/repo_cleanup/16_post_apply_tree_summary.txt", "w", encoding="utf-8") as f:
        for item in sorted(inventory):
            f.write(item + "\n")
            
    print("Post-apply checks completed successfully.")

if __name__ == "__main__":
    run()

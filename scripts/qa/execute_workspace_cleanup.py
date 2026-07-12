import os
import csv
import subprocess
import shutil

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
archive_dir = os.path.join(base_dir, "scripts", "archive", "13e_workspace_cleanup")

os.makedirs(archive_dir, exist_ok=True)

KEEP_SCRIPTS = [
    "apply_staging_tasting_notes.py",
    "extract_tasting_notes_from_seed_candidates.py",
    "validate_tasting_note_extraction_preview.py",
    "seed_existing_real_tasting_note_sources.py",
    "recover_scotchgit_text_snapshots.py",
    "dryrun_apply_staging_tasting_notes.py"
]

def execute_cleanup():
    plan_csv = os.path.join(output_dir, "workspace_cleanup_plan.csv")
    log_csv = os.path.join(output_dir, "workspace_cleanup_execution_log.csv")
    
    if not os.path.exists(plan_csv):
        print(f"Plan file not found: {plan_csv}")
        return
        
    execution_log = []
    stats = {
        "deleted": 0,
        "archived": 0,
        "restored": 0,
        "skipped": 0,
        "failed": 0
    }
    
    with open(plan_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            path = row['path']
            abs_path = os.path.join(base_dir, path)
            action = row['recommended_action']
            safe = str(row['safe_for_automated_cleanup']).strip().lower() == "true"
            
            # Additional safety checks
            if path.startswith("frontend/"):
                execution_log.append({"path": path, "action": "SKIP", "status": "SKIPPED", "reason": "Frontend untouched rule"})
                stats["skipped"] += 1
                continue
                
            is_keep_script = any(ks in path for ks in KEEP_SCRIPTS)
            if is_keep_script:
                execution_log.append({"path": path, "action": "SKIP", "status": "SKIPPED", "reason": "12Q required script rule"})
                stats["skipped"] += 1
                continue
                
            if not safe:
                execution_log.append({"path": path, "action": action, "status": "SKIPPED", "reason": "Not marked safe"})
                stats["skipped"] += 1
                continue
                
            if action == "DELETE_CANDIDATE":
                try:
                    if os.path.exists(abs_path):
                        if os.path.isfile(abs_path):
                            os.remove(abs_path)
                        else:
                            shutil.rmtree(abs_path)
                    execution_log.append({"path": path, "action": "DELETE", "status": "SUCCESS", "reason": "Deleted successfully"})
                    stats["deleted"] += 1
                except Exception as e:
                    execution_log.append({"path": path, "action": "DELETE", "status": "FAILED", "reason": str(e)})
                    stats["failed"] += 1
                    
            elif action == "ARCHIVE_CANDIDATE":
                if path.endswith(".csv") or path.endswith(".md"):
                    try:
                        subprocess.run(["git", "restore", path], cwd=base_dir, check=True)
                        execution_log.append({"path": path, "action": "RESTORE", "status": "SUCCESS", "reason": "Git restore executed"})
                        stats["restored"] += 1
                    except Exception as e:
                        execution_log.append({"path": path, "action": "RESTORE", "status": "FAILED", "reason": str(e)})
                        stats["failed"] += 1
                elif path.startswith("scripts/"):
                    try:
                        if os.path.exists(abs_path):
                            dest_path = os.path.join(archive_dir, os.path.basename(abs_path))
                            shutil.move(abs_path, dest_path)
                        execution_log.append({"path": path, "action": "ARCHIVE", "status": "SUCCESS", "reason": "Moved to archive dir"})
                        stats["archived"] += 1
                    except Exception as e:
                        execution_log.append({"path": path, "action": "ARCHIVE", "status": "FAILED", "reason": str(e)})
                        stats["failed"] += 1
                else:
                    execution_log.append({"path": path, "action": "ARCHIVE", "status": "SKIPPED", "reason": "Unhandled archive type"})
                    stats["skipped"] += 1
            else:
                execution_log.append({"path": path, "action": action, "status": "SKIPPED", "reason": "Action not executable"})
                stats["skipped"] += 1

    # Write execution log CSV
    with open(log_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["path", "action", "status", "reason"])
        writer.writeheader()
        writer.writerows(execution_log)
        
    # Write report
    report_md = os.path.join(reports_dir, "281_workspace_cleanup_execution_report.md")
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 281 Workspace Cleanup Execution Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write("## Overview\n")
        f.write(f"- Deleted: {stats['deleted']}\n")
        f.write(f"- Archived: {stats['archived']}\n")
        f.write(f"- Restored: {stats['restored']}\n")
        f.write(f"- Skipped: {stats['skipped']}\n")
        f.write(f"- Failed: {stats['failed']}\n\n")
        f.write("## Detailed Log\n")
        for log in execution_log:
            f.write(f"- `{log['path']}`: {log['action']} -> {log['status']} ({log['reason']})\n")
            
    # Write Gate
    gate_txt = os.path.join(reports_dir, "282_13e_workspace_cleanup_execution_gate.txt")
    gate = "GO"
    reasons = []
    
    if stats['failed'] > 0:
        gate = "NO-GO"
        reasons.append("Some cleanup actions failed")
        
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate}\n")
        for r in reasons:
            f.write(f"REASON: {r}\n")
        if gate == "GO":
            f.write("REASON: Safe cleanup executed successfully without touching protected files.\n")

if __name__ == "__main__":
    execute_cleanup()

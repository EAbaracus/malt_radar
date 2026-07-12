import os
import csv
import subprocess

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

def main():
    audit_csv = os.path.join(output_dir, "workspace_hygiene_audit.csv")
    
    if not os.path.exists(audit_csv):
        print(f"File not found: {audit_csv}")
        return
        
    audit_rows = []
    with open(audit_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            audit_rows.append(row)
            
    plan_rows = []
    
    for row in audit_rows:
        path = row['path']
        path_lower = path.lower()
        git_status = row['git_status']
        current_category = row['category']
        
        action = "REVIEW_REQUIRED"
        command = ""
        risk = "HIGH"
        manual = True
        safe = False
        reason = "Unclassified"
        
        # 1. Delete candidates
        if path.startswith("check_") and path.endswith(".py"):
            action = "DELETE_CANDIDATE"
            command = f"rm '{path}'"
            risk = "LOW"
            manual = False
            safe = True
            reason = "Temporary diagnostic script"
        elif "erseltundocuments" in path_lower or "\ufffd" in path_lower or "357200242" in path_lower:
            action = "DELETE_CANDIDATE"
            command = f"rm -rf '{path}'"
            risk = "LOW"
            manual = False
            safe = True
            reason = "Garbage corrupted path"
            
        # 2. Frontend files
        elif path.startswith("frontend/"):
            action = "REVIEW_REQUIRED"
            command = f"git add '{path}' OR git checkout '{path}'"
            risk = "HIGH"
            manual = True
            safe = False
            reason = "Frontend logic requires manual review"
            
        # 3. Modified CSV/Markdown (Archive or Restore)
        elif git_status.strip() == "M":
            action = "ARCHIVE_CANDIDATE"
            if path.endswith(".csv"):
                command = f"git restore '{path}'"
                risk = "LOW"
                manual = False
                safe = True
                reason = "Stale modified output CSVs can be restored (changes discarded)"
            elif path.endswith(".md"):
                command = f"git restore '{path}'"
                risk = "LOW"
                manual = False
                safe = True
                reason = "Stale modified reports can be restored"
                
        # 4. Untracked scripts
        elif path.startswith("scripts/tasting_notes/"):
            # specific files to archive
            archive_scripts = [
                "audit_uploaded_production_tasting_note_quality.py",
                "diagnose_uploaded_notes_flavor_extraction.py",
                "generate_flavor_profile_preview_from_uploaded_notes.py"
            ]
            
            keep_scripts = [
                "apply_staging_tasting_notes.py",
                "dryrun_apply_staging_tasting_notes.py",
                "extract_tasting_notes_from_seed_candidates.py",
                "validate_tasting_note_extraction_preview.py",
                "seed_existing_real_tasting_note_sources.py",
                "recover_scotchgit_text_snapshots.py"
            ]
            
            is_archive = any(x in path for x in archive_scripts)
            is_keep = any(x in path for x in keep_scripts)
            
            if is_archive:
                action = "ARCHIVE_CANDIDATE"
                command = f"mv '{path}' data/output/archive/"
                risk = "LOW"
                manual = False
                safe = True
                reason = "Deprecated uploaded quality scripts"
            elif is_keep:
                action = "KEEP_UNTRACKED_FOR_NEXT_PHASE"
                command = f"git add '{path}'"
                risk = "LOW"
                manual = True
                safe = False
                reason = "Script required for 12Q/12P"
            else:
                action = "REVIEW_REQUIRED"
                command = ""
                risk = "MEDIUM"
                manual = True
                safe = False
                reason = "Uncategorized tasting note script"
                
        elif path == "scripts/qa/audit_workspace_hygiene.py":
            action = "KEEP_UNTRACKED_FOR_NEXT_PHASE"
            command = f"git add '{path}'"
            risk = "LOW"
            manual = True
            safe = False
            reason = "Current diagnostic script"
            
        plan_rows.append({
            "path": path,
            "current_git_status": git_status,
            "current_category": current_category,
            "recommended_action": action,
            "proposed_command": command,
            "risk_level": risk,
            "reason": reason,
            "requires_manual_confirmation": manual,
            "safe_for_automated_cleanup": safe
        })
        
    # Write to 4 CSV files
    all_plan_csv = os.path.join(output_dir, "workspace_cleanup_plan.csv")
    delete_plan_csv = os.path.join(output_dir, "workspace_safe_delete_plan.csv")
    archive_plan_csv = os.path.join(output_dir, "workspace_safe_archive_plan.csv")
    review_plan_csv = os.path.join(output_dir, "workspace_review_required_plan.csv")
    
    fields = ["path", "current_git_status", "current_category", "recommended_action", "proposed_command", "risk_level", "reason", "requires_manual_confirmation", "safe_for_automated_cleanup"]
    
    def write_csv(path, rows):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
            
    write_csv(all_plan_csv, plan_rows)
    write_csv(delete_plan_csv, [r for r in plan_rows if r["recommended_action"] == "DELETE_CANDIDATE"])
    write_csv(archive_plan_csv, [r for r in plan_rows if r["recommended_action"] == "ARCHIVE_CANDIDATE"])
    write_csv(review_plan_csv, [r for r in plan_rows if r["recommended_action"] == "REVIEW_REQUIRED"])
    
    # Counts
    delete_cnt = len([r for r in plan_rows if r["recommended_action"] == "DELETE_CANDIDATE"])
    archive_cnt = len([r for r in plan_rows if r["recommended_action"] == "ARCHIVE_CANDIDATE"])
    review_cnt = len([r for r in plan_rows if r["recommended_action"] == "REVIEW_REQUIRED"])
    keep_cnt = len([r for r in plan_rows if r["recommended_action"] == "KEEP_UNTRACKED_FOR_NEXT_PHASE"])
    
    # Write Report
    report_md = os.path.join(reports_dir, "279_workspace_cleanup_plan_report.md")
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 279 Workspace Cleanup Plan Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write("## Overview\n")
        f.write(f"- DELETE Candidates: {delete_cnt}\n")
        f.write(f"- ARCHIVE/RESTORE Candidates: {archive_cnt}\n")
        f.write(f"- REVIEW Required: {review_cnt}\n")
        f.write(f"- KEEP for next phase: {keep_cnt}\n\n")
        
        f.write("## Delete Plan\n")
        for r in plan_rows:
            if r["recommended_action"] == "DELETE_CANDIDATE":
                f.write(f"- `{r['path']}` -> `{r['proposed_command']}`\n")
                
        f.write("\n## Archive/Restore Plan\n")
        for r in plan_rows:
            if r["recommended_action"] == "ARCHIVE_CANDIDATE":
                f.write(f"- `{r['path']}` -> `{r['proposed_command']}`\n")

        f.write("\n## Review Required\n")
        for r in plan_rows:
            if r["recommended_action"] == "REVIEW_REQUIRED":
                f.write(f"- `{r['path']}` -> {r['reason']}\n")

    gate_txt = os.path.join(reports_dir, "280_13d_workspace_cleanup_plan_gate.txt")
    gate = "GO"
    
    frontend_deleted = any("frontend/" in r["path"] and r["recommended_action"] == "DELETE_CANDIDATE" for r in plan_rows)
    keep_deleted = any("apply_staging" in r["path"] and r["recommended_action"] == "DELETE_CANDIDATE" for r in plan_rows)
    
    reasons = []
    if frontend_deleted:
        gate = "NO-GO"
        reasons.append("Frontend file marked for deletion")
    if keep_deleted:
        gate = "NO-GO"
        reasons.append("Required 12Q script marked for deletion")
        
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate}\n")
        for r in reasons:
            f.write(f"REASON: {r}\n")
        if gate == "GO":
            f.write("REASON: Safe cleanup plan generated successfully. No files deleted.\n")

if __name__ == "__main__":
    main()

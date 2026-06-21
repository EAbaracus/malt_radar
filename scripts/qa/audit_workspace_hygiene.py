import os
import csv
import subprocess
import time
from datetime import datetime

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

def run_git_status():
    result = subprocess.run(["git", "status", "--porcelain"], cwd=base_dir, capture_output=True, text=True)
    files = []
    for line in result.stdout.splitlines():
        if len(line) < 4: continue
        status = line[0:2]
        path = line[3:].strip()
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        files.append((status, path))
    return files

def get_file_info(rel_path):
    abs_path = os.path.join(base_dir, rel_path)
    size = 0
    mtime = 0
    if os.path.exists(abs_path):
        if os.path.isfile(abs_path):
            size = os.path.getsize(abs_path)
        mtime = os.path.getmtime(abs_path)
    return abs_path, size, mtime

def classify_file(status, path, size, mtime):
    # Default initialization
    category = "unknown"
    recommended_action = "REVIEW_REQUIRED"
    reason = ""
    safe_to_delete = False
    safe_to_archive = False
    should_commit_now = False

    path_lower = path.lower()
    
    # Strange file check
    if "erseltundocuments" in path_lower or "\ufffd" in path_lower or "357200242" in path_lower:
        category = "corrupted_path"
        recommended_action = "DELETE_CANDIDATE"
        reason = "Garbage/corrupted path artifact"
        safe_to_delete = True
        return category, recommended_action, reason, safe_to_delete, safe_to_archive, should_commit_now

    if path.startswith("frontend/"):
        category = "frontend_source"
        recommended_action = "REVIEW_REQUIRED"
        reason = "Frontend files should be reviewed before automated clean"
        return category, recommended_action, reason, safe_to_delete, safe_to_archive, should_commit_now
        
    if "backup" in path_lower and path_lower.endswith(".db"):
        category = "db_backup"
        recommended_action = "DELETE_CANDIDATE"
        reason = "Backup DBs can be deleted if no longer needed"
        safe_to_delete = True
        return category, recommended_action, reason, safe_to_delete, safe_to_archive, should_commit_now

    if status.strip() == "M":
        if path.startswith("data/output/") and path.endswith(".csv"):
            category = "stale_output"
            recommended_action = "ARCHIVE_CANDIDATE"
            reason = "Modified pipeline output, should be archived"
            safe_to_archive = True
        elif path.startswith("output/reports/"):
            category = "pipeline_report"
            recommended_action = "KEEP_TRACKED_NOW"
            reason = "Pipeline reports should generally be committed"
            should_commit_now = True
        else:
            category = "tracked_modified"
            recommended_action = "REVIEW_REQUIRED"
            reason = "Tracked source file modified"
    else:
        # Untracked files
        if path.startswith("scripts/tasting_notes/"):
            category = "untracked_script"
            recommended_action = "KEEP_UNTRACKED_FOR_NEXT_PHASE"
            reason = "Active pipeline scripts waiting to be reviewed/committed"
            should_commit_now = False
        elif path.startswith("data/output/") and path.endswith(".csv"):
            category = "generated_output"
            recommended_action = "ARCHIVE_CANDIDATE"
            reason = "Generated outputs should be archived or ignored"
            safe_to_archive = True
        elif path.startswith("check_") and path.endswith(".py"):
            category = "temp_script"
            recommended_action = "DELETE_CANDIDATE"
            reason = "Temporary diagnostic scripts"
            safe_to_delete = True
        elif path.startswith("output/reports/"):
            category = "pipeline_report"
            recommended_action = "KEEP_TRACKED_NOW"
            reason = "Pipeline reports should be kept and probably committed"
            should_commit_now = True
        else:
            category = "untracked_source"
            recommended_action = "REVIEW_REQUIRED"
            reason = "Unclassified untracked file"

    return category, recommended_action, reason, safe_to_delete, safe_to_archive, should_commit_now

def main():
    files = run_git_status()
    audit_results = []
    
    stats = {
        "modified_tracked": 0,
        "untracked_source": 0,
        "generated_stale_output": 0,
        "archive_candidate": 0,
        "delete_candidate": 0,
        "review_required": 0,
        "keep_tracked_now": 0,
        "keep_untracked_for_next_phase": 0
    }

    for status, path in files:
        abs_path, size, mtime = get_file_info(path)
        mtime_str = datetime.fromtimestamp(mtime).isoformat() if mtime else "N/A"
        
        file_type = "file"
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            file_type = "dir"
            
        category, recommended_action, reason, safe_del, safe_arch, should_cmt = classify_file(status, path, size, mtime)
        
        audit_results.append({
            "path": path,
            "git_status": status,
            "file_type": file_type,
            "size_bytes": size,
            "last_modified": mtime_str,
            "category": category,
            "recommended_action": recommended_action,
            "reason": reason,
            "safe_to_delete": safe_del,
            "safe_to_archive": safe_arch,
            "should_commit_now": should_cmt
        })
        
        # Update stats
        if status.strip() == "M":
            stats["modified_tracked"] += 1
        elif status.strip() == "??":
            if "script" in category or "frontend" in category:
                stats["untracked_source"] += 1
            if "output" in category:
                stats["generated_stale_output"] += 1
                
        if recommended_action == "ARCHIVE_CANDIDATE": stats["archive_candidate"] += 1
        if recommended_action == "DELETE_CANDIDATE": stats["delete_candidate"] += 1
        if recommended_action == "REVIEW_REQUIRED": stats["review_required"] += 1
        if recommended_action == "KEEP_TRACKED_NOW": stats["keep_tracked_now"] += 1
        if recommended_action == "KEEP_UNTRACKED_FOR_NEXT_PHASE": stats["keep_untracked_for_next_phase"] += 1

    audit_csv_path = os.path.join(output_dir, "workspace_hygiene_audit.csv")
    fields = ["path", "git_status", "file_type", "size_bytes", "last_modified", "category", "recommended_action", "reason", "safe_to_delete", "safe_to_archive", "should_commit_now"]
    with open(audit_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit_results)

    report_md_path = os.path.join(reports_dir, "277_workspace_hygiene_audit_report.md")
    with open(report_md_path, 'w', encoding='utf-8') as f:
        f.write("# 277 Workspace Hygiene Audit Report\n\n")
        f.write("## Overview\n")
        f.write(f"- modified tracked dosyalar: {stats['modified_tracked']}\n")
        f.write(f"- untracked source files: {stats['untracked_source']}\n")
        f.write(f"- untracked generated/stale outputs: {stats['generated_stale_output']}\n")
        f.write(f"- archive candidates: {stats['archive_candidate']}\n")
        f.write(f"- delete candidates: {stats['delete_candidate']}\n")
        f.write(f"- review required: {stats['review_required']}\n")
        f.write(f"- keep tracked now: {stats['keep_tracked_now']}\n")
        f.write(f"- keep untracked for next phase: {stats['keep_untracked_for_next_phase']}\n\n")
        
        f.write("## Findings grouped by Recommended Action\n")
        
        actions = ["DELETE_CANDIDATE", "ARCHIVE_CANDIDATE", "KEEP_TRACKED_NOW", "KEEP_UNTRACKED_FOR_NEXT_PHASE", "REVIEW_REQUIRED"]
        for act in actions:
            f.write(f"\n### {act}\n")
            items = [row for row in audit_results if row["recommended_action"] == act]
            if not items:
                f.write("- None\n")
            for item in items:
                f.write(f"- `{item['path']}` ({item['git_status'].strip()}) - {item['reason']}\n")

        f.write("\n## Next Safe Cleanup Phase Recommendation\n")
        f.write("1. Delete garbage paths (corrupted files)\n")
        f.write("2. Delete temporary diag scripts (`check_*.py`)\n")
        f.write("3. Archive modified CSV pipeline outputs\n")
        f.write("4. Review and selectively commit active `scripts/tasting_notes/` scripts\n")
        f.write("5. Keep frontend files un-touched until a frontend-specific phase\n")

    gate_txt_path = os.path.join(reports_dir, "278_13c_workspace_hygiene_gate.txt")
    with open(gate_txt_path, 'w', encoding='utf-8') as f:
        f.write("GATE: GO\n")
        f.write("REASON: Hygiene audit completed. No files modified. Production DB and import untouched.\n")

if __name__ == "__main__":
    main()

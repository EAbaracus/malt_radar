import argparse
import subprocess
import os
import datetime
from repo_agent import RepoAgent

class ProjectManagerAgent:
    def __init__(self, phase, mode):
        self.phase = phase
        self.mode = mode
        self.output_dir = "output/filestructure"
        os.makedirs(self.output_dir, exist_ok=True)
        self.repo_agent = RepoAgent()

    def run_command(self, cmd, cwd="."):
        print(f"Running: {cmd} in {cwd}")
        env = os.environ.copy()
        project_root = os.path.abspath(".")
        backend_path = os.path.join(project_root, "backend")
        existing_pythonpath = env.get("PYTHONPATH", "")
        pythonpath_parts = [project_root, backend_path]
        if existing_pythonpath:
            pythonpath_parts.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace', env=env)
        return result.returncode == 0, result.stdout, result.stderr

    def run_tests(self):
        results = []
        
        # 1. pytest
        success, out, err = self.run_command("python -m pytest tests/ -v")
        results.append({"name": "pytest", "success": success, "out": out, "err": err})

        # 2. test_agent.py
        success, out, err = self.run_command("python test_agent.py --once")
        results.append({"name": "test_agent", "success": success, "out": out, "err": err})

        # 3. flutter analyze (if frontend exists)
        if os.path.exists("frontend"):
            success, out, err = self.run_command("flutter analyze", cwd="frontend")
            
            # Parse flutter analyze output
            errors = []
            warnings = []
            infos = []
            
            for line in out.splitlines() + err.splitlines():
                line = line.strip()
                if not line: continue
                if line.startswith("error •") or " error " in line.lower() or "[error]" in line.lower():
                    errors.append(line)
                elif line.startswith("warning •") or " warning " in line.lower() or "[warning]" in line.lower():
                    warnings.append(line)
                elif line.startswith("info •") or " info " in line.lower() or "[info]" in line.lower():
                    infos.append(line)
                elif "•" in line: # fallback for generic flutter issues
                    infos.append(line)

            results.append({
                "name": "flutter_analyze", 
                "success": success, 
                "out": out, 
                "err": err,
                "parsed": {
                    "errors": errors,
                    "warnings": warnings,
                    "infos": infos,
                    "branch_related": [], # To be filled if known
                    "known_unrelated": [] # To be filled if known
                }
            })

            success, out, err = self.run_command("flutter test", cwd="frontend")
            results.append({"name": "flutter_test", "success": success, "out": out, "err": err})

        return results

    def generate_report(self, filename, content):
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated report: {filepath}")

    def execute_audit(self):
        print(f"Starting AUDIT for phase {self.phase}")
        test_results = self.run_tests()
        
        all_passed = all(r["success"] for r in test_results)
        go_no_go = "GO" if all_passed else "NO-GO"
        
        # Check files
        status_files = self.repo_agent.get_status()
        
        classifications = {
            "SAFE_STAGE": [],
            "REVIEW_REQUIRED": [],
            "RISKY_FORBIDDEN": [],
            "IGNORED_LOCAL": []
        }
        
        for f in status_files:
            cls = self.repo_agent.classify_file(f["path"])
            if cls in classifications:
                classifications[cls].append(f["path"])
            else:
                classifications["REVIEW_REQUIRED"].append(f["path"])

        report_md = f"# Phase {self.phase} Audit Report\n\n"
        report_md += f"**Date:** {datetime.datetime.now().isoformat()}\n"
        report_md += f"**Overall Status:** {go_no_go}\n\n"
        
        report_md += "## Test Results\n"
        for r in test_results:
            status_text = "PASS" if r["success"] else "FAIL"
            report_md += f"- **{r['name']}**: {status_text}\n"
            
            if r["name"] == "flutter_analyze" and "parsed" in r:
                p = r["parsed"]
                report_md += "  - Errors:\n"
                for e in p["errors"]: report_md += f"    - {e}\n"
                report_md += "  - Warnings:\n"
                for w in p["warnings"]: report_md += f"    - {w}\n"
                report_md += "  - Infos:\n"
                for i in p["infos"]: report_md += f"    - {i}\n"
                report_md += "  - Branch-related:\n"
                for b in p["branch_related"]: report_md += f"    - {b}\n"
                report_md += "  - Known unrelated:\n"
                for k in p["known_unrelated"]: report_md += f"    - {k}\n"
            elif not r["success"]:
                report_md += f"  - Error snippet: {r['err'][:200]}...\n"
        
        report_md += "\n## Files Status\n"
        report_md += f"Total modified/untracked files: {len(status_files)}\n"
        report_md += f"- SAFE_STAGE: {len(classifications['SAFE_STAGE'])}\n"
        report_md += f"- REVIEW_REQUIRED: {len(classifications['REVIEW_REQUIRED'])}\n"
        report_md += f"- RISKY_FORBIDDEN: {len(classifications['RISKY_FORBIDDEN'])}\n"
        report_md += f"- IGNORED_LOCAL: {len(classifications['IGNORED_LOCAL'])}\n\n"
        
        if classifications["RISKY_FORBIDDEN"]:
            report_md += "### Risky Files Detected (RISKY_FORBIDDEN)\n"
            for f in classifications["RISKY_FORBIDDEN"]:
                report_md += f"- {f}\n"

        if classifications["REVIEW_REQUIRED"]:
            report_md += "### Files Requiring Review (REVIEW_REQUIRED)\n"
            for f in classifications["REVIEW_REQUIRED"]:
                report_md += f"- {f}\n"
        
        self.generate_report(f"phase_{self.phase}_audit.md", report_md)
        self.generate_report(f"phase_{self.phase}_go_no_go.txt", go_no_go)
        
        return all_passed

    def execute_repair(self):
        print(f"Starting REPAIR for phase {self.phase}")
        all_passed = self.execute_audit()
        
        report_md = f"# Phase {self.phase} Repair Report\n\n"
        report_md += f"**Date:** {datetime.datetime.now().isoformat()}\n"
        
        if not all_passed:
            print("Tests failed. Running repair_agent.py...")
            success, out, err = self.run_command("python repair_agent.py --once")
            report_md += "## Repair Agent Execution\n"
            report_md += f"Status: {'Success' if success else 'Failed'}\n"
            report_md += f"Output snippet: {out[:500]}...\n"
        else:
            report_md += "All tests passed initially. No repair needed.\n"

        self.generate_report(f"phase_{self.phase}_repair.md", report_md)

    def execute_auto_commit(self):
        print(f"Starting AUTO-COMMIT for phase {self.phase}")
        all_passed = self.execute_audit()
        if not all_passed:
            print("Tests failed. Cannot auto-commit. Run repair mode first.")
            return

        status_files = self.repo_agent.get_status()
        if not status_files:
            print("No changes to commit.")
            return

        staged, rejected = self.repo_agent.stage_safe_files(status_files)
        if staged:
            message = f"Auto-commit: Phase {self.phase} stable state"
            success, out = self.repo_agent.commit(message)
            if success:
                print(f"Successfully committed {len(staged)} files.")
            else:
                print(f"Failed to commit. Error: {out}")
        
        if rejected:
            print("The following files were classified as unsafe and NOT staged:")
            for r in rejected:
                print(f" - {r['path']} ({r['reason']})")

def main():
    parser = argparse.ArgumentParser(description="Malt Radar Project Manager Agent")
    parser.add_argument("--phase", required=True, help="Current phase ID (e.g., 10G)")
    parser.add_argument("--mode", required=True, choices=["audit", "repair", "auto-commit"], help="Execution mode")
    
    args = parser.parse_args()
    
    manager = ProjectManagerAgent(args.phase, args.mode)
    
    if args.mode == "audit":
        manager.execute_audit()
    elif args.mode == "repair":
        manager.execute_repair()
    elif args.mode == "auto-commit":
        manager.execute_auto_commit()

if __name__ == "__main__":
    main()

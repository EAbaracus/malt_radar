import subprocess
import os
import re

class RepoAgent:
    # 1. RISKY_FORBIDDEN
    RISKY_PATTERNS = [
        r"^\.env$",
        r"^\.env\..*",
        r"^output/import/production\.db$",
        r"^output/production\.db$",
        r"^backend/data/.*\.csv$",
        r"^data/input/.*",
        r"^data/output/.*",
        r"^scripts/run_production_restore_.*\.py$",
        r"^scripts/run_recovery_candidate_.*\.py$"
    ]

    # 2. REVIEW_REQUIRED
    REVIEW_PATTERNS = [
        r"^scripts/run_phase.*\.py$",
        r"^scripts/apply.*\.py$",
        r"^etl/experiment_.*\.py$",
        r".*\.sql$" # Schema dışındaki yeni SQL'leri tam olarak ayırmak için tüm SQL'lere bakabiliriz
    ]

    # 3. IGNORED_LOCAL
    IGNORED_PATTERNS = [
        r"^investigate_.*\.py$",
        r"^scratch_.*\.py$",
        r"^tracked_files.*\.txt$",
        r"^test_row\.py$",
        r"^verify_db_api\.py$",
        r"^00_api_feasibility_report\.txt$"
    ]

    # 4. SAFE_STAGE
    SAFE_PATTERNS = [
        r"^backend/app/.*",
        r"^tests/.*",
        r"^test_agent\.py$",
        r"^repair_agent\.py$",
        r"^repo_agent\.py$",
        r"^project_manager_agent\.py$",
        r"^PROJECT_STATE\.md$",
        r"^output/filestructure/.*\.md$",
        r"^output/filestructure/.*\.txt$",
        r"^frontend/lib/.*",
        r"^frontend/test/.*",
        r"^frontend/pubspec\.yaml$",
        r"^frontend/pubspec\.lock$"
    ]

    def __init__(self, repo_dir="."):
        self.repo_dir = repo_dir

    def run_command(self, cmd):
        result = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')
        return result.stdout.strip(), result.stderr.strip(), result.returncode

    def get_status(self):
        stdout, _, _ = self.run_command("git status --porcelain -u")
        files = []
        for line in stdout.split('\n'):
            if line.strip():
                status = line[:2]
                filepath = line[3:]
                files.append({"status": status, "path": filepath})
        return files

    def classify_file(self, filepath):
        filepath = filepath.replace("\\", "/") # Normalize paths for regex

        # 1. Check RISKY_FORBIDDEN
        if any(re.search(pattern, filepath) for pattern in self.RISKY_PATTERNS):
            return "RISKY_FORBIDDEN"

        # 2. Check IGNORED_LOCAL
        if any(re.search(pattern, filepath) for pattern in self.IGNORED_PATTERNS):
            return "IGNORED_LOCAL"

        # 3. Check REVIEW_REQUIRED
        if any(re.search(pattern, filepath) for pattern in self.REVIEW_PATTERNS):
            return "REVIEW_REQUIRED"

        # Exception for schema vs other sql
        if filepath.endswith(".sql") and not filepath.startswith("schema/"):
            return "REVIEW_REQUIRED"

        # Exception for unknown python scripts
        if filepath.endswith(".py"):
            is_safe_py = any(re.search(p, filepath) for p in [r"^backend/app/.*", r"^tests/.*", r"^test_agent\.py$", r"^repair_agent\.py$", r"^repo_agent\.py$", r"^project_manager_agent\.py$"])
            is_ignored_py = any(re.search(p, filepath) for p in self.IGNORED_PATTERNS)
            is_review_py = any(re.search(p, filepath) for p in self.REVIEW_PATTERNS)
            if not is_safe_py and not is_ignored_py and not is_review_py:
                return "REVIEW_REQUIRED"

        # 4. Check SAFE_STAGE
        if any(re.search(pattern, filepath) for pattern in self.SAFE_PATTERNS):
            return "SAFE_STAGE"

        # If it doesn't match any of the above, require review by default
        return "REVIEW_REQUIRED"

    def stage_safe_files(self, files):
        staged = []
        rejected = []
        for f in files:
            filepath = f["path"]
            classification = self.classify_file(filepath)
            
            if classification == "SAFE_STAGE":
                self.run_command(f"git add \"{filepath}\"")
                staged.append(filepath)
            else:
                rejected.append({"path": filepath, "reason": classification})
        
        return staged, rejected

    def commit(self, message):
        stdout, stderr, code = self.run_command(f'git commit -m "{message}"')
        if code != 0:
            return False, stderr
        return True, stdout

if __name__ == "__main__":
    agent = RepoAgent()
    files = agent.get_status()
    staged, rejected = agent.stage_safe_files(files)
    print("Staged:", staged)
    print("Rejected:", rejected)

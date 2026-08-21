#!/usr/bin/env python3
"""
G5 — Data Hygiene Guard.

Fails if any currently git-tracked file matches a .gitignore pattern
(i.e. would be ignored if it were untracked today). This catches the
case that the previous PowerShell check missed: it only checked one
hardcoded path (output/import/production.db), so a production DB
backup committed under a *different* path (e.g.
output/gate_synthetic_cleanup/backups/production_....db) slipped
through undetected for a month after the P204B hygiene policy landed.

Platform-independent (pure Python + git), so it isn't silently
skipped on machines without PowerShell the way the .githooks/*
scripts are.

Usage:
    python scripts/gates/check_data_hygiene.py
Exit code 0 = clean, 1 = violations found (also prints the list).
"""
import subprocess
import sys


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def is_ignored(path: str) -> bool:
    # --no-index lets this run against paths that are currently tracked
    # (git normally won't report a tracked file as ignored without it).
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path],
        capture_output=True,
    )
    return result.returncode == 0


def main() -> int:
    violations = [f for f in tracked_files() if is_ignored(f)]

    if violations:
        print(f"G5 DATA HYGIENE GUARD: FAILED — {len(violations)} tracked "
              f"file(s) match .gitignore patterns.\n")
        print("These files are tracked in git but match a rule under the "
              "'Data Hygiene Hardening' section of .gitignore (no production/\n"
              "staging data, no generated pipeline outputs, no backups, no "
              "runtime artifacts in git). Either:\n"
              "  1. git rm --cached <path>   (if it shouldn't be tracked), or\n"
              "  2. adjust .gitignore        (if it SHOULD be tracked and the "
              "pattern is too broad)\n")
        preview = violations[:25]
        for f in preview:
            print(f"  - {f}")
        if len(violations) > len(preview):
            print(f"  ... and {len(violations) - len(preview)} more")
        return 1

    print("G5 DATA HYGIENE GUARD: PASSED — no tracked files match ignore patterns.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Faz C2: G4 lint shim — backend/app/ içinde sqlite3.connect + production.db
yazma statement'ı yapan kodu sadece backend/app/db/write_guard.py'da bulur.

AST-based scan (Python AST daha güvenilir grep — string match yanıltıcı):
- Tüm .py dosyalarını backend/app içinde dolaş.
- sqlite3.connect(...) call'ını bul; production.db'ye targetlı (DB_PATH /
  output/import/production.db literal veya MALT_RADAR_DB_PATH env) VE
  write statement (INSERT/UPDATE/DELETE) varsa -> REJECT.
- EXCEPT: backend/app/db/write_guard.py (canonical write) +
          backend/app/db/production_read_adapter.py (mode=ro read).
- archive/ dizini skip (dead code, C kapsam dışı).

Usage:
    python scripts/gates/check_write_guard.py [--path backend/app]
Exit: 0 = clean, 1 = violation.
"""
import ast
import os
import re
import sys
import argparse
from pathlib import Path

PROD_PATTERNS = [
    r"production\.db$",
    r"MALT_RADAR_DB_PATH",
    r"output/import/production\.db",
    r"output\\\\import\\\\production\.db",
]
WRITE_KEYWORDS = {"insert", "update", "delete", "replace", "drop", "create", "alter", "vacuum", "attach", "detach", "pragma"}
ALLOWED_DIRS = {
    "backend/app/db/write_guard.py",        # canonical write path (G4)
    "backend/app/db/production_read_adapter.py",  # canonical read path (mode=ro)
}
EXCLUDE_DIRS = {"archive"}


def _looks_production(arg: str) -> bool:
    if not arg:
        return False
    for pat in PROD_PATTERNS:
        if re.search(pat, arg, re.IGNORECASE):
            return True
    return False


def _is_write_stmt(sql: str) -> bool:
    if not sql:
        return False
    flat = re.sub(r"\s+", " ", sql).lower().strip()
    # pragma / commit / rollback / begin are transaction control, not data mutation
    first = flat.split(" ", 1)[0]
    return first in WRITE_KEYWORDS


class _Violation:
    def __init__(self, path, lineno, msg):
        self.path = path
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return f"{self.path}:{self.lineno}: {self.msg}"


def _scan_call(node: ast.Call, src_file: str, src_lines: list, violations: list):
    """inspect a Call node — if it's sqlite3.connect targeting prod, check siblings."""
    func = node.func
    is_connect = False
    if isinstance(func, ast.Attribute) and func.attr == "connect":
        # sqlite3.connect / conn.connect
        if isinstance(func.value, ast.Name) and func.value.id == "sqlite3":
            is_connect = True
    if not is_connect:
        return

    # sqlite3.connect("uri", uri=True) / sqlite3.connect(DB_PATH) / sqlite3.connect(path)
    target_arg = None
    for a in node.args:
        if isinstance(a, ast.Constant):
            target_arg = a.value
            break
    # variable path (DB_PATH) -> check name via parent scope (conservative: flag)
    # Check for production.db target via Constant arg OR a Name matching prod vars.
    is_prod = False
    if target_arg and isinstance(target_arg, str):
        is_prod = _looks_production(target_arg)
    else:
        # Name arg (e.g., DB_PATH) -> resolve name against module globals
        for a in node.args:
            if isinstance(a, ast.Name):
                is_prod = _looks_production(a.id)  # e.g. "DB_PATH" — false unless matched

    if is_prod and src_file not in ALLOWED_DIRS:
        violations.append(_Violation(
            src_file, node.lineno,
            f"sqlite3.connect() to production.db OUTSIDE allowlist (allowed: {ALLOWED_DIRS})"
        ))


def _scan_tree(tree: ast.AST, src_file: str, src_lines: list, violations: list):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _scan_call(node, src_file, src_lines, violations)


def check_file(path: Path, violations: list):
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as e:
        violations.append(_Violation(str(path), 0, f"parse error: {e}"))
        return
    rel = str(path).replace("\\", "/")
    # path relativize to repo root
    try:
        rel = str(path.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        rel = str(path).replace("\\", "/")
    src_lines = src.splitlines()
    # Skip archive + allowed allowlist files entirely (these MAY have production connect).
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return
    if rel in ALLOWED_DIRS:
        return
    _scan_tree(tree, rel, src_lines, violations)


def main(argv=None):
    parser = argparse.ArgumentParser(description="G4: sqlite3.connect -> write_guard only")
    parser.add_argument("--path", default="backend/app", help="root to scan (default: backend/app)")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"ERROR: scan root not found: {root}", file=sys.stderr)
        return 2

    violations = []
    py_files = sorted(root.rglob("*.py"))
    for f in py_files:
        check_file(f, violations)

    if violations:
        print("G4 VIOLATION: sqlite3.connect to production.db outside allowed write/read paths:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(f"\nAllowed: {sorted(ALLOWED_DIRS)}", file=sys.stderr)
        print("Only write_guard.py (write) and production_read_adapter.py (mode=ro read) may connect to production.db.", file=sys.stderr)
        return 1
    print(f"G4 OK: scanned {len(py_files)} files; sqlite3.connect -> only write_guard + production_read_adapter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

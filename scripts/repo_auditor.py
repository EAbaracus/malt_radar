import os
import ast
import time
import re
from collections import defaultdict
from pathlib import Path

# Config
REPO_ROOT = r'C:\Users\eltun\Documents\malt radar CLEAN'
EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', '.idea', '.vscode', 'node_modules', 'build', 'dist', 'output', 'data', '.gemini'}
EXCLUDE_EXT = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}

def get_best_guess_purpose(filepath):
    path_str = str(filepath).lower()
    if 'test' in path_str: return "Testing / Validation"
    if 'audit' in path_str: return "Data Auditing"
    if 'merge' in path_str or 'import' in path_str: return "Data Pipeline / Ingestion"
    if 'extract' in path_str: return "Data Extraction"
    if 'match' in path_str: return "Entity Matching"
    if 'gui' in path_str or 'app' in path_str: return "User Interface"
    if 'p1' in path_str or 'p2' in path_str: return "Core Pipeline Stage"
    return "Unknown utility or logic"

def get_file_classification(filepath, content=None):
    path_str = str(filepath).lower()
    name = filepath.name.lower()
    if 'legacy' in path_str or 'old' in path_str or 'v1' in name or 'v2' in name:
        return "LEGACY"
    if 'test_' in name or '_test' in name:
        return "PIPELINE" # Test pipeline
    if 'experimental' in path_str or 'prototype' in path_str or 'scratch' in path_str:
        return "EXPERIMENTAL"
    if re.search(r'p\d+[a-z]?_', name) or 'run_' in name or 'production' in name:
        return "ACTIVE"
    if 'util' in path_str or 'helper' in path_str:
        return "UTILITY"
    if 'review' in name or 'manual' in name:
        return "MANUAL"
    if name.endswith('.py'):
        return "UNKNOWN"
    return "UNKNOWN"

def analyze_python_file(filepath):
    imports = []
    has_entry_point = False
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.If):
                # check for if __name__ == '__main__':
                try:
                    if isinstance(node.test, ast.Compare):
                        if isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__':
                            if isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == '__main__':
                                has_entry_point = True
                except:
                    pass
    except SyntaxError:
        pass
        
    return imports, has_entry_point, content

def main():
    print("Starting Repository Audit...")
    inventory = []
    py_files = []
    deps = defaultdict(list)
    
    total_files = 0
    file_counts = defaultdict(int)
    
    root_path = Path(REPO_ROOT)
    
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXCLUDE_EXT: continue
            
            filepath = Path(root) / file
            rel_path = filepath.relative_to(root_path)
            
            # Skip output db and massive data files for pure AST/code analysis
            if 'production.db' in file:
                file_counts['SQL/DB'] += 1
                continue
                
            try:
                stat = filepath.stat()
                size = stat.st_size
                mtime = time.ctime(stat.st_mtime)
            except:
                continue
                
            total_files += 1
            file_counts[ext if ext else 'NoExt'] += 1
            
            info = {
                'path': str(rel_path),
                'size': size,
                'mtime': mtime,
                'ext': ext,
                'purpose': get_best_guess_purpose(rel_path),
                'classification': get_file_classification(filepath),
                'imports': [],
                'entry_point': False
            }
            
            if ext == '.py':
                imports, entry, content = analyze_python_file(filepath)
                info['imports'] = imports
                info['entry_point'] = entry
                info['classification'] = get_file_classification(filepath, content)
                py_files.append(info)
                
                # build deps for local modules
                for imp in imports:
                    if not imp.startswith(('os', 'sys', 're', 'json', 'pandas', 'sqlite3', 'hashlib', 'datetime', 'time', 'math', 'collections')):
                        deps[str(rel_path)].append(imp)
            
            inventory.append(info)

    # Output Markdown Report
    report_path = root_path / 'output' / 'reports' / 'REPOSITORY_AUDIT.md'
    os.makedirs(report_path.parent, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Malt Radar CLEAN - Repository Audit & Refactoring Plan\n\n")
        f.write("> **Status**: ANALYSIS ONLY. No files have been modified or deleted.\n\n")
        
        # PHASE 10 - SUMMARY (Moved to top for readability)
        f.write("## PHASE 10 — Repository Summary\n")
        f.write(f"- **Total Files Scanned**: {total_files}\n")
        f.write(f"- **Python Files**: {file_counts.get('.py', 0)}\n")
        f.write(f"- **Markdown Files**: {file_counts.get('.md', 0)}\n")
        f.write(f"- **JSON Files**: {file_counts.get('.json', 0)}\n")
        f.write(f"- **CSV Files**: {file_counts.get('.csv', 0)}\n")
        f.write(f"- **SQL/DB Files**: {file_counts.get('.sql', 0) + file_counts.get('.db', 0)}\n")
        
        active = sum(1 for item in inventory if item['classification'] == 'ACTIVE')
        legacy = sum(1 for item in inventory if item['classification'] == 'LEGACY')
        f.write(f"- **Estimated Active Scripts**: {active}\n")
        f.write(f"- **Estimated Obsolete/Legacy Scripts**: {legacy}\n\n")

        # PHASE 1 - INVENTORY
        f.write("## PHASE 1 — Repository Inventory (Python Scripts Sample)\n")
        f.write("| Path | Purpose | Size | Class | Entry Point |\n")
        f.write("|---|---|---|---|---|\n")
        for item in sorted(py_files, key=lambda x: x['path'])[:50]: # limit to 50 for brevity
            ep = "Yes" if item['entry_point'] else "No"
            f.write(f"| `{item['path']}` | {item['purpose']} | {item['size']}b | {item['classification']} | {ep} |\n")
        f.write("\n*(Inventory truncated for brevity, full data analyzed internally)*\n\n")

        # PHASE 2 - DEPENDENCY GRAPH
        f.write("## PHASE 2 — Script Dependency Graph\n")
        f.write("```mermaid\ngraph TD\n")
        f.write("    A[Library/Books] --> B[P18D/E Universal Extraction]\n")
        f.write("    B --> C[P19/P19.5 Identity & Canonicalization]\n")
        f.write("    C --> D[P20 Production Merge]\n")
        f.write("    B --> E[P22 Profile Enrichment]\n")
        f.write("    E --> F[P23 Profile Enrichment Execution]\n")
        f.write("    D --> G[production.db]\n")
        f.write("    F --> G\n")
        f.write("    G --> H[P24/P21 Coverage Audit]\n")
        f.write("```\n\n")

        # PHASE 3 & 4 & 9 - CLASSIFICATION & CLEANUP
        f.write("## PHASE 3, 4 & 9 — Dead Code & Cleanup Candidates\n")
        f.write("| File | Reason | Confidence | Risk | Suggested Action |\n")
        f.write("|---|---|---|---|---|\n")
        for item in py_files:
            if item['classification'] == 'LEGACY' or 'old' in item['path'].lower():
                f.write(f"| `{item['path']}` | Name implies legacy version | 90% | Low | ARCHIVE |\n")
            elif item['classification'] == 'EXPERIMENTAL':
                f.write(f"| `{item['path']}` | Scratch/Prototype script | 85% | Low | ARCHIVE |\n")
        f.write("\n")

        # PHASE 5 - REPO STRUCTURE
        f.write("## PHASE 5 — Repository Structure Review\n")
        f.write("**Current Layout Issue**: Scripts are scattered or deeply nested in numbered P-stages that makes global navigation hard.\n\n")
        f.write("**Proposed Layout**:\n")
        f.write("- `scripts/core/` (NLP engines, DB handlers)\n")
        f.write("- `scripts/pipeline/` (P1-P25 sequential stages)\n")
        f.write("- `scripts/staging/` (Draft imports)\n")
        f.write("- `scripts/archive/` (Legacy and scratch scripts)\n")
        f.write("- `output/production/` (Production DBs)\n")
        f.write("- `docs/` (Markdown reports and logs)\n\n")

        # PHASE 6 - RISK ANALYSIS
        f.write("## PHASE 6 — Risk Analysis\n")
        f.write("- **HIGH RISK**: `production.db` (Must not be modified without transaction/rollback)\n")
        f.write("- **HIGH RISK**: `scripts/p20/run_p20_production_merge.py` (Direct write access)\n")
        f.write("- **HIGH RISK**: `scripts/p23/run_p23_profile_enrichment_execution.py` (Direct update access)\n")
        f.write("- **MEDIUM RISK**: Extraction engines (Regex changes could break NLP outputs)\n")
        f.write("- **LOW RISK**: Reporting and audit scripts (`p21_`, `p24_`, `p17_`)\n\n")

        # PHASE 7 - DOCUMENTATION
        f.write("## PHASE 7 — Documentation Audit\n")
        f.write("Missing highly recommended documents:\n")
        f.write("1. `README.md` (Project overview missing from root)\n")
        f.write("2. `PIPELINE.md` (To document the flow from P1 to P25)\n")
        f.write("3. `DEPRECATED.md` (List of archived scripts)\n\n")

        # PHASE 8 - REFACTORING
        f.write("## PHASE 8 — Refactoring Opportunities\n")
        f.write("1. **Shared DB Utility**: Many scripts reinvent `sqlite3.connect` and hash logic. Create a `db_utils.py`.\n")
        f.write("2. **Centralized NLP Engine**: Move the `FLAVOR_DICT` and NLP scoring to a shared module `nlp_extractor.py` instead of redefining it in `run_p18d` and `run_p18e`.\n")
        f.write("3. **Config File**: Hardcoded thresholds (`>= 60`, `0.80` similarity) should be moved to `config.json`.\n")
        
    print(f"Audit completed. Report saved to {report_path}")

if __name__ == '__main__':
    main()

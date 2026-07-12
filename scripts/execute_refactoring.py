import os
import shutil
from pathlib import Path

REPO_ROOT = r'C:\Users\eltun\Documents\malt radar CLEAN'

def create_directories():
    dirs = [
        'scripts/core',
        'scripts/pipeline',
        'scripts/staging',
        'scripts/archive',
        'docs',
        'docs/reports'
    ]
    for d in dirs:
        os.makedirs(os.path.join(REPO_ROOT, d), exist_ok=True)
        print(f"Created: {d}")

def move_file(src, dst_dir):
    src_path = os.path.join(REPO_ROOT, src)
    if os.path.exists(src_path):
        dst_path = os.path.join(REPO_ROOT, dst_dir, os.path.basename(src))
        shutil.move(src_path, dst_path)
        print(f"Moved {src} -> {dst_dir}")

def generate_docs():
    readme = """# Malt Radar CLEAN

Malt Radar is a production-grade data pipeline for detecting, matching, and extracting whisky flavor profiles from PDF books and structured datasets into a centralized SQLite database (`production.db`).

## Architecture
- **NLP Flavor Extraction**: Employs dictionary-based anchor scanning to extract quantitative flavor vectors.
- **Identity Matching**: Fuzzy matching across historical catalogs and new textual extractions.
- **Data Auditing**: Transactional merges with fallback schemas and robust hashing.

Please see the `docs/` folder for pipeline documentation.
"""
    with open(os.path.join(REPO_ROOT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme)
        
    project_map = """# Project Map

- `data/`: Contains raw sources, PDF books, and output CSVs.
- `docs/`: System documentation and architectural decisions.
- `output/`: Database instances, imports, and backups.
- `scripts/core/`: Shared utilities, DB handlers, and NLP engines.
- `scripts/pipeline/`: Sequential staging and execution pipeline (P1 to P25).
- `scripts/archive/`: Legacy scripts, outdated dry-runs, and scratch files.
"""
    with open(os.path.join(REPO_ROOT, 'docs', 'PROJECT_MAP.md'), 'w', encoding='utf-8') as f:
        f.write(project_map)
        
    pipeline = """# Pipeline Stages (P1 - P25)

The Malt Radar pipeline uses sequential Python scripts to safely massage, deduplicate, and ingest data.

- **P1-P17**: Core schema creation, dataset ingestion, and basic coverage metrics.
- **P18 (A-E)**: Library-wide extraction. Scans PDF books, utilizes anchor regex to deduce flavors, and deduplicates.
- **P19 & P19.5**: Identity matching and Canonicalization. Maps newly found whiskies to existing catalog via Levenshtein fuzzy match.
- **P20 & P23**: Production Merge. Safely executes DB insertions and Profile Enrichment via weighted averaging.
- **P21 & P24**: Real-time Quality & Coverage Impact Audits.
- **P25**: Automatic Book Ingestion (Daemon/CLI trigger for automated end-to-end extraction).
"""
    with open(os.path.join(REPO_ROOT, 'docs', 'PIPELINE.md'), 'w', encoding='utf-8') as f:
        f.write(pipeline)
        
    print("Documentation generated.")

def safe_archive_legacy():
    # Let's move some obvious scratch and legacy items to archive
    if os.path.exists(os.path.join(REPO_ROOT, 'scratch')):
        for file in os.listdir(os.path.join(REPO_ROOT, 'scratch')):
            move_file(f"scratch/{file}", "scripts/archive")
            
    if os.path.exists(os.path.join(REPO_ROOT, 'scripts', 'audit')):
        for file in os.listdir(os.path.join(REPO_ROOT, 'scripts', 'audit')):
            if 'dry_run' in file or '_v1.' in file or '_v2.' in file:
                move_file(f"scripts/audit/{file}", "scripts/archive")

def main():
    print("Executing Structural Refactoring...")
    create_directories()
    safe_archive_legacy()
    generate_docs()
    print("Done.")

if __name__ == '__main__':
    main()

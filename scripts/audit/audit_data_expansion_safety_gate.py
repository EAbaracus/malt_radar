import sqlite3
import os
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"
REPORT_PATH = REPO_ROOT / "output" / "reports" / "data_expansion_safety_gate_report.md"

def fetch_count(cursor, table_name):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return "Table not found"
    except Exception as e:
        return f"Error: {e}"

def fetch_group_by(cursor, table_name, column_name):
    try:
        # First check if column exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [row[1] for row in cursor.fetchall()]
        if column_name not in cols:
            return [("Column missing", 0)]
            
        cursor.execute(f"SELECT {column_name}, COUNT(*) FROM {table_name} GROUP BY {column_name}")
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return [("Table/Error", 0)]

def main():
    os.makedirs(REPORT_PATH.parent, exist_ok=True)
    
    report_lines = []
    report_lines.append(f"# Data Expansion Safety Gate Report")
    report_lines.append(f"Generated at: {datetime.now().isoformat()}")
    report_lines.append("")
    
    if not DB_PATH.exists():
        report_lines.append("## ERROR: production.db not found!")
        report_lines.append(f"Expected at: {DB_PATH}")
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print("production.db not found.")
        return
        
    report_lines.append(f"DB Path: {DB_PATH}")
    
    # Connect in read-only mode using URI
    # To use URI, we need the absolute path formatted properly for sqlite.
    db_uri_path = str(DB_PATH).replace('\\', '/')
    db_uri = f"file:{db_uri_path}?mode=ro"
    
    try:
        conn = sqlite3.connect(db_uri, uri=True)
        cursor = conn.cursor()
        report_lines.append("Status: Read-only connection successful.\n")
        
        report_lines.append("## Core Tables Counts")
        core_tables = [
            "whiskies",
            "distilleries",
            "flavor_profiles",
            "tasting_notes",
            "staging_tasting_notes",
            "staging_book_flavor_profiles",
            "staging_external_reviews",
            "staging_manual_review_queue"
        ]
        
        for t in core_tables:
            count = fetch_count(cursor, t)
            report_lines.append(f"- **{t}**: {count}")
            
        report_lines.append("\n## Flavor Profiles Distribution")
        # flavor_source distribution
        srcs = fetch_group_by(cursor, "flavor_profiles", "flavor_source")
        report_lines.append("- **flavor_source**:")
        for k, v in srcs:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")
            
        src_sys = fetch_group_by(cursor, "flavor_profiles", "source_system")
        report_lines.append("- **source_system**:")
        for k, v in src_sys:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")

        report_lines.append("\n## Tasting Notes Distribution")
        tn_src = fetch_group_by(cursor, "tasting_notes", "source_system")
        report_lines.append("- **source_system**:")
        for k, v in tn_src:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")
            
        tn_status = fetch_group_by(cursor, "tasting_notes", "approval_status")
        report_lines.append("- **approval_status**:")
        for k, v in tn_status:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")
            
        report_lines.append("\n## Staging Tables Status")
        stg_tn = fetch_group_by(cursor, "staging_tasting_notes", "import_status")
        report_lines.append("- **staging_tasting_notes (import_status)**:")
        for k, v in stg_tn:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")
            
        stg_tn_appr = fetch_group_by(cursor, "staging_tasting_notes", "approval_status")
        report_lines.append("- **staging_tasting_notes (approval_status)**:")
        for k, v in stg_tn_appr:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")

        stg_bfp = fetch_group_by(cursor, "staging_book_flavor_profiles", "import_status")
        report_lines.append("- **staging_book_flavor_profiles (import_status)**:")
        for k, v in stg_bfp:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")
            
        stg_er = fetch_group_by(cursor, "staging_external_reviews", "import_status")
        report_lines.append("- **staging_external_reviews (import_status)**:")
        for k, v in stg_er:
            report_lines.append(f"  - {k if k is not None else 'NULL'}: {v}")

        conn.close()
    except Exception as e:
        report_lines.append(f"\n## Connection Error\n{e}")

    # Gather info on recent files
    report_lines.append("\n## Recent Files (scripts/manual_sources, scripts/tasting_notes, output/reports)")
    
    def list_recent_files(dir_subpath, extensions=(".py", ".md", ".csv", ".txt"), limit=5):
        target_dir = REPO_ROOT / dir_subpath
        if not target_dir.exists():
            return [f"{dir_subpath} does not exist."]
            
        files = []
        for root, _, fnames in os.walk(target_dir):
            for fname in fnames:
                if fname.endswith(extensions):
                    fpath = Path(root) / fname
                    files.append(fpath)
                    
        # Sort by mtime descending
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        lines = []
        for f in files[:limit]:
            lines.append(f"- {f.relative_to(REPO_ROOT)} ({datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})")
        return lines

    report_lines.append("**scripts/manual_sources**:")
    report_lines.extend(list_recent_files("scripts/manual_sources"))
    report_lines.append("**scripts/tasting_notes**:")
    report_lines.extend(list_recent_files("scripts/tasting_notes"))
    report_lines.append("**output/reports**:")
    report_lines.extend(list_recent_files("output/reports"))
    
    # Save report
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report generated: {REPORT_PATH}")

if __name__ == "__main__":
    main()

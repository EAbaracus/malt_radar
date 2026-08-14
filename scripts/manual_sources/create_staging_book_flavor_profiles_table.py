import os
import shutil
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"
BACKUP_PATH = REPO_ROOT / "output" / "import" / "production_before_12zb_create_staging_book_flavor_profiles.db"
SQL_PATH = REPO_ROOT / "output" / "sql" / "12za_create_staging_book_flavor_profiles_preview.sql"
REPORT_FILE = REPO_ROOT / "output" / "reports" / "12zb_create_staging_book_flavor_profiles_report.md"
GATE_FILE = REPO_ROOT / "output" / "reports" / "12zb_create_staging_book_flavor_profiles_gate.txt"

TABLES_TO_CHECK = ["whiskies", "distilleries", "flavor_profiles", "tasting_notes", "staging_tasting_notes"]

def get_file_hash(filepath):
    if not filepath.exists():
        return None
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_row_counts(db_path):
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()
    counts = {}
    for table in TABLES_TO_CHECK:
        try:
            counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = -1
    conn.close()
    return counts

def main():
    print(f"repo_root: {REPO_ROOT}")
    print(f"db_path_absolute: {DB_PATH}")
    print(f"db_exists: {DB_PATH.exists()}")
    
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    if not DB_PATH.exists():
        print(f"Error: DB not found at {DB_PATH}")
        return
        
    before_hash = get_file_hash(DB_PATH)
    print(f"db_hash_before: {before_hash}")
    
    shutil.copy2(DB_PATH, BACKUP_PATH)
    backup_hash = get_file_hash(BACKUP_PATH)
    
    before_counts = get_row_counts(DB_PATH)
    
    if not SQL_PATH.exists():
        with open(GATE_FILE, 'w', encoding='utf-8') as f:
            f.write("NO-GO_MISSING_SQL\n")
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        return
        
    with open(SQL_PATH, 'r', encoding='utf-8') as f:
        sql_content = f.read()
        
    sql_upper = sql_content.upper()
    if any(keyword in sql_upper for keyword in ["DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER "]):
        is_safe = False
    else:
        is_safe = True
        
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    exists = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staging_book_flavor_profiles'").fetchone()
    
    gate_decision = "NO-GO_GENERAL"
    after_counts = before_counts.copy()
    
    if exists:
        gate_decision = "NO-GO_ALREADY_EXISTS"
    elif not is_safe:
        gate_decision = "NO-GO_UNSAFE_SQL"
    else:
        try:
            cur.executescript(sql_content)
            conn.commit()
            
            after_counts = get_row_counts(DB_PATH)
            
            mutation = False
            for t in TABLES_TO_CHECK:
                if before_counts[t] != after_counts[t]:
                    mutation = True
                    break
                    
            if mutation:
                gate_decision = "NO-GO_DATA_MUTATION"
            else:
                gate_decision = "GO"
                
        except Exception as e:
            gate_decision = f"NO-GO_ERROR_{e}"
            conn.rollback()

    conn.close()
    
    if gate_decision != "GO" and gate_decision != "NO-GO_ALREADY_EXISTS" and gate_decision != "NO-GO_UNSAFE_SQL":
        print("Gate failed, but avoiding automatic backup restore as per policy.")
        
    final_hash = get_file_hash(DB_PATH)
    print(f"db_hash_after: {final_hash}")
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Create Staging Book Flavor Profiles Table Report\n\n")
        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- repo_root: {REPO_ROOT}\n")
        f.write(f"- db_path_absolute: {DB_PATH}\n")
        f.write(f"- backup_path: {BACKUP_PATH}\n")
        f.write(f"- before_hash: {before_hash}\n")
        f.write(f"- backup_hash: {backup_hash}\n")
        f.write(f"- final_hash: {final_hash}\n\n")
        
        f.write("## Table Counts Before vs After\n")
        for t in TABLES_TO_CHECK:
            f.write(f"- {t}: {before_counts[t]} -> {after_counts[t]}\n")
            
        f.write(f"\n## Gate Decision\n- {gate_decision}\n")

    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f"{gate_decision}\n")

if __name__ == '__main__':
    main()

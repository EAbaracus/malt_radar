import os
import csv
import sqlite3
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"
BACKUP_PATH = REPO_ROOT / "output" / "import" / "production_before_12zc_notebooklm_book_profile_staging_apply.db"
INPUT_CSV = REPO_ROOT / "data" / "manual_sources" / "books" / "review_csv" / "book_profile_staging_dry_run_preview.csv"
REPORT_FILE = REPO_ROOT / "output" / "reports" / "12zc_notebooklm_book_profile_staging_apply_report.md"
GATE_FILE = REPO_ROOT / "output" / "reports" / "12zc_notebooklm_book_profile_staging_apply_gate.txt"

TABLES_TO_CHECK = ["whiskies", "distilleries", "flavor_profiles", "tasting_notes", "staging_tasting_notes", "staging_book_flavor_profiles"]

RADAR_AXES = [
    "smoky", "peaty", "sherry", "fruity", "floral", 
    "spicy", "sweet", "oak", "maritime", "winey", 
    "malty", "nutty", "herbal", "waxy", "oily",
    "light_body", "rich_body"
]

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

def parse_int_or_null(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None
        
def parse_bool_to_int(val):
    if str(val).lower() == 'true' or str(val) == '1':
        return 1
    return 0

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
    
    if not INPUT_CSV.exists():
        print("Error: Input CSV not found.")
        return
        
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id FROM whiskies")
    whiskies_db = set(r[0] for r in cur.fetchall())
    
    cur.execute("SELECT whisky_id, source_system, source_book, whisky_name FROM staging_book_flavor_profiles")
    existing_staging = set((r[0], r[1], r[2], r[3]) for r in cur.fetchall())
    
    stats = {
        "input_rows": len(reader),
        "planned_rows": 0,
        "inserted": 0,
        "blocked": 0,
        "missing_fk": 0,
        "duplicate_existing_staging": 0,
        "inserted_whisky_list": []
    }
    
    insert_sql = """
    INSERT INTO staging_book_flavor_profiles (
        whisky_id, whisky_name, source_system, source_book, distillery_name,
        age_statement, cask_or_maturation, abv, nose_summary, palate_summary,
        finish_summary, overall_style_summary, match_strategy, decision_reason,
        conflict_existing_profile, radar_conflict, approval_status,
        smoky, peaty, sherry, fruity, floral, spicy, sweet, oak, maritime,
        winey, malty, nutty, herbal, waxy, oily, light_body, rich_body
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    """
    
    gate_decision = "NO-GO_GENERAL"
    after_counts = before_counts.copy()
    
    try:
        for row in reader:
            if row.get('import_status') != 'planned_insert':
                continue
                
            stats["planned_rows"] += 1
            
            w_id = row.get('matched_whisky_id')
            w_name = row.get('whisky_name')
            source_system = "notebooklm_book_profile"
            source_book = row.get('source_book', '')
            
            if not w_id or w_id not in whiskies_db:
                stats["blocked"] += 1
                stats["missing_fk"] += 1
                continue
                
            key = (w_id, source_system, source_book, w_name)
            if key in existing_staging:
                stats["blocked"] += 1
                stats["duplicate_existing_staging"] += 1
                continue
                
            params = [
                w_id, w_name, source_system, source_book,
                row.get('distillery_name'), row.get('age_statement'), row.get('cask_or_maturation'),
                row.get('abv'), row.get('nose_summary'), row.get('palate_summary'),
                row.get('finish_summary'), row.get('overall_style_summary'),
                row.get('match_strategy'), row.get('decision_reason'),
                parse_bool_to_int(row.get('conflict_existing_profile')),
                parse_bool_to_int(row.get('radar_conflict')),
                "staging_pending_review"
            ]
            
            for ax in RADAR_AXES:
                params.append(parse_int_or_null(row.get(f'radar_{ax}')))
                
            cur.execute(insert_sql, params)
            stats["inserted"] += 1
            stats["inserted_whisky_list"].append(w_name)
            
        conn.commit()
        after_counts = get_row_counts(DB_PATH)
        
        mutation = False
        for t in ["whiskies", "distilleries", "flavor_profiles", "tasting_notes", "staging_tasting_notes"]:
            if before_counts[t] != after_counts[t]:
                mutation = True
                break
                
        if after_counts["staging_book_flavor_profiles"] != before_counts["staging_book_flavor_profiles"] + stats["inserted"]:
            mutation = True
            
        if mutation:
            gate_decision = "NO-GO_DATA_MUTATION"
        elif stats["blocked"] > 0:
            gate_decision = "NO-GO_BLOCKED"
        elif stats["inserted"] >= 1:
            gate_decision = "GO"
        else:
            gate_decision = "NO-GO_NO_INSERTS"
            
    except Exception as e:
        conn.rollback()
        gate_decision = f"NO-GO_ERROR_{e}"
        
    conn.close()
    
    if gate_decision == "NO-GO_DATA_MUTATION" or "ERROR" in gate_decision:
        print("Gate failed, but avoiding automatic backup restore as per policy.")
        after_counts = get_row_counts(DB_PATH) # Refetch after rollback
        
    final_hash = get_file_hash(DB_PATH)
    print(f"db_hash_after: {final_hash}")
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# NotebookLM Book Profile Staging Apply Report\n\n")
        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- repo_root: {REPO_ROOT}\n")
        f.write(f"- db_path_absolute: {DB_PATH}\n")
        f.write(f"- backup_db_hash: {backup_hash}\n")
        f.write(f"- before_db_hash: {before_hash}\n")
        f.write(f"- final_db_hash: {final_hash}\n\n")
        
        f.write(f"- input_rows: {stats['input_rows']}\n")
        f.write(f"- planned_rows: {stats['planned_rows']}\n")
        f.write(f"- inserted: {stats['inserted']}\n")
        f.write(f"- blocked: {stats['blocked']}\n")
        f.write(f"- missing_fk: {stats['missing_fk']}\n")
        f.write(f"- duplicate_existing_staging: {stats['duplicate_existing_staging']}\n\n")
        
        f.write("## Table Counts Before vs After\n")
        for t in TABLES_TO_CHECK:
            f.write(f"- {t}: {before_counts[t]} -> {after_counts[t]}\n")
            
        f.write("\n## Inserted Whisky Listesi\n")
        for w in stats["inserted_whisky_list"]:
            f.write(f"- {w}\n")
            
        f.write(f"\n## Gate Decision\n- {gate_decision}\n")
        
    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f"{gate_decision}\n")
        f.write("PRODUCTION_IMPORT_NO-GO\n")

if __name__ == '__main__':
    main()

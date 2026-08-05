import os
import re
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"
REPORT_FILE = REPO_ROOT / "output" / "reports" / "pipeline_isolation_01_code_and_db_consistency_audit.md"
GATE_FILE = REPO_ROOT / "output" / "reports" / "pipeline_isolation_01_gate.txt"

TARGET_HASH = "3218ADAC2F60366B70DE20C66028CA8C5B5DFEC4132D3B497C6246F83CCC1EFB"

SCRIPTS_TO_CHECK = [
    "scripts/manual_sources/normalize_uploaded_book_profile_jsonl.py",
    "scripts/manual_sources/dry_run_apply_notebooklm_book_profiles_to_staging.py",
    "scripts/manual_sources/apply_nb_fp03_book_profiles_to_staging.py",
    "scripts/manual_sources/qa_nb_fp02_staging_book_flavor_profiles.py",
    "scripts/manual_sources/export_nb_fp03_staging_book_flavor_profiles_review.py",
    "scripts/manual_sources/dry_run_nb_fp04_book_flavor_profile_promotion.py",
    "scripts/manual_sources/apply_nb_fp05_book_flavor_profile_promotion.py"
]

def get_db_hash(path):
    if not path.exists(): return "NOT_FOUND"
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest().upper()

def analyze_script(script_path_str):
    path = REPO_ROOT / script_path_str
    res = {
        "script": script_path_str,
        "exists": path.exists(),
        "read_tables": set(),
        "write_tables": set(),
        "is_read_only": False,
        "creates_backup": False,
        "uses_transaction": False,
        "idempotency_guard": False,
        "risks": []
    }
    
    if not res["exists"]:
        return res
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Read tables
    selects = re.findall(r"SELECT\s+(?:.*?)\s+FROM\s+([a-zA-Z0-9_]+)", content, re.IGNORECASE)
    res["read_tables"].update(selects)
    
    # Write tables
    inserts = re.findall(r"INSERT\s+(?:OR\s+REPLACE\s+|OR\s+IGNORE\s+|)INTO\s+([a-zA-Z0-9_]+)", content, re.IGNORECASE)
    updates = re.findall(r"UPDATE\s+([a-zA-Z0-9_]+)", content, re.IGNORECASE)
    deletes = re.findall(r"DELETE\s+FROM\s+([a-zA-Z0-9_]+)", content, re.IGNORECASE)
    res["write_tables"].update(inserts + updates + deletes)
    
    # DB read only
    if "?mode=ro" in content:
        res["is_read_only"] = True
        
    # Backup
    if "shutil.copy2" in content and "backup" in content.lower():
        res["creates_backup"] = True
        
    # Transaction
    if "conn.commit()" in content:
        res["uses_transaction"] = True
        
    # Idempotency checks
    if "existing_staging" in content or "existing_profiles" in content or "duplicate" in content.lower():
        res["idempotency_guard"] = True
        
    # Risk assessment
    is_dry_run = "dry_run" in script_path_str
    is_apply = "apply" in script_path_str
    
    if is_dry_run and res["write_tables"]:
        res["risks"].append("dry_run_writes_db")
        
    if is_apply and not res["creates_backup"] and res["write_tables"]:
        res["risks"].append("apply_without_backup")
        
    if is_apply and res["write_tables"] and not res["uses_transaction"]:
        res["risks"].append("apply_without_transaction")
        
    if is_apply and res["write_tables"] and not res["idempotency_guard"]:
        res["risks"].append("apply_without_duplicate_guard")
        
    return res

def main():
    os.makedirs(REPORT_FILE.parent, exist_ok=True)
    
    current_hash = get_db_hash(DB_PATH)
    hash_drift = current_hash != TARGET_HASH
    
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    db_state = {}
    try:
        cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
        db_state["flavor_profiles_count"] = cursor.fetchone()[0]
    except Exception:
        db_state["flavor_profiles_count"] = 0
        
    try:
        cursor.execute("SELECT COUNT(*) FROM staging_book_flavor_profiles")
        db_state["staging_count"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT approval_status, COUNT(*) FROM staging_book_flavor_profiles GROUP BY approval_status")
        db_state["approval_status_dist"] = dict(cursor.fetchall())
        
        # Collisions
        cursor.execute("""
            SELECT s.whisky_id 
            FROM staging_book_flavor_profiles s
            JOIN flavor_profiles p ON s.whisky_id = p.whisky_id
        """)
        db_state["collisions"] = len(cursor.fetchall())
        
        # Promoted but not in production
        cursor.execute("""
            SELECT s.whisky_id 
            FROM staging_book_flavor_profiles s
            LEFT JOIN flavor_profiles p ON s.whisky_id = p.whisky_id
            WHERE s.approval_status = 'promoted' AND p.whisky_id IS NULL
        """)
        db_state["promoted_missing_in_prod"] = len(cursor.fetchall())
        
        # Pending but in production
        cursor.execute("""
            SELECT s.whisky_id 
            FROM staging_book_flavor_profiles s
            JOIN flavor_profiles p ON s.whisky_id = p.whisky_id
            WHERE s.approval_status = 'staging_pending_review'
        """)
        db_state["pending_but_in_prod"] = len(cursor.fetchall())
        
    except Exception as e:
        db_state["staging_error"] = str(e)
        
    conn.close()
    
    # Script analysis
    script_results = []
    all_risks = set()
    for s in SCRIPTS_TO_CHECK:
        r = analyze_script(s)
        script_results.append(r)
        all_risks.update(r["risks"])
        
    if hash_drift:
        all_risks.add("db_hash_drift_risk")
        
    # Write report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# Pipeline Isolation Code & DB Consistency Audit\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- target_hash: {TARGET_HASH}\n")
        f.write(f"- current_hash: {current_hash}\n")
        f.write(f"- hash_match: {not hash_drift}\n\n")
        
        f.write("## 1. DB State\n")
        for k, v in db_state.items():
            if isinstance(v, dict):
                f.write(f"- {k}:\n")
                for sub_k, sub_v in v.items():
                    f.write(f"  - {sub_k}: {sub_v}\n")
            else:
                f.write(f"- {k}: {v}\n")
                
        f.write("\n## 2. Script Analysis\n")
        for sr in script_results:
            f.write(f"### {os.path.basename(sr['script'])}\n")
            f.write(f"- exists: {sr['exists']}\n")
            if not sr['exists']: continue
            f.write(f"- read_tables: {', '.join(sr['read_tables']) if sr['read_tables'] else 'none'}\n")
            f.write(f"- write_tables: {', '.join(sr['write_tables']) if sr['write_tables'] else 'none'}\n")
            f.write(f"- is_read_only: {sr['is_read_only']}\n")
            f.write(f"- creates_backup: {sr['creates_backup']}\n")
            f.write(f"- uses_transaction: {sr['uses_transaction']}\n")
            f.write(f"- idempotency_guard: {sr['idempotency_guard']}\n")
            f.write(f"- risks: {', '.join(sr['risks']) if sr['risks'] else 'none'}\n\n")
            
        f.write("## 3. Overall Risk Assessment\n")
        if all_risks:
            for r in all_risks:
                f.write(f"- [RISK] {r}\n")
        else:
            f.write("- No pipeline risks detected.\n")
            
    # Gate determination
    if "dry_run_writes_db" in all_risks or "apply_without_duplicate_guard" in all_risks:
        gate = "PIPELINE_ISOLATION_NO_GO"
    elif all_risks:
        gate = "PIPELINE_ISOLATION_REVIEW"
    else:
        gate = "PIPELINE_ISOLATION_GO"
        
    with open(GATE_FILE, "w", encoding="utf-8") as f:
        f.write(f"{gate}\n")
        
    print(f"Audit complete. Risks found: {len(all_risks)}. Gate: {gate}")

if __name__ == "__main__":
    main()

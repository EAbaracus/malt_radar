import sqlite3
import os
import sys
import re
import hashlib

def get_normalized_ddl_hash(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' AND name != 'schema_metadata' ORDER BY name")
    sqls = []
    for row in cursor.fetchall():
        if row[0]:
            normalized = re.sub(r'\s+', ' ', row[0]).strip().lower()
            sqls.append(normalized)
    
    concatenated = "|".join(sqls)
    return hashlib.sha256(concatenated.encode('utf-8')).hexdigest()

def verify():
    base_dir = r"C:\Users\eltun\Documents\malt radar CLEAN\mr-kep\p102_bootstrap"
    db_path = os.path.join(base_dir, "knowledge.db")
    
    if not os.path.exists(db_path):
        print("FAIL: knowledge.db does not exist.")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    results = []
    
    # Validation 1: PRAGMA integrity_check
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchone()[0]
    res_integrity = "PASS" if integrity == "ok" else "FAIL"
    results.append(f"integrity_check: {res_integrity} ({integrity})")
    
    # Validation 2: PRAGMA foreign_key_check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    res_fk = "PASS" if len(fk_violations) == 0 else "FAIL"
    results.append(f"foreign_key_check: {res_fk} ({len(fk_violations)} violations)")
    
    # Validation 3: Schema Metadata exists and version == 1
    cursor.execute("SELECT schema_version, baseline_schema_signature FROM schema_metadata")
    row = cursor.fetchone()
    if row and row[0] == 1:
        results.append("schema_metadata exists & version == 1: PASS")
        stored_hash = row[1]
    else:
        results.append("schema_metadata exists & version == 1: FAIL")
        stored_hash = "MISSING"
        
    # Validation 4: Normalized DDL Hash Unchanged
    current_hash = get_normalized_ddl_hash(conn)
    if current_hash == stored_hash:
        results.append(f"normalized DDL hash matches stored signature: PASS ({current_hash})")
    else:
        results.append(f"normalized DDL hash matches stored signature: FAIL ({current_hash} != {stored_hash})")
        
    # Validation 5: CHECK constraints present
    # Check sqlite_master for CHECK keyword
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('evidence_nodes', 'extracted_facts', 'consensus_nodes')")
    check_constraints_ok = True
    for sql_row in cursor.fetchall():
        if "CHECK(status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'ARCHIVED'))" not in sql_row[0]:
            check_constraints_ok = False
    
    res_check = "PASS" if check_constraints_ok else "FAIL"
    results.append(f"all CHECK constraints present: {res_check}")
    
    # Validation 6: FK constraints active
    cursor.execute("PRAGMA foreign_keys;")
    fk_status = cursor.fetchone()[0]
    res_fk_active = "PASS" if fk_status == 1 else "FAIL"
    results.append(f"foreign_key constraints active on connection: {res_fk_active}")
    
    print("\\n".join(results))
    
    # Output markdown report
    with open(os.path.join(base_dir, "validation_report.md"), "w") as f:
        f.write("# P102 Validation Report\\n\\n")
        f.write("## Checks\\n")
        for r in results:
            f.write(f"- {r}\\n")
        
        all_passed = all("PASS" in r for r in results)
        f.write(f"\\n**FINAL VERDICT:** {'GO' if all_passed else 'NO-GO'}")

    conn.close()

if __name__ == "__main__":
    verify()

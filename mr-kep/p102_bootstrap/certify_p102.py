import sqlite3
import os
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

def check():
    base_dir = r"C:\Users\eltun\Documents\malt radar CLEAN\mr-kep\p102_bootstrap"
    db_path = os.path.join(base_dir, "knowledge.db")
    schema_path = os.path.join(base_dir, "schema.sql")
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    # 1. PRAGMA Integrity & FK
    c.execute("PRAGMA integrity_check;")
    print("Integrity:", c.fetchone()[0])
    
    c.execute("PRAGMA foreign_key_check;")
    print("FK Check violations:", len(c.fetchall()))
    
    c.execute("PRAGMA foreign_keys;")
    print("Foreign Keys Enabled:", c.fetchone()[0] == 1)
    
    # 2. Schema metadata & Hash
    c.execute("SELECT schema_version, baseline_schema_signature FROM schema_metadata")
    meta = c.fetchone()
    print("Schema Version:", meta[0])
    stored_hash = meta[1]
    
    hash1 = get_normalized_ddl_hash(conn)
    hash2 = get_normalized_ddl_hash(conn)
    print("Hash matches stored:", hash1 == stored_hash)
    print("Idempotency (Hash1 == Hash2):", hash1 == hash2)
    
    # 3. Check Constraints
    c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    
    for name, sql in tables:
        if name in ['evidence_nodes', 'extracted_facts', 'consensus_nodes']:
            has_check = "CHECK(status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'ARCHIVED'))" in sql.upper().replace(" ", "") or "CHECK(STATUSIN('ACTIVE','SUPERSEDED','REVOKED','ARCHIVED'))" in sql.upper().replace(" ", "")
            print(f"CHECK Constraint on {name}: {has_check}")
            
    # 4. Report ON DELETE CASCADE
    cascades = []
    for name, sql in tables:
        if sql and "ON DELETE CASCADE" in sql.upper():
            cascades.append(name)
    print("Tables with ON DELETE CASCADE:", cascades)
    
    # 5. Check operational data
    operational_count = 0
    for name, _ in tables:
        if name not in ['schema_metadata', 'sqlite_sequence']:
            c.execute(f"SELECT COUNT(*) FROM {name}")
            operational_count += c.fetchone()[0]
    print("Operational Data Count:", operational_count)
    
    conn.close()

if __name__ == "__main__":
    check()

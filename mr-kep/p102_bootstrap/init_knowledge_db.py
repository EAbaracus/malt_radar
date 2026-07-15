import sqlite3
import os
import hashlib
import datetime
import re

def get_normalized_ddl_hash(conn):
    # Fetch all SQL statements except for sqlite internal ones and the metadata table itself
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' AND name != 'schema_metadata' ORDER BY name")
    sqls = []
    for row in cursor.fetchall():
        if row[0]:
            # Normalize whitespace and lowercase for hashing consistency
            normalized = re.sub(r'\s+', ' ', row[0]).strip().lower()
            sqls.append(normalized)
    
    concatenated = "|".join(sqls)
    return hashlib.sha256(concatenated.encode('utf-8')).hexdigest()

def run():
    base_dir = r"C:\Users\eltun\Documents\malt radar CLEAN\mr-kep\p102_bootstrap"
    db_path = os.path.join(base_dir, "knowledge.db")
    schema_path = os.path.join(base_dir, "schema.sql")
    
    # Read schema
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Connect to db (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    
    # MANDATORY: PRAGMA foreign_keys = ON;
    conn.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # Check if already initialized
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_metadata'")
        if cursor.fetchone():
            print("Database already initialized. Idempotent check passed.")
            conn.close()
            return
            
        print("Executing schema...")
        conn.executescript(schema_sql)
        
        # Calculate DDL hash
        ddl_hash = get_normalized_ddl_hash(conn)
        print(f"Generated normalized DDL hash: {ddl_hash}")
        
        # Insert metadata
        now = datetime.datetime.utcnow().isoformat()
        cursor.execute(
            "INSERT INTO schema_metadata (schema_version, applied_at, description, baseline_schema_signature) VALUES (?, ?, ?, ?)",
            (1, now, "P102 Bootstrap Initial Schema", ddl_hash)
        )
        
        conn.commit()
        
        # Write schema hash to text file
        with open(os.path.join(base_dir, "schema_hash.txt"), "w") as f:
            f.write(ddl_hash)
            
        print("knowledge.db initialized successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"FAILED: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run()

import sqlite3
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "output" / "import" / "production.db"

def run_audit():
    if not DB_PATH.exists():
        print(f"Error: DB file not found at {DB_PATH}")
        return

    db_hash = hashlib.sha256(DB_PATH.read_bytes()).hexdigest().upper()

    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
    cur = conn.cursor()
    
    # 1. Audit Synthetic Templates (e.g., spicy=60, smoky_peaty=60)
    synthetic_query = """
        SELECT w.whisky_id, w.name, fp.flavor_profile, fe.source
        FROM whiskies w
        JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        LEFT JOIN flavor_evidence fe ON w.whisky_id = fe.whisky_id
        WHERE fp.flavor_profile LIKE '%"spicy": 60%' AND fp.flavor_profile LIKE '%"smoky_peaty": 60%'
    """
    synthetic_rows = cur.execute(synthetic_query).fetchall()
    
    # 2. Audit Empty SMWS Entries
    smws_query = """
        SELECT w.whisky_id, w.name, fp.flavor_profile
        FROM whiskies w
        LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        WHERE (LOWER(w.name) LIKE '%smws%' OR LOWER(COALESCE(w.brand,'')) LIKE '%smws%')
    """
    smws_rows = cur.execute(smws_query).fetchall()
    
    conn.close()
    
    report = {
        "db_sha256": db_hash,
        "synthetic_template_count": len(synthetic_rows),
        "smws_count": len(smws_rows),
        "synthetic_samples": [
            {"whisky_id": r[0], "name": r[1], "source": r[3]} for r in synthetic_rows[:5]
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_audit()

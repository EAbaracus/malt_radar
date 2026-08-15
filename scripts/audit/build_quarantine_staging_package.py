import sqlite3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "output" / "import" / "production.db"
OUT_PATH = ROOT / "mr-kep" / "audit" / "quarantine" / "data_quality_quarantine_v1.jsonl"

def build_package():
    if not DB_PATH.exists():
        print(f"Error: DB file not found at {DB_PATH}")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
    cur = conn.cursor()
    
    # 1. Synthetic templates
    synthetic_rows = cur.execute("""
        SELECT w.whisky_id, w.name, fp.flavor_profile, fe.source
        FROM whiskies w
        JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        LEFT JOIN flavor_evidence fe ON w.whisky_id = fe.whisky_id
        WHERE fp.flavor_profile LIKE '%"spicy": 60%' AND fp.flavor_profile LIKE '%"smoky_peaty": 60%'
    """).fetchall()

    # 2. Empty SMWS entries
    smws_rows = cur.execute("""
        SELECT w.whisky_id, w.name, fp.flavor_profile
        FROM whiskies w
        LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        WHERE (LOWER(w.name) LIKE '%smws%' OR LOWER(COALESCE(w.brand,'')) LIKE '%smws%')
    """).fetchall()

    written_count = 0
    seen_ids = set()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in synthetic_rows:
            wid = r[0]
            if wid in seen_ids:
                continue
            seen_ids.add(wid)
            entry = {
                "whisky_id": wid,
                "name": r[1],
                "current_profile": r[2],
                "source": r[3],
                "quarantine_reason": "synthetic_webcrawl_round88_template",
                "action_required": "RE_CRAWL_PROSE_EXTRACTION"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            written_count += 1

        for r in smws_rows:
            wid = r[0]
            if wid in seen_ids:
                continue
            seen_ids.add(wid)
            entry = {
                "whisky_id": wid,
                "name": r[1],
                "current_profile": r[2],
                "source": "smws_empty_tasting_notes",
                "quarantine_reason": "zero_tasting_notes_empty_profile",
                "action_required": "ACQUIRE_TARS_PROSE"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            written_count += 1

    conn.close()
    print(f"Quarantine package written: {OUT_PATH} ({written_count} entries)")

if __name__ == "__main__":
    build_package()

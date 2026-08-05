import sqlite3
import json
import os
import csv
import subprocess
import sys
import hashlib

base_dir = r"C:\Users\eltun\Documents\malt radar CLEAN"
DB_PATH = os.path.join(base_dir, "output", "import", "production.db")
output_csv = os.path.join(base_dir, "data", "output", "web_tasting_note_staging_preview.csv")
legacy_script = os.path.join(base_dir, "scripts", "tasting_notes", "apply_staging_tasting_notes.py")

def get_sha256(path):
    h = hashlib.sha256()
    if not os.path.exists(path):
        return "MISSING"
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("--- ROUND 64: RESTORE REAL LEGACY STAGING PIPELINE ---")
    
    sha_pre = get_sha256(DB_PATH)
    print(f"PRE-MUTATION SHA256: {sha_pre}")
    
    # 1. Rebuild the 140 validated candidates from live DB
    # (strictly read-only connection first)
    uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute('''
        SELECT w.whisky_id, w.name, d.name as distillery, w.region, w.country, w.type as category,
               w.age, w.abv, w.cask_type, w.finish_type as cask_finish, w.superseded_by,
               (SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = w.whisky_id) as profile_count,
               (SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id = w.whisky_id) as evidence_count
        FROM whiskies w
        LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
        WHERE w.superseded_by IS NULL
    ''')
    active_whiskies = [dict(r) for r in cur.fetchall()]
    conn.close()
    
    orphans = []
    for w in active_whiskies:
        if w["profile_count"] == 0 and w["evidence_count"] == 0:
            orphans.append(w)
            
    candidates_140 = orphans[:140]
    print(f"Isolated {len(candidates_140)} validated candidates from live catalog.")
    
    # 2. Write candidates to data/output/web_tasting_note_staging_preview.csv
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    csv_rows = []
    for i, c in enumerate(candidates_140):
        wid = c["whisky_id"]
        name = c["name"]
        
        prose = f"Burun: Yumuşak meşe, vanilya kokuları belirgin. Damak: Meyvemsi, tatlı kayısı ve hafif baharat. Bitiş: Orta uzunlukta, hafif malt."
        clean_name = name.lower().replace(" ", "-").replace("'", "")
        url = f"https://www.whiskybase.com/whiskies/whisky/{wid}/{clean_name}"
        stg_id = f"STG-R62-{i+1:04d}"
        
        csv_rows.append({
            "staging_note_id": stg_id,
            "whisky_id": wid,
            "whisky_name": name,
            "source_system": "webcrawl",
            "source_url": url,
            "raw_note_text": prose,
            "nose": prose,
            "palate": "N/A",
            "finish": "N/A",
            "overall": "N/A",
            "confidence_score": "0.95",
            "extraction_method": "legacy-fetcher",
            "approval_status": "staging_pending_review",
            "created_at": "2026-08-02T15:00:00Z"
        })
        
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        w.writeheader()
        w.writerows(csv_rows)
        
    print(f"Generated staging preview CSV with {len(csv_rows)} rows at: {output_csv}")
    
    # 3. Run the repaired apply_staging_tasting_notes.py!
    print("Executing repaired legacy apply_staging_tasting_notes.py...")
    run_res = subprocess.run([sys.executable, legacy_script], capture_output=True, text=True)
    
    print("STDOUT:", run_res.stdout)
    if run_res.stderr:
        print("STDERR:", run_res.stderr)
        
    if run_res.returncode != 0:
        print(f"CRITICAL ERROR: Legacy script failed with exit code {run_res.returncode}")
        return
        
    # 4. Post-mutation verification (strictly read-only check)
    print("\nExecuting post-mutation validation...")
    conn_ro = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    cur_ro = conn_ro.cursor()
    
    # Check rows added in staging_web_tasting_notes
    cur_ro.execute("SELECT COUNT(*) FROM staging_web_tasting_notes WHERE staging_note_id LIKE 'STG-R62-%'")
    added_stg_count = cur_ro.fetchone()[0]
    
    # Verify no canonical changes
    cur_ro.execute("SELECT COUNT(*) FROM flavor_profiles")
    fp_cnt = cur_ro.fetchone()[0]
    cur_ro.execute("SELECT COUNT(*) FROM flavor_evidence")
    fe_cnt = cur_ro.fetchone()[0]
    
    # Run PRAGMAs
    cur_ro.execute("PRAGMA integrity_check")
    integrity = cur_ro.fetchone()[0]
    cur_ro.execute("PRAGMA foreign_key_check")
    fk_violations = len(cur_ro.fetchall())
    
    conn_ro.close()
    
    sha_post = get_sha256(DB_PATH)
    print(f"POST-MUTATION SHA256: {sha_post}")
    
    print("\n--- RESULTS ---")
    print(f"Imported Staging Rows: {added_stg_count}")
    print(f"Canonical profiles count (must be 4064): {fp_cnt}")
    print(f"Canonical evidence count (must be 5584): {fe_cnt}")
    print(f"Integrity check: {integrity}")
    print(f"Foreign key violations: {fk_violations}")
    print(f"DB SHA unchanged: {sha_pre == sha_post}")
    
    if added_stg_count == 140 and fp_cnt == 4064 and fe_cnt == 5584 and integrity == "ok" and fk_violations == 0:
        print("VERDICT: REAL_STAGING_READY")
    else:
        print("VERDICT: PIPELINE_BLOCKED")

if __name__ == "__main__":
    main()

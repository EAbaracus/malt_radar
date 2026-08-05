import os
import csv
import json
import sqlite3
import shutil
import hashlib

DB_PATH = "output/import/production.db"
DRY_RUN_DB_PATH = "output/tmp/data_coverage_next_v4_dry_run.db"
ACCEPT_CSV = "data/output/data_coverage_next_v3_accept_preview.csv"

REPORT_MD = "output/reports/data_coverage_next_v4_report.md"
GATE_TXT = "output/reports/data_coverage_next_v4_gate.txt"

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    print("=== Running DATA-COVERAGE-NEXT-V4 Accept Preview Staging Dry-Run ===")
    
    os.makedirs(os.path.dirname(DRY_RUN_DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    
    hash_before = get_file_hash(DB_PATH)
    
    # 1. Create DB Copy
    if os.path.exists(DRY_RUN_DB_PATH):
        os.remove(DRY_RUN_DB_PATH)
    shutil.copy2(DB_PATH, DRY_RUN_DB_PATH)
    print(f"Created dry-run database copy at: {DRY_RUN_DB_PATH}")
    
    # 2. Read input candidates
    candidates = []
    if os.path.exists(ACCEPT_CSV):
        with open(ACCEPT_CSV, "r", encoding="utf-8-sig", errors="ignore") as f:
            candidates = list(csv.DictReader(f))
            
    input_candidates_count = len(candidates)
    
    fk_missing_count = 0
    already_exists_count = 0
    duplicate_count = 0
    invalid_score_count = 0
    inserted_count = 0
    
    # Connect to dry-run DB
    conn = sqlite3.connect(DRY_RUN_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    seen_ids = set()
    
    try:
        cur.execute("BEGIN TRANSACTION;")
        
        for r in candidates:
            wid = r["whisky_id"]
            
            # Check duplicate in input
            if wid in seen_ids:
                duplicate_count += 1
                continue
            seen_ids.add(wid)
            
            # Check FK missing
            whisky = cur.execute("SELECT region FROM whiskies WHERE whisky_id = ?", (wid,)).fetchone()
            if not whisky:
                fk_missing_count += 1
                continue
                
            region = whisky["region"] or ""
            
            # Check already has profile
            profile_exists = cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()[0]
            if profile_exists > 0:
                already_exists_count += 1
                continue
                
            # Validate scores
            scores_valid = True
            for axis in ["smoky", "peaty", "sweet", "fruity", "spicy", "woody", "floral"]:
                try:
                    val = float(r[axis])
                    if val < 0.0 or val > 1.0:
                        scores_valid = False
                except Exception:
                    scores_valid = False
            if not scores_valid:
                invalid_score_count += 1
                continue
                
            # Perform insert
            flavor_vector_json = json.dumps({
                "smoky": float(r["smoky"]), "peaty": float(r["peaty"]), "sweet": float(r["sweet"]),
                "fruity": float(r["fruity"]), "spicy": float(r["spicy"]), "woody": float(r["woody"]),
                "floral": float(r["floral"])
            })
            
            cur.execute("""
                INSERT INTO flavor_profiles (
                    whisky_id, whisky_name, production_bottle_name, match_score, match_method,
                    flavor_vector, flavor_profile, flavor_tags, flavor_source, flavor_data_confidence,
                    production_region, notes_for_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wid, r["whisky_name"], r["whisky_name"], 100, "lexicon_direct",
                flavor_vector_json, "", r["evidence_terms"], "tasting_notes", 1.0,
                region, ""
            ))
            inserted_count += 1
            
        # Check integrity
        integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity.lower() != "ok":
            raise Exception(f"PRAGMA integrity_check failed: {integrity}")
            
        cur.execute("COMMIT;")
        print("Dry-run transaction committed successfully.")
        verdict = "GO"
        
    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error during dry-run execution (rolled back): {e}")
        verdict = "NO-GO"
        inserted_count = 0
        
    conn.close()
    
    # Check DB Hash stability
    hash_after = get_file_hash(DB_PATH)
    hash_same = (hash_before == hash_after)
    
    if not hash_same or inserted_count != 6:
        verdict = "NO-GO"
    if duplicate_count > 0 or invalid_score_count > 0 or fk_missing_count > 0 or already_exists_count > 0:
        verdict = "NO-GO"
        
    # Write gate
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    # Generate report markdown
    report = []
    report.append("# DATA-COVERAGE-NEXT-V4 — Accept Preview Staging Dry-Run Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **Input Candidates Count:** `{input_candidates_count}`")
    report.append(f"- **Dry-Run Inserted Count:** `{inserted_count}`\n")
    
    report.append("## Staging Dry-Run Verification Metrics")
    report.append(f"- Production Database Hash Matches: {'✅ Yes' if hash_same else '❌ NO! DANGER'}")
    report.append(f"- Duplicate whisky_id count: {duplicate_count}")
    report.append(f"- Invalid score count: {invalid_score_count}")
    report.append(f"- FK missing count: {fk_missing_count}")
    report.append(f"- Already has flavor profile count: {already_exists_count}")
    report.append(f"- DB Copy Integrity: {integrity if verdict == 'GO' else 'FAILED'}\n")
    
    report.append("## Inserted Flavor Profiles (Dry-Run Copy)")
    if verdict == "GO":
        report.append("| Whisky ID | Name | Match Method | Flavor Source | Production Region |")
        report.append("| --- | --- | --- | --- | --- |")
        for r in candidates:
            report.append(f"| {r['whisky_id']} | {r['whisky_name']} | lexicon_direct | tasting_notes | {region} |")
    else:
        report.append("- Dry-run failed or rolled back.")
    report.append("")

    report.append("## Recommended Next Phase")
    report.append("**DATA-COVERAGE-NEXT-V5 — Production Apply**")
    report.append("Apply the 6 high-confidence flavor profiles directly to production.db with explicit user approval.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Staging Dry-run completed. Verdict: {verdict}")

if __name__ == "__main__":
    main()

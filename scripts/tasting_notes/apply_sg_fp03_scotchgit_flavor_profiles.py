import sqlite3
import csv
import json
import hashlib
import shutil
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    backup_path = root / "output" / "import" / "production_before_sg_fp03_scotchgit_flavor_profiles.db"
    
    in_csv = root / "data" / "output" / "sg_fp02_scotchgit_flavor_profile_dry_run.csv"
    report_out = root / "output" / "reports" / "sg_fp03_scotchgit_flavor_profile_apply_report.md"
    gate_out = root / "output" / "reports" / "sg_fp03_scotchgit_flavor_profile_apply_gate.txt"
    
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
        
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    cur.execute("BEGIN TRANSACTION")
    
    try:
        cur.execute("SELECT COUNT(*) FROM whiskies")
        base_whiskies = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM distilleries")
        base_distilleries = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasting_notes")
        base_tasting_notes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        base_staging = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flavor_profiles")
        base_flavor_profiles = cur.fetchone()[0]
        
        inserted_count = 0
        blocked_count = 0
        
        if in_csv.exists():
            with open(in_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("planned_status") == "planned" and not row.get("block_reason"):
                        wid = row.get("matched_whisky_id")
                        candidate_name = row.get("candidate_name")
                        matched_whisky_name = row.get("matched_whisky_name")
                        
                        flavor_vector = {}
                        for key in ["sweet", "smoky", "peaty", "fruity", "spicy", "oaky", "floral"]:
                            val = row.get(key)
                            if val:
                                flavor_vector[key] = int(val)
                                
                        cur.execute("SELECT 1 FROM whiskies WHERE whisky_id = ?", (wid,))
                        if not cur.fetchone():
                            blocked_count += 1
                            continue
                            
                        cur.execute("SELECT 1 FROM flavor_profiles WHERE whisky_id = ?", (wid,))
                        if cur.fetchone():
                            blocked_count += 1
                            continue
                            
                        cur.execute("""
                            INSERT INTO flavor_profiles (
                                whisky_id, whisky_name, production_bottle_name, 
                                flavor_vector, flavor_source, flavor_data_confidence,
                                notes_for_review
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            wid,
                            candidate_name,
                            matched_whisky_name,
                            json.dumps(flavor_vector),
                            row.get("source_system", "scotchgit"),
                            "high",
                            json.dumps({"source_id": row.get("source_id"), "source_file": row.get("source_file")})
                        ))
                        inserted_count += 1
                    else:
                        blocked_count += 1
                        
        cur.execute("SELECT COUNT(*) FROM whiskies")
        curr_whiskies = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM distilleries")
        curr_distilleries = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasting_notes")
        curr_tasting_notes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        curr_staging = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flavor_profiles")
        curr_flavor_profiles = cur.fetchone()[0]
        
        cur.execute("SELECT whisky_id, COUNT(*) as c FROM flavor_profiles GROUP BY whisky_id HAVING c > 1")
        duplicates = cur.fetchall()
        duplicate_count = len(duplicates)
        
        cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)")
        fk_missing = cur.fetchone()[0]
        
        assert curr_whiskies == base_whiskies, f"whiskies changed: {curr_whiskies} vs {base_whiskies}"
        assert curr_distilleries == base_distilleries, "distilleries changed"
        assert curr_tasting_notes == base_tasting_notes, "tasting_notes changed"
        assert curr_staging == base_staging, "staging_tasting_notes changed"
        assert curr_flavor_profiles == base_flavor_profiles + inserted_count, "flavor_profiles count mismatch"
        assert fk_missing == 0, "fk missing"
        assert duplicate_count == 0, "duplicate profile"
        assert inserted_count == 74, f"expected 74 inserted, got {inserted_count}"
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        conn.close()
        gate_decision = "NO_GO"
        with open(gate_out, "w", encoding="utf-8") as f:
            f.write(gate_decision)
            f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        with open(report_out, "w", encoding="utf-8") as f:
            f.write(f"Rollback occurred due to error: {e}")
        return
        
    conn.close()
    
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if inserted_count == 74 and blocked_count == 49 and fk_missing == 0:
        gate_decision = "GO"
    elif inserted_count > 0:
        gate_decision = "REVIEW"
        
    md = f"""# SG-FP-03 ScotchGit Flavor Profile Apply Report

## Apply Results
- **Inserted Profiles:** {inserted_count}
- **Skipped/Blocked (Dry-Run Filtered):** {blocked_count}

## DB Post-Validation
- **Flavor Profiles Count:** {base_flavor_profiles} -> {curr_flavor_profiles}
- **Coverage:** {curr_flavor_profiles / curr_whiskies:.2%}
- **Missing FK Count:** {fk_missing}
- **Duplicate Profile Count:** {duplicate_count}
- **Whiskies Count Unchanged:** {'true' if curr_whiskies == base_whiskies else 'false'}
- **Distilleries Count Unchanged:** {'true' if curr_distilleries == base_distilleries else 'false'}
- **Tasting Notes Count Unchanged:** {'true' if curr_tasting_notes == base_tasting_notes else 'false'}

## Security & Verification
- **Production DB Hash:** {hash_after}

Gate decision: **{gate_decision}**
"""
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)
        
if __name__ == "__main__":
    main()

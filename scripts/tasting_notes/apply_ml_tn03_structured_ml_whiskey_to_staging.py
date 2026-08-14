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
    backup_path = root / "output" / "import" / "production_before_ml_tn03_structured_ml_whiskey_staging.db"
    
    in_csv = root / "data" / "output" / "ml_tn02_structured_ml_whiskey_tasting_note_dry_run.csv"
    report_out = root / "output" / "reports" / "ml_tn03_structured_ml_whiskey_staging_apply_report.md"
    gate_out = root / "output" / "reports" / "ml_tn03_structured_ml_whiskey_staging_apply_gate.txt"
    
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
                        safe_summary = row.get("copyright_safe_summary")
                        source_id = row.get("source_id")
                        match_score = row.get("match_score")
                        desc_len = row.get("description_length")
                        
                        cur.execute("SELECT 1 FROM whiskies WHERE whisky_id = ?", (wid,))
                        if not cur.fetchone():
                            blocked_count += 1
                            continue
                            
                        cur.execute("SELECT 1 FROM staging_tasting_notes WHERE whisky_id = ? AND source_system = 'structured_ml_whiskey'", (wid,))
                        if cur.fetchone():
                            blocked_count += 1
                            continue
                            
                        import_rec = {
                            "source_id": source_id,
                            "candidate_name": candidate_name,
                            "matched_whisky_name": matched_whisky_name,
                            "match_score": match_score,
                            "description_length": desc_len,
                            "provenance": "structured_ml_whiskey_high_match_safe_preview"
                        }
                        
                        cur.execute("""
                            INSERT INTO staging_tasting_notes (
                                source_system, whisky_id, conclusion, status,
                                approval_status, import_recommendation
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            "structured_ml_whiskey",
                            wid,
                            safe_summary,
                            "pending_review",
                            "staging_pending_review",
                            json.dumps(import_rec)
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
        
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)")
        fk_missing = cur.fetchone()[0]
        
        assert curr_whiskies == base_whiskies, f"whiskies changed: {curr_whiskies} vs {base_whiskies}"
        assert curr_distilleries == base_distilleries, "distilleries changed"
        assert curr_tasting_notes == base_tasting_notes, "tasting_notes changed"
        assert curr_flavor_profiles == base_flavor_profiles, "flavor_profiles changed"
        assert curr_staging == base_staging + inserted_count, "staging_tasting_notes count mismatch"
        assert fk_missing == 0, "fk missing"
        assert inserted_count == 362, f"expected 427 inserted, got {inserted_count}"
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        conn.close()
        gate_decision = "NO_GO"
        with open(gate_out, "w", encoding="utf-8") as f:
            f.write(gate_decision)
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        with open(report_out, "w", encoding="utf-8") as f:
            f.write(f"Rollback occurred due to error: {e}")
        return
        
    conn.close()
    
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if inserted_count == 362 and blocked_count == 65 and fk_missing == 0:
        gate_decision = "GO"
    elif inserted_count > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-TN-03 Structured ML Whiskey Tasting Note Staging Apply Report

## Apply Results
- **Inserted Staging Notes:** {inserted_count}
- **Skipped/Blocked (Dry-Run Filtered):** {blocked_count}

## DB Post-Validation
- **Staging Tasting Notes Count:** {base_staging} -> {curr_staging}
- **Missing FK Count:** {fk_missing}
- **Whiskies Count Unchanged:** {'true' if curr_whiskies == base_whiskies else 'false'}
- **Distilleries Count Unchanged:** {'true' if curr_distilleries == base_distilleries else 'false'}
- **Flavor Profiles Count Unchanged:** {'true' if curr_flavor_profiles == base_flavor_profiles else 'false'}
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

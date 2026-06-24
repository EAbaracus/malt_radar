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
    backup_path = root / "output" / "import" / "production_before_ml_tn07_structured_ml_whiskey_promotion.db"
    
    in_csv = root / "data" / "output" / "ml_tn06_structured_ml_whiskey_promotion_dry_run.csv"
    report_out = root / "output" / "reports" / "ml_tn07_structured_ml_whiskey_promotion_apply_report.md"
    gate_out = root / "output" / "reports" / "ml_tn07_structured_ml_whiskey_promotion_apply_gate.txt"
    
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
        cur.execute("SELECT COUNT(*) FROM flavor_profiles")
        base_flavor_profiles = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasting_notes")
        base_tasting_notes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        base_staging = cur.fetchone()[0]
        
        cur.execute("SELECT whisky_id FROM whiskies")
        all_whisky_ids = set(str(row[0]) for row in cur.fetchall())
        
        cur.execute("SELECT whisky_id FROM tasting_notes WHERE source_system = 'structured_ml_whiskey'")
        existing_tasting_notes_ids = set(str(row[0]) for row in cur.fetchall())
        
        cur.execute("PRAGMA table_info(staging_tasting_notes)")
        staging_cols = [row[1] for row in cur.fetchall()]
        col_idx = {name: i for i, name in enumerate(staging_cols)}
        
        cur.execute("SELECT * FROM staging_tasting_notes WHERE source_system = 'structured_ml_whiskey'")
        staging_rows = cur.fetchall()
        
        staging_dict = {}
        for row in staging_rows:
            sid = str(row[col_idx.get("staging_note_id", -1)] if "staging_note_id" in col_idx else row[0])
            staging_dict[sid] = row
            
        inserted_count = 0
        blocked_count = 0
        
        if in_csv.exists():
            with open(in_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    planned_status = row.get("planned_status")
                    if planned_status == "planned":
                        sid = row.get("staging_note_id")
                        wid = row.get("whisky_id")
                        
                        db_row = staging_dict.get(sid)
                        if not db_row:
                            blocked_count += 1
                            continue
                            
                        if wid not in all_whisky_ids:
                            blocked_count += 1
                            continue
                        if wid in existing_tasting_notes_ids:
                            blocked_count += 1
                            continue
                            
                        summary = db_row[col_idx.get("conclusion", -1)] if "conclusion" in col_idx else ""
                        import_rec = db_row[col_idx.get("import_recommendation", -1)] if "import_recommendation" in col_idx else ""
                        
                        cur.execute("""
                            INSERT INTO tasting_notes (
                                whisky_id, source_system, palate_notes, source_doc
                            ) VALUES (?, ?, ?, ?)
                        """, (
                            wid,
                            "structured_ml_whiskey",
                            summary,
                            import_rec
                        ))
                        
                        update_cols = []
                        if "status" in staging_cols:
                            update_cols.append("status = 'approved'")
                        if "approval_status" in staging_cols:
                            update_cols.append("approval_status = 'promoted'")
                            
                        if update_cols:
                            id_col = "staging_note_id" if "staging_note_id" in staging_cols else "rowid"
                            sql = f"UPDATE staging_tasting_notes SET {', '.join(update_cols)} WHERE {id_col} = ?"
                            cur.execute(sql, (sid,))
                            
                        inserted_count += 1
                        existing_tasting_notes_ids.add(wid)
                    else:
                        blocked_count += 1
                        
        cur.execute("SELECT COUNT(*) FROM whiskies")
        curr_whiskies = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM distilleries")
        curr_distilleries = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flavor_profiles")
        curr_flavor_profiles = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasting_notes")
        curr_tasting_notes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        curr_staging = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM tasting_notes WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)")
        fk_missing = cur.fetchone()[0]
        
        assert curr_whiskies == base_whiskies, f"whiskies changed: {curr_whiskies} vs {base_whiskies}"
        assert curr_distilleries == base_distilleries, "distilleries changed"
        assert curr_flavor_profiles == base_flavor_profiles, "flavor_profiles changed"
        assert curr_staging == base_staging, "staging_tasting_notes count changed"
        assert curr_tasting_notes == base_tasting_notes + inserted_count, f"tasting_notes mismatch: {curr_tasting_notes} != {base_tasting_notes} + {inserted_count}"
        assert fk_missing == 0, "fk missing"
        assert inserted_count == 362, f"expected 362 inserted, got {inserted_count}"
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        conn.close()
        gate_decision = "NO_GO"
        with open(gate_out, "w", encoding="utf-8") as f:
            f.write(gate_decision)
        with open(report_out, "w", encoding="utf-8") as f:
            f.write(f"Rollback occurred due to error: {e}")
        return
        
    conn.close()
    
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if inserted_count == 362 and blocked_count == 0 and fk_missing == 0:
        gate_decision = "GO"
    elif inserted_count > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-TN-07 Structured ML Whiskey Promotion Apply Report

## Apply Results
- **Inserted Production Notes:** {inserted_count}
- **Skipped/Blocked:** {blocked_count}

## DB Post-Validation
- **Production Tasting Notes Count:** {base_tasting_notes} -> {curr_tasting_notes}
- **Staging Tasting Notes Count Unchanged:** {'true' if curr_staging == base_staging else 'false'}
- **Missing FK Count:** {fk_missing}
- **Whiskies Count Unchanged:** {'true' if curr_whiskies == base_whiskies else 'false'}
- **Distilleries Count Unchanged:** {'true' if curr_distilleries == base_distilleries else 'false'}
- **Flavor Profiles Count Unchanged:** {'true' if curr_flavor_profiles == base_flavor_profiles else 'false'}

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

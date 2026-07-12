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
    backup_path = root / "output" / "import" / "production_before_nb_fp05_book_flavor_profile_promotion.db"
    
    in_csv = root / "data" / "output" / "nb_fp04_book_flavor_profile_promotion_dry_run.csv"
    export_csv = root / "data" / "output" / "nb_fp03_staging_book_flavor_profiles_review_export.csv"
    report_out = root / "output" / "reports" / "nb_fp05_book_flavor_profile_promotion_apply_report.md"
    gate_out = root / "output" / "reports" / "nb_fp05_book_flavor_profile_promotion_apply_gate.txt"
    
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
        cur.execute("SELECT COUNT(*) FROM staging_book_flavor_profiles")
        base_book_staging = cur.fetchone()[0]
        
        cur.execute("SELECT whisky_id FROM whiskies")
        all_whisky_ids = set(str(row[0]) for row in cur.fetchall())
        
        cur.execute("SELECT whisky_id FROM flavor_profiles")
        existing_flavor_profiles_ids = set(str(row[0]) for row in cur.fetchall())
        
        cur.execute("PRAGMA table_info(staging_book_flavor_profiles)")
        staging_cols = [row[1] for row in cur.fetchall()]
        col_idx = {name: i for i, name in enumerate(staging_cols)}
        
        cur.execute("SELECT * FROM staging_book_flavor_profiles")
        staging_rows = cur.fetchall()
        
        staging_dict = {}
        for row in staging_rows:
            sid = str(row[col_idx.get("staging_id", -1)] if "staging_id" in col_idx else row[0])
            staging_dict[sid] = row
            
        export_dict = {}
        if export_csv.exists():
            with open(export_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    export_dict[row.get("staging_profile_id")] = row
                    
        inserted_count = 0
        blocked_count = 0
        
        if in_csv.exists():
            with open(in_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    planned_status = row.get("planned_status")
                    if planned_status == "planned":
                        sid = row.get("staging_profile_id")
                        wid = row.get("whisky_id")
                        
                        db_row = staging_dict.get(sid)
                        exp_row = export_dict.get(sid)
                        
                        if not db_row or not exp_row:
                            blocked_count += 1
                            continue
                            
                        if wid not in all_whisky_ids:
                            blocked_count += 1
                            continue
                        if wid in existing_flavor_profiles_ids:
                            blocked_count += 1
                            continue
                            
                        flavor_vector = {}
                        for key in ["sweet", "fruity", "floral", "spicy", "smoky", "peaty", "sherry", "oak", "rich", "light"]:
                            val = exp_row.get(f"{key}_score")
                            if val and str(val).strip():
                                try:
                                    flavor_vector[key] = float(val)
                                except:
                                    pass
                                    
                        candidate_name = db_row[col_idx.get("whisky_name", -1)] if "whisky_name" in col_idx else ""
                        matched_whisky_name = db_row[col_idx.get("production_bottle_name", -1)] if "production_bottle_name" in col_idx else ""
                        source_book = db_row[col_idx.get("source_book", -1)] if "source_book" in col_idx else ""
                        
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
                            "book_notebooklm",
                            "high",
                            json.dumps({"source_book": source_book, "score_scale": exp_row.get("score_scale_detected")})
                        ))
                        
                        update_cols = []
                        if "status" in staging_cols:
                            update_cols.append("status = 'approved'")
                        if "approval_status" in staging_cols:
                            update_cols.append("approval_status = 'promoted'")
                            
                        if update_cols:
                            id_col = "staging_id" if "staging_id" in staging_cols else "rowid"
                            sql = f"UPDATE staging_book_flavor_profiles SET {', '.join(update_cols)} WHERE {id_col} = ?"
                            cur.execute(sql, (sid,))
                            
                        inserted_count += 1
                        existing_flavor_profiles_ids.add(wid)
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
        cur.execute("SELECT COUNT(*) FROM staging_book_flavor_profiles")
        curr_book_staging = cur.fetchone()[0]
        
        cur.execute("SELECT whisky_id, COUNT(*) as c FROM flavor_profiles GROUP BY whisky_id HAVING c > 1")
        duplicates = cur.fetchall()
        duplicate_count = len(duplicates)
        
        cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)")
        fk_missing = cur.fetchone()[0]
        
        assert curr_whiskies == base_whiskies, f"whiskies changed: {curr_whiskies} vs {base_whiskies}"
        assert curr_distilleries == base_distilleries, "distilleries changed"
        assert curr_tasting_notes == base_tasting_notes, "tasting_notes changed"
        assert curr_staging == base_staging, "staging_tasting_notes changed"
        assert curr_book_staging == base_book_staging, "staging_book_flavor_profiles changed"
        assert curr_flavor_profiles == base_flavor_profiles + inserted_count, f"flavor_profiles count mismatch"
        assert fk_missing == 0, "fk missing"
        assert duplicate_count == 0, "duplicate profile"
        assert inserted_count == 2, f"expected 2 inserted, got {inserted_count}"
        
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
    if inserted_count == 2 and blocked_count == 0 and fk_missing == 0:
        gate_decision = "GO"
    elif inserted_count > 0:
        gate_decision = "REVIEW"
        
    md = f"""# NB-FP-05 Staging Book Flavor Profiles Promotion Apply Report

## Apply Results
- **Inserted Profiles:** {inserted_count}
- **Skipped/Blocked (Dry-Run Filtered):** {blocked_count}

## DB Post-Validation
- **Flavor Profiles Count:** {base_flavor_profiles} -> {curr_flavor_profiles}
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

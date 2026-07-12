import sqlite3
import csv
import json
import hashlib
import shutil
import uuid
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
    backup_path = root / "output" / "import" / "production_before_12y_book_minibatch_staging.db"
    
    in_jsonl = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12w_book_minibatch_validated.jsonl"
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12x_book_minibatch_valid_staging_dry_run.csv"
    
    report_out = root / "output" / "reports" / "12y_book_minibatch_staging_apply_report.md"
    gate_out = root / "output" / "reports" / "12y_book_minibatch_staging_apply_gate.txt"
    
    shutil.copy2(db_path, backup_path)
    
    plan_map = {}
    with open(in_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            b_id = row.get("batch_id")
            title = row.get("candidate_title_clean")
            key = f"{b_id}|{title}"
            plan_map[key] = row
            
    candidates = []
    with open(in_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                key = f"{data.get('batch_id')}|{data.get('candidate_title_clean')}"
                if key in plan_map:
                    data["_plan"] = plan_map[key]
                    candidates.append(data)
            except:
                continue
                
    to_insert = []
    for cand in candidates:
        plan = cand["_plan"]
        if (plan.get("planned_status") == "planned" and 
            cand.get("copyright_safe") is True and 
            plan.get("duplicate_note_found") == "false" and 
            plan.get("matched_distillery_id") and 
            float(cand.get("confidence", 0)) >= 0.5):
            to_insert.append(cand)
            
    metrics = {
        "planned_for_insert": len(to_insert),
        "inserted": 0,
        "blocked": 0,
        "fk_missing": 0,
        "pre_whiskies": 0,
        "pre_distilleries": 0,
        "pre_tasting_notes": 0,
        "pre_flavor_profiles": 0,
        "pre_staging": 0,
        "post_whiskies": 0,
        "post_distilleries": 0,
        "post_tasting_notes": 0,
        "post_flavor_profiles": 0,
        "post_staging": 0,
        "rollback_happened": False,
        "error": None
    }
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) FROM whiskies")
        metrics["pre_whiskies"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM distilleries")
        metrics["pre_distilleries"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasting_notes")
        metrics["pre_tasting_notes"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flavor_profiles")
        metrics["pre_flavor_profiles"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        metrics["pre_staging"] = cur.fetchone()[0]
        
        cur.execute("BEGIN TRANSACTION")
        
        for cand in to_insert:
            plan = cand["_plan"]
            
            dist_id = plan["matched_distillery_id"]
            title = cand["candidate_title_clean"]
            dist_name = cand["possible_distillery"]
            
            # Check FK (distillery exists?)
            cur.execute("SELECT 1 FROM distilleries WHERE distillery_id = ?", (dist_id,))
            if not cur.fetchone():
                metrics["fk_missing"] += 1
                metrics["blocked"] += 1
                continue
                
            tasting = cand.get("structured_tasting_note", {})
            radar = cand.get("radar_scores_0_100", {})
            
            source_url = cand.get("book_source", None)
            
            import_rec_json = json.dumps({
                "distillery_id": dist_id,
                "confidence": cand.get("confidence", 0),
                "radar_scores_0_100": radar,
                "style_summary": tasting.get("style_summary"),
                "batch_id": cand.get("batch_id")
            })
            
            full_product_name = f"{dist_name} {title}" if title != dist_name else dist_name
            
            # The schema doesn't have an ID we supply directly unless it's autoincrement. We let it autoincrement.
            # Insert into the actual schema of staging_tasting_notes
            cur.execute('''
                INSERT INTO staging_tasting_notes (
                    source_system,
                    product_name,
                    nose, palate, finish, conclusion,
                    source_name, source_url,
                    approval_status, match_status, status, source_verified,
                    import_recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                "book_entry_boundary_clean_title",
                full_product_name,
                tasting.get("nose"), 
                tasting.get("palate"), 
                tasting.get("finish"), 
                tasting.get("overall_summary"),
                cand.get("book_source"),
                source_url,
                "staging_pending_review",
                "unmatched",
                "PENDING",
                "1",
                import_rec_json
            ))
            metrics["inserted"] += 1
            
        cur.execute("SELECT COUNT(*) FROM whiskies")
        metrics["post_whiskies"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM distilleries")
        metrics["post_distilleries"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasting_notes")
        metrics["post_tasting_notes"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flavor_profiles")
        metrics["post_flavor_profiles"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM staging_tasting_notes")
        metrics["post_staging"] = cur.fetchone()[0]
        
        assert metrics["post_whiskies"] == metrics["pre_whiskies"] == 1831, f"Whiskies count changed! {metrics['post_whiskies']} != 1831"
        assert metrics["post_distilleries"] == metrics["pre_distilleries"] == 990, "Distilleries count changed!"
        assert metrics["post_tasting_notes"] == metrics["pre_tasting_notes"] == 85, "Tasting notes count changed!"
        assert metrics["post_flavor_profiles"] == metrics["pre_flavor_profiles"] == 380, "Flavor profiles count changed!"
        assert metrics["post_staging"] == metrics["pre_staging"] + metrics["inserted"], "Staging count mismatch!"
        assert metrics["post_staging"] == 81, "Staging count should be 81!"
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        metrics["rollback_happened"] = True
        metrics["error"] = str(e)
    finally:
        conn.close()
        
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["rollback_happened"] or metrics["inserted"] == 0:
        gate_decision = "NO_GO"
    elif metrics["inserted"] == metrics["planned_for_insert"] and metrics["blocked"] == 0 and metrics["fk_missing"] == 0:
        gate_decision = "GO"
    else:
        gate_decision = "REVIEW"
        
    md = f"""# 12Y Book Minibatch Staging Insert Report

## Security & DB Status
- DB Modified: `{'true' if hash_after != get_hash(backup_path) else 'false'}`
- Production DB Hash: `{hash_after}`
- Backup Hash: `{get_hash(backup_path)}`

## Metrics
- **Planned for Insert:** {metrics["planned_for_insert"]}
- **Inserted:** {metrics["inserted"]}
- **Blocked:** {metrics["blocked"]}
- **FK Missing:** {metrics["fk_missing"]}

## Core Tables Counts (Pre -> Post)
- **Whiskies:** {metrics["pre_whiskies"]} -> {metrics["post_whiskies"]}
- **Distilleries:** {metrics["pre_distilleries"]} -> {metrics["post_distilleries"]}
- **Flavor Profiles:** {metrics["pre_flavor_profiles"]} -> {metrics["post_flavor_profiles"]}
- **Tasting Notes:** {metrics["pre_tasting_notes"]} -> {metrics["post_tasting_notes"]}
- **Staging Tasting Notes:** {metrics["pre_staging"]} -> {metrics["post_staging"]}

## Transaction Status
- **Rollback Happened:** {metrics["rollback_happened"]}
- **Error:** {metrics["error"] or "None"}

Gate decision: **{gate_decision}**
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)

if __name__ == "__main__":
    main()

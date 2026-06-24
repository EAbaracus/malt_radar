import sqlite3
import csv
import json
import hashlib
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
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12z_book_staging_qa.csv"
    report_out = root / "output" / "reports" / "12z_book_staging_qa_report.md"
    gate_out = root / "output" / "reports" / "12z_book_staging_qa_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(staging_tasting_notes)")
    columns = {row[1]: idx for idx, row in enumerate(cur.fetchall())}
    
    cur.execute("SELECT * FROM staging_tasting_notes WHERE source_system = 'book_entry_boundary_clean_title'")
    rows = cur.fetchall()
    
    metrics = {
        "qa_input_count": len(rows),
        "qa_pass": 0,
        "qa_warn": 0,
        "qa_fail": 0,
        "duplicate_count": 0,
        "long_raw_excerpt": 0
    }
    
    product_names = [r[columns["product_name"]] for r in rows if "product_name" in columns and r[columns["product_name"]]]
    
    out_csv_rows = []
    
    for row in rows:
        reasons = []
        qa_status = "qa_pass"
        
        def val(colname):
            if colname in columns:
                return row[columns[colname]]
            return None
            
        note_id = val("staging_note_id")
        whisky_id = val("whisky_id")
        src_sys = val("source_system")
        approval = val("approval_status")
        review_stat = val("status")
        prod_name = val("product_name")
        imp_rec = val("import_recommendation")
        
        nose = val("nose")
        palate = val("palate")
        finish = val("finish")
        conclusion = val("conclusion")
        
        if src_sys != "book_entry_boundary_clean_title":
            qa_status = "qa_fail"
            reasons.append("Invalid source_system")
            
        if approval != "staging_pending_review" and review_stat != "PENDING":
            qa_status = "qa_warn"
            reasons.append("Approval/status not pending")
            
        imp_json_ok = False
        has_struct_note = False
        has_style = False
        radar_non_null = 0
        conf = 0.0
        dist_id = None
        
        if imp_rec:
            try:
                j = json.loads(imp_rec)
                imp_json_ok = True
                dist_id = j.get("distillery_id")
                conf = float(j.get("confidence", 0))
                has_style = bool(j.get("style_summary"))
                radar = j.get("radar_scores_0_100", {})
                
                for k, v in radar.items():
                    if v is not None:
                        if not isinstance(v, (int, float)) or not (0 <= v <= 100):
                            qa_status = "qa_fail"
                            reasons.append("Invalid radar score")
                        else:
                            radar_non_null += 1
            except:
                qa_status = "qa_fail"
                reasons.append("Invalid import_recommendation JSON")
                
        if not whisky_id and not dist_id and not val("matched_master_whisky_id"):
            qa_status = "qa_fail"
            reasons.append("Missing whisky_id or dist_id mapping")
            
        if conf < 0.5:
            qa_status = "qa_fail"
            reasons.append("Low confidence")
            
        has_nose = bool(nose)
        has_palate = bool(palate)
        has_finish = bool(finish)
        
        if not (has_nose or has_palate or has_finish or has_style or conclusion):
            qa_status = "qa_fail"
            reasons.append("No tasting notes found")
        else:
            has_struct_note = True
            
        suspect_long = False
        for text in [nose, palate, finish, conclusion]:
            if text and len(text) > 600:
                suspect_long = True
                
        if suspect_long:
            metrics["long_raw_excerpt"] += 1
            if qa_status != "qa_fail":
                qa_status = "qa_warn"
            reasons.append("Suspected long raw excerpt (not copyright safe)")
            
        dup_count = product_names.count(prod_name) - 1
        if dup_count > 0:
            metrics["duplicate_count"] += 1
            if qa_status != "qa_fail":
                qa_status = "qa_warn"
            reasons.append(f"Duplicate product name ({dup_count} others)")
            
        metrics[qa_status] += 1
        
        out_csv_rows.append({
            "staging_note_id": note_id,
            "whisky_id": whisky_id,
            "source_system": src_sys,
            "approval_status": approval,
            "review_status": review_stat,
            "candidate_title_clean": prod_name,
            "possible_distillery": "",
            "qa_status": qa_status,
            "qa_reason": " | ".join(reasons),
            "has_structured_note": has_struct_note,
            "has_nose": has_nose,
            "has_palate": has_palate,
            "has_finish": has_finish,
            "has_style_summary": has_style,
            "radar_non_null_count": radar_non_null,
            "confidence": conf,
            "copyright_safe": not suspect_long,
            "import_recommendation_json_ok": imp_json_ok,
            "suspected_long_raw_excerpt": suspect_long,
            "duplicate_staging_count": dup_count
        })
        
    if out_csv_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_csv_rows[0].keys()))
            w.writeheader()
            w.writerows(out_csv_rows)
            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["qa_fail"] > 0 or metrics["qa_pass"] == 0:
        gate_decision = "NO_GO"
    elif metrics["qa_pass"] == metrics["qa_input_count"] and metrics["qa_warn"] == 0 and metrics["long_raw_excerpt"] == 0:
        gate_decision = "GO"
    else:
        gate_decision = "REVIEW"
        
    md = f"""# 12Z Book Staging QA Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **QA Input Count:** {metrics["qa_input_count"]}
- **QA Pass:** {metrics["qa_pass"]}
- **QA Warn:** {metrics["qa_warn"]}
- **QA Fail:** {metrics["qa_fail"]}
- **Duplicate Staging Count:** {metrics["duplicate_count"]}
- **Long Raw Excerpt Count:** {metrics["long_raw_excerpt"]}

Gate decision: **{gate_decision}**
"""
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)

if __name__ == "__main__":
    main()

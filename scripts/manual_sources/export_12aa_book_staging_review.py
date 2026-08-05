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
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12aa_book_staging_review_export.csv"
    out_jsonl = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12aa_book_staging_review_export.jsonl"
    report_out = root / "output" / "reports" / "12aa_book_staging_review_export_report.md"
    gate_out = root / "output" / "reports" / "12aa_book_staging_review_export_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(staging_tasting_notes)")
    columns = {row[1]: idx for idx, row in enumerate(cur.fetchall())}
    
    cur.execute("SELECT * FROM staging_tasting_notes WHERE source_system = 'book_entry_boundary_clean_title'")
    rows = cur.fetchall()
    
    metrics = {
        "export_input_count": len(rows),
        "export_ready": 0,
        "export_warn": 0,
        "export_fail": 0,
        "json_parse_fail": 0,
        "missing_structured_note": 0
    }
    
    out_csv_rows = []
    out_jsonl_rows = []
    
    for row in rows:
        export_status = "export_ready"
        
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
        
        if approval != "staging_pending_review" and review_stat != "PENDING":
            export_status = "export_warn"
            
        radar = {}
        conf = 0.0
        style = ""
        copyright_safe = True
        
        if imp_rec:
            try:
                j = json.loads(imp_rec)
                conf = float(j.get("confidence", 0))
                style = j.get("style_summary", "")
                radar = j.get("radar_scores_0_100", {})
            except:
                metrics["json_parse_fail"] += 1
                export_status = "export_fail"
        else:
            metrics["json_parse_fail"] += 1
            export_status = "export_fail"
            
        has_nose = bool(nose)
        has_palate = bool(palate)
        has_finish = bool(finish)
        
        if not (has_nose or has_palate or has_finish or style or conclusion):
            metrics["missing_structured_note"] += 1
            export_status = "export_fail"
            
        for text in [nose, palate, finish, conclusion]:
            if text and len(text) > 600:
                export_status = "export_warn"
                copyright_safe = False
                
        metrics[export_status] += 1
        
        csv_row = {
            "staging_note_id": note_id,
            "whisky_id": whisky_id,
            "source_system": src_sys,
            "approval_status": approval,
            "review_status": review_stat,
            "candidate_title_clean": prod_name,
            "possible_distillery": "",
            "nose": nose,
            "palate": palate,
            "finish": finish,
            "style_summary": style,
            "overall_summary": conclusion,
            "sweet": radar.get("sweet"),
            "smoky": radar.get("smoky"),
            "peaty": radar.get("peaty"),
            "fruity": radar.get("fruity"),
            "spicy": radar.get("spicy"),
            "oaky": radar.get("oaky"),
            "floral": radar.get("floral"),
            "confidence": conf,
            "copyright_safe": copyright_safe,
            "export_status": export_status,
            "review_decision": "",
            "reviewer_notes": ""
        }
        
        out_csv_rows.append(csv_row)
        out_jsonl_rows.append(csv_row)
        
    if out_csv_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_csv_rows[0].keys()))
            w.writeheader()
            w.writerows(out_csv_rows)
            
    if out_jsonl_rows:
        Path(out_jsonl).parent.mkdir(parents=True, exist_ok=True)
        with open(out_jsonl, "w", encoding="utf-8") as f:
            for r in out_jsonl_rows:
                f.write(json.dumps(r) + "\n")
                f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["export_fail"] > 0 or metrics["export_ready"] == 0:
        gate_decision = "NO_GO"
    elif metrics["export_ready"] == metrics["export_input_count"] and metrics["export_warn"] == 0:
        gate_decision = "GO"
    else:
        gate_decision = "REVIEW"
        
    md = f"""# 12AA Book Staging Review Export Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Export Input Count:** {metrics["export_input_count"]}
- **Export Ready:** {metrics["export_ready"]}
- **Export Warn:** {metrics["export_warn"]}
- **Export Fail:** {metrics["export_fail"]}
- **JSON Parse Fail:** {metrics["json_parse_fail"]}
- **Missing Structured Note:** {metrics["missing_structured_note"]}

Gate decision: **{gate_decision}**
"""
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)

if __name__ == "__main__":
    main()

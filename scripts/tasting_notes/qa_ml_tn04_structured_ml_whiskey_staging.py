import sqlite3
import csv
import json
import hashlib
from pathlib import Path
from collections import defaultdict

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    out_csv = root / "data" / "output" / "ml_tn04_structured_ml_whiskey_staging_qa.csv"
    report_out = root / "output" / "reports" / "ml_tn04_structured_ml_whiskey_staging_qa_report.md"
    gate_out = root / "output" / "reports" / "ml_tn04_structured_ml_whiskey_staging_qa_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT whisky_id FROM whiskies")
    all_whisky_ids = set(row[0] for row in cur.fetchall())
    
    cur.execute("SELECT whisky_id FROM tasting_notes WHERE source_system = 'structured_ml_whiskey'")
    existing_tasting_notes_ids = set(row[0] for row in cur.fetchall())
    
    cur.execute("PRAGMA table_info(staging_tasting_notes)")
    columns = [row[1] for row in cur.fetchall()]
    
    col_idx = {name: i for i, name in enumerate(columns)}
    
    cur.execute("SELECT * FROM staging_tasting_notes WHERE source_system = 'structured_ml_whiskey'")
    rows = cur.fetchall()
    
    metrics = {
        "qa_input_count": len(rows),
        "qa_pass_count": 0,
        "qa_warn_count": 0,
        "qa_fail_count": 0,
        "fk_missing_count": 0,
        "json_parse_fail_count": 0,
        "raw_long_text_count": 0,
        "duplicate_staging_count": 0,
        "duplicate_tasting_note_count": 0,
        "missing_summary_count": 0,
        "too_short_summary_count": 0,
        "missing_provenance_count": 0
    }
    
    staging_whisky_counts = defaultdict(int)
    for row in rows:
        wid = row[col_idx["whisky_id"]]
        if wid: staging_whisky_counts[wid] += 1
        
    out_rows = []
    
    for row in rows:
        staging_note_id = row[col_idx.get("staging_note_id", -1)] if "staging_note_id" in col_idx else row[0]
        wid = row[col_idx["whisky_id"]]
        source_sys = row[col_idx["source_system"]]
        app_status = row[col_idx.get("approval_status", -1)] if "approval_status" in col_idx else ""
        rev_status = row[col_idx.get("review_status", -1)] if "review_status" in col_idx else row[col_idx.get("status", -1)]
        status = row[col_idx.get("status", -1)] if "status" in col_idx else ""
        
        summary = row[col_idx.get("conclusion", -1)] if "conclusion" in col_idx else ""
        if not summary: summary = ""
        
        import_rec_str = row[col_idx.get("import_recommendation", -1)] if "import_recommendation" in col_idx else ""
        
        qa_status = "qa_pass"
        reasons = []
        
        if not wid or wid not in all_whisky_ids:
            qa_status = "qa_fail"
            reasons.append("fk_missing")
            metrics["fk_missing_count"] += 1
            
        json_ok = "true"
        has_src_id = "false"
        has_prov = "false"
        if import_rec_str:
            try:
                rec_json = json.loads(import_rec_str)
                if rec_json.get("source_id"): has_src_id = "true"
                if rec_json.get("provenance"): has_prov = "true"
            except:
                json_ok = "false"
                qa_status = "qa_fail"
                reasons.append("json_parse_fail")
                metrics["json_parse_fail_count"] += 1
        else:
            json_ok = "false"
            qa_status = "qa_warn"
            reasons.append("missing_import_recommendation")
            
        if has_prov == "false" or has_src_id == "false":
            if qa_status == "qa_pass": qa_status = "qa_warn"
            reasons.append("missing_provenance")
            metrics["missing_provenance_count"] += 1
            
        sum_len = len(summary)
        raw_long_text = "false"
        if sum_len == 0:
            qa_status = "qa_fail"
            reasons.append("missing_summary")
            metrics["missing_summary_count"] += 1
        elif sum_len < 30:
            if qa_status == "qa_pass": qa_status = "qa_warn"
            reasons.append("too_short_summary")
            metrics["too_short_summary_count"] += 1
        elif sum_len > 350:
            qa_status = "qa_fail"
            reasons.append("raw_long_text_suspected")
            raw_long_text = "true"
            metrics["raw_long_text_count"] += 1
            
        dup_staging_count = staging_whisky_counts.get(wid, 0)
        if dup_staging_count > 1:
            qa_status = "qa_fail"
            reasons.append("duplicate_staging")
            metrics["duplicate_staging_count"] += 1
            
        dup_tasting_note = "false"
        if wid in existing_tasting_notes_ids:
            qa_status = "qa_fail"
            reasons.append("duplicate_tasting_note")
            dup_tasting_note = "true"
            metrics["duplicate_tasting_note_count"] += 1
            
        if qa_status == "qa_pass":
            metrics["qa_pass_count"] += 1
        elif qa_status == "qa_warn":
            metrics["qa_warn_count"] += 1
        else:
            metrics["qa_fail_count"] += 1
            
        out_rows.append({
            "staging_note_id": staging_note_id,
            "whisky_id": wid,
            "source_system": source_sys,
            "approval_status": app_status,
            "review_status": rev_status,
            "status": status,
            "qa_status": qa_status,
            "qa_reason": " | ".join(reasons),
            "summary_length": sum_len,
            "import_recommendation_json_ok": json_ok,
            "has_source_id": has_src_id,
            "has_provenance": has_prov,
            "suspected_raw_long_text": raw_long_text,
            "duplicate_staging_count": dup_staging_count,
            "duplicate_tasting_note_found": dup_tasting_note,
            "review_decision": "approve" if qa_status == "qa_pass" else "reject",
            "reviewer_notes": ""
        })
        
    if out_rows:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
            
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["qa_pass_count"] > 0 and metrics["qa_fail_count"] == 0 and metrics["raw_long_text_count"] == 0:
        if metrics["qa_warn_count"] > 0:
            gate_decision = "REVIEW"
        else:
            gate_decision = "GO"
    elif metrics["qa_pass_count"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# ML-TN-04 Structured ML Whiskey Staging QA Report

## Metrics
- **QA Input Count:** {metrics["qa_input_count"]}
- **QA Pass:** {metrics["qa_pass_count"]}
- **QA Warn:** {metrics["qa_warn_count"]}
- **QA Fail:** {metrics["qa_fail_count"]}

## Block Reasons Details
- **Missing FK:** {metrics["fk_missing_count"]}
- **JSON Parse Fail:** {metrics["json_parse_fail_count"]}
- **Raw Long Text Suspected:** {metrics["raw_long_text_count"]}
- **Duplicate Staging Count (total offenses):** {metrics["duplicate_staging_count"]}
- **Duplicate Tasting Note Count:** {metrics["duplicate_tasting_note_count"]}
- **Missing Summary:** {metrics["missing_summary_count"]}
- **Too Short Summary:** {metrics["too_short_summary_count"]}
- **Missing Provenance:** {metrics["missing_provenance_count"]}

## Security & Verification
- **DB Modified:** {'true' if hash_before != hash_after else 'false'}
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

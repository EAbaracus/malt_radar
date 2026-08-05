import sqlite3
import csv
import json
import hashlib
import sys
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def create_example_schema():
    return [
        {
            "batch_id": "batch_12v_xxxxxx",
            "candidate_title_clean": "Example 12 Year Old",
            "possible_distillery": "Example Distillery",
            "structured_tasting_note": {
                "nose": "Fruity and sweet.",
                "palate": "Oak and spice.",
                "finish": "Long and warm.",
                "style_summary": "A balanced dram.",
                "overall_summary": "Very good indeed."
            },
            "radar_scores_0_100": {
                "sweet": 60,
                "smoky": 10,
                "peaty": 0,
                "fruity": 80,
                "spicy": 40,
                "oaky": 50,
                "floral": 20
            },
            "confidence": 0.95,
            "copyright_safe": True,
            "notes": None
        }
    ]

def validate_scores(radar):
    if not isinstance(radar, dict): return False, 0
    non_null_count = 0
    for k in ["sweet", "smoky", "peaty", "fruity", "spicy", "oaky", "floral"]:
        val = radar.get(k)
        if val is not None:
            if not isinstance(val, (int, float)): return False, non_null_count
            if not (0 <= val <= 100): return False, non_null_count
            non_null_count += 1
    return True, non_null_count

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_jsonl = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12v_book_clean_title_minibatch_input.jsonl"
    in_llm_json = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12w_book_minibatch_llm_output.json"
    
    out_jsonl = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12w_book_minibatch_validated.jsonl"
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12w_book_minibatch_validation_review.csv"
    report_out = root / "output" / "reports" / "12w_book_minibatch_validation_report.md"
    gate_out = root / "output" / "reports" / "12w_book_minibatch_validation_gate.txt"
    
    hash_before = get_hash(db_path)
    
    metrics = {
        "input_batch_count": 0,
        "llm_output_count": 0,
        "valid_candidate": 0,
        "manual_review": 0,
        "rejected": 0,
        "missing_output_count": 0
    }
    
    expected_inputs = {}
    if in_jsonl.exists():
        with open(in_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                metrics["input_batch_count"] += 1
                key = f"{data.get('batch_id')}|{data.get('possible_distillery')}|{data.get('candidate_title_clean')}"
                expected_inputs[key] = data
                
    if not in_llm_json.exists():
        metrics["missing_output_count"] = metrics["input_batch_count"]
        with open(in_llm_json, "w", encoding="utf-8") as f:
            json.dump(create_example_schema(), f, indent=2, ensure_ascii=False)
            
        md = f"""# 12W Book Minibatch Validation Report

## Security & DB Status
- DB Modified: false
- Production DB Hash: {hash_before}

## Error
- File `12w_book_minibatch_llm_output.json` did not exist.
- An example schema has been written to the path to guide manual/LLM execution.

## Metrics
- **Input Batch Count:** {metrics["input_batch_count"]}
- **LLM Output Count:** 0
- **Valid Candidate:** 0
- **Manual Review:** 0
- **Rejected:** 0
- **Missing Output:** {metrics["missing_output_count"]}
"""
        with open(report_out, "w", encoding="utf-8") as f:
            f.write(md)
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

            
        with open(gate_out, "w", encoding="utf-8") as f:
            f.write("NO_GO")
            
        return

    with open(in_llm_json, "r", encoding="utf-8") as f:
        try:
            llm_data = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON in LLM output")
            llm_data = []
            
    if not isinstance(llm_data, list):
        llm_data = [llm_data]
        
    out_csv_rows = []
    out_jsonl_rows = []
    
    for item in llm_data:
        metrics["llm_output_count"] += 1
        b_id = item.get("batch_id")
        dist = item.get("possible_distillery")
        title = item.get("candidate_title_clean")
        key = f"{b_id}|{dist}|{title}"
        
        status = "valid_candidate"
        reasons = []
        
        if key not in expected_inputs:
            status = "rejected"
            reasons.append("Mismatch: batch_id/distillery/title not found in input")
            
        if item.get("copyright_safe") is not True:
            status = "rejected"
            reasons.append("Not flagged as copyright safe")
            
        conf = item.get("confidence")
        if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
            status = "rejected"
            reasons.append("Invalid confidence score")
            
        tasting = item.get("structured_tasting_note") or {}
        has_nose = bool(tasting.get("nose"))
        has_palate = bool(tasting.get("palate"))
        has_finish = bool(tasting.get("finish"))
        has_style = bool(tasting.get("style_summary"))
        
        if not (has_nose or has_palate or has_finish or has_style):
            status = "rejected"
            reasons.append("No valid tasting notes extracted")
            
        for k, v in tasting.items():
            if v and isinstance(v, str) and len(v) > 600:
                if status != "rejected":
                    status = "manual_review"
                reasons.append(f"Long field '{k}' might be direct quote")
                
        radar = item.get("radar_scores_0_100")
        valid_radar, non_null_count = validate_scores(radar)
        if not valid_radar:
            status = "rejected"
            reasons.append("Invalid radar score format/value")
            
        if status == "valid_candidate" and conf < 0.7:
            status = "manual_review"
            reasons.append("Low confidence")
            
        if key in expected_inputs:
            del expected_inputs[key]
            
        metrics[status] += 1
        
        out_csv_rows.append({
            "batch_id": b_id,
            "possible_distillery": dist,
            "candidate_title_clean": title,
            "validation_status": status,
            "rejection_reason": " | ".join(reasons),
            "has_nose": has_nose,
            "has_palate": has_palate,
            "has_finish": has_finish,
            "has_style_summary": has_style,
            "radar_non_null_count": non_null_count,
            "confidence": conf,
            "copyright_safe": item.get("copyright_safe"),
            "review_status": "pending_review" if status != "rejected" else "rejected"
        })
        
        if status in ["valid_candidate", "manual_review"]:
            out_jsonl_rows.append(item)
            
    metrics["missing_output_count"] = len(expected_inputs)
    
    if out_csv_rows:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_csv_rows[0].keys()))
            w.writeheader()
            w.writerows(out_csv_rows)
            
    if out_jsonl_rows:
        with open(out_jsonl, "w", encoding="utf-8") as f:
            for jrow in out_jsonl_rows:
                f.write(json.dumps(jrow, ensure_ascii=False) + "\n")
                
    hash_after = get_hash(db_path)
    
    gate_decision = "NO_GO"
    if metrics["llm_output_count"] == 0 or metrics["valid_candidate"] == 0:
        gate_decision = "NO_GO"
    elif metrics["valid_candidate"] > 0 and metrics["rejected"] == 0 and metrics["manual_review"] == 0 and metrics["missing_output_count"] == 0:
        gate_decision = "GO"
    elif metrics["valid_candidate"] > 0:
        gate_decision = "REVIEW"
        
    md = f"""# 12W Book Minibatch Validation Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input Batch Count:** {metrics["input_batch_count"]}
- **LLM Output Count:** {metrics["llm_output_count"]}
- **Valid Candidate:** {metrics["valid_candidate"]}
- **Manual Review:** {metrics["manual_review"]}
- **Rejected:** {metrics["rejected"]}
- **Missing Output:** {metrics["missing_output_count"]}

Gate decision: **{gate_decision}**
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)

if __name__ == "__main__":
    main()

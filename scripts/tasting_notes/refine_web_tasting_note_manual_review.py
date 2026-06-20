import os
import csv
import re

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

input_csv_path = os.path.join(output_dir, "web_tasting_note_extraction_manual_review.csv")

refined_csv_path = os.path.join(output_dir, "web_tasting_note_manual_review_refined.csv")
parser_csv_path = os.path.join(output_dir, "web_tasting_note_parser_improvement_candidates.csv")
safe_csv_path = os.path.join(output_dir, "web_tasting_note_safe_summary_candidates.csv")
wrong_match_csv_path = os.path.join(output_dir, "web_tasting_note_wrong_match_rejects.csv")

OUT_FIELDS = [
    "whisky_id", "whisky_name", "source_url", "source_domain", "source_type",
    "match_score", "mismatch_flags", "extraction_status", "manual_review_reason",
    "refined_class", "short_signal_summary", "parser_gap", "recommended_action",
    "production_ready"
]

def main():
    print("Starting Manual Review Candidate Refinement Pipeline...")
    
    if not os.path.exists(input_csv_path):
        print(f"Error: {input_csv_path} not found.")
        return
        
    with open(input_csv_path, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    refined_results = []
    parser_candidates = []
    safe_candidates = []
    wrong_matches = []
    
    counts = {
        "parser_improvement_candidate": 0,
        "safe_official_summary_candidate": 0,
        "retailer_summary_candidate": 0,
        "wrong_match_reject": 0,
        "low_quality_source_reject": 0,
        "bot_block_or_redirect": 0,
        "insufficient_tasting_signal": 0
    }
    
    for row in reader:
        out = {k: row.get(k, "") for k in OUT_FIELDS}
        out["production_ready"] = "false" # Must remain false per Gate rule
        out["manual_review_reason"] = row.get("recommended_action", "manual_review")
        
        mismatch = row.get("mismatch_flags", "")
        s_type = row.get("source_type", "")
        snapshot_path = row.get("snapshot_path", "")
        
        refined_class = ""
        parser_gap = ""
        short_signal = ""
        action = "keep_in_manual_review"
        
        html_content = ""
        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, 'r', encoding='utf-8', errors='ignore') as hf:
                html_content = hf.read()
                
        # Simple extraction for short_signal
        from bs4 import BeautifulSoup
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True).lower()
            if len(text) < 500:
                refined_class = "bot_block_or_redirect"
                action = "reject"
            else:
                # Basic signal matching
                match = re.search(r'(.{0,40}(?:tasting note|review|nose|palate|finish).{0,60})', text)
                if match:
                    short_signal = match.group(1).strip()
        else:
            text = ""
            
        if not refined_class:
            if mismatch:
                refined_class = "wrong_match_reject"
                action = "reject"
            elif s_type in ["unknown", "community_review"]:
                refined_class = "low_quality_source_reject"
                action = "reject"
            elif s_type == "retailer_note":
                refined_class = "retailer_summary_candidate"
            elif s_type == "official":
                if short_signal:
                    refined_class = "safe_official_summary_candidate"
                else:
                    refined_class = "insufficient_tasting_signal"
                    action = "reject"
            elif s_type == "review_site":
                # If we have "nose", "palate", "finish" in the text but our parser didn't extract it
                if "nose" in text and "palate" in text and "finish" in text:
                    refined_class = "parser_improvement_candidate"
                    parser_gap = "Missing explicit structure extraction"
                elif short_signal:
                    refined_class = "parser_improvement_candidate"
                    parser_gap = "Missed generic tasting signal"
                else:
                    refined_class = "insufficient_tasting_signal"
                    action = "reject"
            else:
                refined_class = "insufficient_tasting_signal"
                action = "reject"
                
        out["refined_class"] = refined_class
        out["parser_gap"] = parser_gap
        out["short_signal_summary"] = short_signal
        out["recommended_action"] = action
        
        counts[refined_class] = counts.get(refined_class, 0) + 1
        refined_results.append(out)
        
        if refined_class == "parser_improvement_candidate":
            parser_candidates.append(out)
        elif refined_class == "safe_official_summary_candidate":
            safe_candidates.append(out)
        elif refined_class == "wrong_match_reject":
            wrong_matches.append(out)

    # Write CSVs
    def write_csv(path, rows):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            
    write_csv(refined_csv_path, refined_results)
    write_csv(parser_csv_path, parser_candidates)
    write_csv(safe_csv_path, safe_candidates)
    write_csv(wrong_match_csv_path, wrong_matches)
    
    # Reports
    r1_path = os.path.join(reports_dir, "222_web_tasting_note_manual_review_refinement_report.md")
    with open(r1_path, 'w', encoding='utf-8') as f:
        f.write("# Manual Review Refinement Report\n\n")
        f.write(f"Total manual review candidates processed: {len(refined_results)}\n\n")
        f.write("## Refined Class Breakdown\n")
        for k, v in counts.items():
            f.write(f"- {k}: {v}\n")
            
    r2_path = os.path.join(reports_dir, "223_web_tasting_note_parser_gap_report.md")
    with open(r2_path, 'w', encoding='utf-8') as f:
        f.write("# Parser Gap Report\n\n")
        f.write(f"Total parser improvement candidates: {len(parser_candidates)}\n\n")
        f.write("These candidates indicate that the current parser missed existing tasting signals or explicit headings.\n")
        
    gate_path = os.path.join(reports_dir, "224_web_tasting_note_manual_review_gate.txt")
    
    # Gate Validation
    prod_ready_fail = any(c["production_ready"] == "true" for c in refined_results)
    if not prod_ready_fail and len(refined_results) > 0:
        decision = "GO"
        msg = "Refinement successful. All production_ready values remained false."
    else:
        decision = "NO-GO"
        msg = "Failed criteria. Some candidates were marked production_ready=true or no candidates processed."
        
    with open(gate_path, 'w', encoding='utf-8') as f:
        f.write("12E Manual Review Refinement Gate\n=================================\n")
        f.write(f"Decision: {decision}\n\n{msg}")

    print(f"Refinement Pipeline finished. Processed: {len(refined_results)}")
    print(counts)

if __name__ == "__main__":
    main()

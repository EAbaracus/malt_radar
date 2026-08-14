import json
import csv
import re
from pathlib import Path
from collections import Counter

# Paths
INPUT_JSONL = Path("data/manual_sources/books/extracted_jsonl/12n_local_rule_book_profile_extractions.jsonl")
OUTPUT_JSONL = Path("data/manual_sources/books/extracted_jsonl/12n_local_rule_book_profile_extractions_clean.jsonl")
OUTPUT_CSV = Path("data/manual_sources/books/review_csv/12n_local_rule_clean_review.csv")
REPORT_MD = Path("output/reports/12n_local_rule_cleanup_report.md")
GATE_TXT = Path("output/reports/12n_local_rule_cleanup_gate.txt")

TARGETS = ["Ardbeg", "Highland Park", "Laphroaig", "Springbank", "Talisker", "Scapa"]

def clean_whisky_name(name):
    if not name: return ""
    
    # Split patterns based on requirements
    split_patterns = [
        r",\s*\d+(\.\d+)?\s*vol",
        r"\d+(\.\d+)?%",
        r"ALC/VOL",
        r"alc/vol",
        r"alc.\s*vol",
        r"TASTING NOTES",
        r" tasting notes ",
        r" made with ",
        r" a marriage ",
        r" pronounced ",
        r" fitting its name",
        r" the gulf ",
        r" a still ",
        r" every year ",
        r" officially ",
        r" non–chill ",
        r" non-chill ",
        r" the classic ",
        r" according to "
    ]
    
    cleaned = name
    for pattern in split_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            cleaned = cleaned[:match.start()]
            
    # Also drop any trailing dashes or commas
    cleaned = cleaned.strip(" -,.")
    
    # Maximum 6-8 words
    words = cleaned.split()
    if len(words) > 8:
        cleaned = " ".join(words[:8])
        
    return cleaned.strip()

def normalize_region(region):
    if not region: return ""
    region_upper = region.upper()
    if "ISLAY" in region_upper: return "Islay"
    if "SPEYSIDE" in region_upper: return "Speyside"
    if "HIGHLAND" in region_upper: return "Highland"
    if "ISLAND" in region_upper or "ORKNEY" in region_upper: return "Island/Orkney"
    if "CAMPBELTOWN" in region_upper: return "Campbeltown"
    if "LOWLAND" in region_upper: return "Lowland"
    return region

def process_records():
    if not INPUT_JSONL.exists():
        print(f"Input file not found: {INPUT_JSONL}")
        return
        
    records = []
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            records.append(json.loads(line))
            
    input_records = len(records)
    
    output_records = []
    stats = {
        "import_status": Counter(),
        "targets": Counter(),
        "reasons": Counter()
    }
    
    for row in records:
        reasons = []
        
        target = row.get("target", "")
        
        # 1. Clean whisky_name
        orig_name = row.get("whisky_name", "")
        cleaned_name = clean_whisky_name(orig_name)
        row["whisky_name"] = cleaned_name
        
        if cleaned_name.lower() == target.lower():
            reasons.append("generic_whisky_name")
            
        # 2. Normalize region
        row["region"] = normalize_region(row.get("region", ""))
        
        # 3. Cross-target leak
        for t in TARGETS:
            if t.lower() != target.lower() and t.lower() in cleaned_name.lower():
                reasons.append("cross_target_leak")
                
        # 4. Weak row detection
        radar_scores = row.get("radar_scores_0_100", {})
        radar_fields = [k for k, v in radar_scores.items() if isinstance(v, (int, float))]
        
        # Determine if it's a distillery_profile
        is_distillery_profile = False
        if row.get("record_type") == "distillery_profile" or row.get("type") == "distillery_profile":
            is_distillery_profile = True
            
        score_filled = len(radar_fields)
        has_summary = bool(row.get("nose_summary") or row.get("palate_summary") or row.get("finish_summary"))
        flavor_tags = row.get("flavor_tags", [])
        num_tags = len(flavor_tags) if isinstance(flavor_tags, list) else 0

        if not has_summary and num_tags < 4:
            reasons.append("weak_summary_and_tags")
            
        if not is_distillery_profile and score_filled < 3:
            reasons.append("weak_radar_signal")
            
        # 5. Import status rules
        if is_distillery_profile:
            import_status = "manual_review"
            reasons.append("distillery_profile")
        elif "cross_target_leak" in reasons or "weak_radar_signal" in reasons:
            import_status = "quarantine"
        elif not row.get("whisky_name"):
            import_status = "quarantine"
        elif "weak_summary_and_tags" in reasons:
            import_status = "manual_review"
        elif reasons:
            import_status = "manual_review"
        else:
            import_status = "staging_candidate"
            
        row["import_status"] = import_status
        row["cleanup_reasons"] = ", ".join(reasons)
        
        output_records.append(row)
        
        # Update stats
        stats["import_status"][import_status] += 1
        stats["targets"][target] += 1
        for r in reasons:
            stats["reasons"][r] += 1
            
    # Write JSONL
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for row in output_records:
            f.write(json.dumps(row) + "\n")
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

            
    # Write CSV
    if output_records:
        csv_keys = set()
        for r in output_records:
            csv_keys.update(r.keys())
        # Make a nicely ordered header
        header = ["target", "whisky_name", "record_type", "import_status", "cleanup_reasons", "region", "age_statement", "nose_summary", "palate_summary", "finish_summary"]
        header += [k for k in sorted(list(csv_keys)) if k not in header]
        
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            for row in output_records:
                # remove complex fields for csv
                csv_row = row.copy()
                if "radar_scores_0_100" in csv_row:
                    del csv_row["radar_scores_0_100"]
                if isinstance(csv_row.get("flavor_tags"), list):
                    csv_row["flavor_tags"] = "|".join(csv_row["flavor_tags"])
                writer.writerow(csv_row)
                
    # Write Report
    report_content = f"""# 12N Local Rule Cleanup Report

## Summary
- Input Records: {input_records}
- Output Records: {len(output_records)}
- Production DB Modified: False

## Import Status Counts
"""
    for k, v in stats["import_status"].most_common():
        report_content += f"- {k}: {v}\n"
        
    report_content += "\n## Targets\n"
    for k, v in stats["targets"].most_common():
        report_content += f"- {k}: {v}\n"
        
    report_content += "\n## Cleanup Reasons\n"
    for k, v in stats["reasons"].most_common():
        report_content += f"- {k}: {v}\n"
        
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    # Write Gate
    GATE_TXT.parent.mkdir(parents=True, exist_ok=True)
    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write("REVIEW")
        
    print(f"Cleanup complete. Processed {input_records} records.")
    print(f"staging_candidate: {stats['import_status']['staging_candidate']}")
    print(f"manual_review: {stats['import_status']['manual_review']}")
    print(f"quarantine: {stats['import_status']['quarantine']}")

if __name__ == "__main__":
    process_records()

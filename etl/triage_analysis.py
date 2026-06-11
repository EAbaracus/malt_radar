import csv
import json
import os
from collections import Counter

INPUT_FILE = "output/final_consolidated/review_needed_319_triage.csv"
OUTPUT_DIR = "output/final_consolidated/"

def run():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    # Output lists
    auto_fix_candidates = []
    manual_only = []
    reject_candidates = []
    distillery_alias_patch = []
    blended_patch = []

    counts = Counter()
    
    # Knowledge base for aliases
    ALIAS_MAP = {
        "hazelburn": "Springbank",
        "green spot": "Midleton",
        "yellow spot": "Midleton",
        "blue spot": "Midleton",
        "red spot": "Midleton",
        "ben nevis": "Ben Nevis",
        "longmorn": "Longmorn",
        "royal brackla": "Royal Brackla",
        "millstone": "Zuidam",
        "mortlach": "Mortlach",
        "knappogue castle": "Knappogue Castle",
        "white oak": "Eigashima (White Oak)",
        "scallywag": "Douglas Laing",
        "big peat": "Douglas Laing",
        "rock island": "Douglas Laing",
        "epicuran": "Douglas Laing",
        "pittyvaich": "Pittyvaich",
        "glenlossie": "Glenlossie",
        "dallas dhu": "Dallas Dhu",
        "rosebank": "Rosebank",
        "banff": "Banff",
        "port charlotte": "Bruichladdich"
    }

    BLENDED_BRANDS = ["scallywag", "big peat", "rock island", "sheep dip", "timorous beastie", "compass box"]

    output_rows = []

    for r in records:
        name = r.get("entity_name", "").lower()
        reason = r.get("problem_reason", "")
        tclass = r.get("classification", "")
        
        # New fields
        suggested_action = "Manual Review"
        suggested_distillery = ""
        suggested_bottler = ""
        confidence = "Low"
        auto_fix_safe = "false"
        notes = ""

        # Reject Candidate
        if tclass == "low_confidence" or "low confidence" in reason.lower() or "not whisky" in reason.lower():
            suggested_action = "Reject"
            notes = "Flagged as low confidence or invalid"
            confidence = "High"
            auto_fix_safe = "false"
            tclass = "reject_candidate"
        
        # Blended Patch
        elif tclass == "blended_or_vatted_malt" or any(b in name for b in BLENDED_BRANDS):
            tclass = "blended_or_vatted_malt"
            suggested_action = "Change type to Blended Malt"
            confidence = "High"
            auto_fix_safe = "true"
            notes = "Matches blended malt heuristic"
            # Extract bottler if known
            if "scallywag" in name or "big peat" in name or "timorous beastie" in name:
                suggested_bottler = "Douglas Laing"

        # Alias Patch
        else:
            mapped_distillery = None
            for alias, dist in ALIAS_MAP.items():
                if name.startswith(alias) or f" {alias} " in f" {name} ":
                    mapped_distillery = dist
                    break
            
            if mapped_distillery:
                if mapped_distillery == "Douglas Laing": # They are bottlers of blended malts usually, but sometimes single
                    suggested_action = "Assign to bottler / Set type"
                    suggested_bottler = mapped_distillery
                else:
                    suggested_action = "Map to known distillery alias"
                    suggested_distillery = mapped_distillery
                confidence = "High"
                auto_fix_safe = "true"
                notes = f"Mapped using alias knowledge base"
                tclass = "distillery_alias_patch"

            # Brand but not distillery
            elif "cask" in name or "batch" in name or "vintage" in name:
                tclass = "brand_not_distillery"
                suggested_action = "Check if it's an independent bottler release missing distillery"
                notes = "Contains typical bottling keywords but missing distillery"

        # Update row
        r["triage_class"] = tclass # override with refined class
        r["suggested_action"] = suggested_action
        r["suggested_distillery"] = suggested_distillery
        r["suggested_bottler"] = suggested_bottler
        r["confidence"] = confidence
        r["auto_fix_safe"] = auto_fix_safe
        r["notes"] = notes
        
        counts[tclass] += 1
        
        # Keep only required fields
        out_row = {
            "entity_name": r.get("entity_name"),
            "problem_reason": reason,
            "triage_class": tclass,
            "suggested_action": suggested_action,
            "suggested_distillery": suggested_distillery,
            "suggested_bottler": suggested_bottler,
            "confidence": confidence,
            "auto_fix_safe": auto_fix_safe,
            "notes": notes
        }
        
        output_rows.append(out_row)
        
        if auto_fix_safe == "true":
            auto_fix_candidates.append(out_row)
        else:
            if tclass == "reject_candidate":
                reject_candidates.append(out_row)
            else:
                manual_only.append(out_row)
                
        if tclass == "distillery_alias_patch":
            distillery_alias_patch.append(out_row)
        elif tclass == "blended_or_vatted_malt":
            blended_patch.append(out_row)

    # Save summary JSON
    summary = {
        "total_review_needed": len(records),
        "auto_fix_safe_count": len(auto_fix_candidates),
        "manual_only_count": len(manual_only),
        "reject_candidate_count": len(reject_candidates),
        "blended_patch_count": len(blended_patch),
        "distillery_alias_patch_count": len(distillery_alias_patch),
        "class_breakdown": dict(counts)
    }
    with open(os.path.join(OUTPUT_DIR, "review_needed_triage_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # Save CSVs
    fieldnames = ["entity_name", "problem_reason", "triage_class", "suggested_action", 
                  "suggested_distillery", "suggested_bottler", "confidence", "auto_fix_safe", "notes"]

    def write_csv(filename, data):
        if not data: return
        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    write_csv("review_needed_auto_fix_candidates.csv", auto_fix_candidates)
    write_csv("review_needed_manual_only.csv", manual_only)
    write_csv("review_needed_reject_candidates.csv", reject_candidates)
    write_csv("review_needed_distillery_alias_patch.csv", distillery_alias_patch)
    write_csv("review_needed_blended_patch.csv", blended_patch)

    print("Triage analysis completed.")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    run()

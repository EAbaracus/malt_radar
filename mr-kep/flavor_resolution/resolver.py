import os
import json
import csv
from collections import defaultdict
from .scoring import score_axis

AXIS_KEYWORDS = {
    "smoky": ["smoke", "smoky", "ash", "ashy", "embers", "phenolic", "tar", "tarry"],
    "peaty": ["peat", "peaty", "bog", "medicinal", "tcp", "band-aid", "iodine"],
    "sherry": ["sherry", "oloroso", "px", "pedro ximenez", "dried fruit", "raisin", "fig", "prune", "plum", "chocolate", "cocoa"],
    "fruity": ["fruit", "fruity", "apple", "pear", "citrus", "lemon", "lime", "orange", "peel", "zest", "mango", "banana", "orchard"],
    "sweet": ["sweet", "sweetness", "honey", "caramel", "butterscotch", "vanilla", "fudge", "toffee", "sugar", "praline", "marzipan"],
    "spicy": ["spice", "spicy", "cinnamon", "nutmeg", "ginger", "clove", "pepper", "peppery", "chilli"],
    "maritime": ["maritime", "sea", "salt", "salty", "brine", "briny", "coastal", "seaweed", "oyster", "beach", "marine"]
}

def resolve_flavor_profiles(evidence_staging_path: str, whisky_staging_path: str, out_csv_path: str, out_mapping_path: str):
    # Load all candidates from gold_whisky_staging.csv to ensure we process 100/100
    candidates = []
    with open(whisky_staging_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append({
                "id": row["gsd_candidate_id"],
                "name": row.get("canonical_name") or row.get("distillery_name", "Unknown")
            })

    # Read all evidence items
    evidence_by_cand = defaultdict(list)
    with open(evidence_staging_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            ev = json.loads(line)
            # Only use sensory evidence (nose, palate, finish)
            if ev.get("field_name") in ["nose", "palate", "finish"]:
                evidence_by_cand[ev["candidate_id"]].append(ev)

    flavor_profiles = []
    mappings = []
    
    total_unresolved_axes = 0
    total_axes = 0

    for cand in candidates:
        cand_id = cand["id"]
        name = cand["name"]
        
        cand_evs = evidence_by_cand.get(cand_id, [])

        profile = {
            "whisky_id": cand_id,
            "name": name,
            "smoky": None,
            "peaty": None,
            "sherry": None,
            "fruity": None,
            "sweet": None,
            "spicy": None,
            "maritime": None,
            "confidence": 1.0 if cand_evs else None,
            "evidence_count": 0
        }

        axis_matched_evs = defaultdict(set) # axis -> set of evidence_ids
        axis_keywords_found = defaultdict(set) # axis -> set of matched keywords

        for ev in cand_evs:
            ev_id = ev.get("evidence_id")
            quote = (ev.get("quote") or "").lower()
            val = (ev.get("field_value") or "").lower()
            text = f"{quote} {val}"

            for axis, keywords in AXIS_KEYWORDS.items():
                for kw in keywords:
                    if kw in text:
                        axis_keywords_found[axis].add(kw)
                        axis_matched_evs[axis].add(ev_id)

        # Count matched unique evidence records overall
        all_matched_evs = set()
        for axis, ev_ids in axis_matched_evs.items():
            all_matched_evs.update(ev_ids)
        profile["evidence_count"] = len(all_matched_evs)

        # Score axes and write mappings
        for axis in AXIS_KEYWORDS.keys():
            total_axes += 1
            kw_count = len(axis_keywords_found[axis])
            score = score_axis(kw_count)
            profile[axis] = score

            if score is None:
                total_unresolved_axes += 1

            # Log mappings
            for ev_id in axis_matched_evs[axis]:
                # Find the source quote and confidence for this evidence_id
                target_ev = next(e for e in cand_evs if e["evidence_id"] == ev_id)
                mappings.append({
                    "evidence_id": ev_id,
                    "whisky_id": cand_id,
                    "axis": axis,
                    "source_quote": target_ev.get("quote"),
                    "confidence": target_ev.get("confidence")
                })

        flavor_profiles.append(profile)

    # Write staging csv
    os.makedirs(os.path.dirname(out_csv_path), exist_ok=True)
    with open(out_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["whisky_id", "name", "smoky", "peaty", "sherry", "fruity", "sweet", "spicy", "maritime", "confidence", "evidence_count"])
        writer.writeheader()
        writer.writerows(flavor_profiles)

    # Write mapping jsonl
    os.makedirs(os.path.dirname(out_mapping_path), exist_ok=True)
    with open(out_mapping_path, 'w', encoding='utf-8') as f:
        for m in mappings:
            f.write(json.dumps(m) + "\n")

    return {
        "total_whisky": len(candidates),
        "profiles_created": len(flavor_profiles),
        "total_axes": total_axes,
        "unresolved_axes": total_unresolved_axes,
        "resolved_axes": total_axes - total_unresolved_axes,
        "mappings_count": len(mappings)
    }

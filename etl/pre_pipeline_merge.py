import os
import csv
import json
import argparse
from collections import defaultdict

# Setup directories
RAW_PRODUCTS = "output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv"
RAW_DISTILLERIES = "output/final/67_FINAL_import_ready_distilleries_whiskycom_enriched.csv"
RAW_FLAVORS = "recovered_from_radiant_bardeen/output/import/22_flavor_import_ready_cleaned.csv"

CLAUDE_DIR = "claude database"
CLAUDE_PRODUCTS = os.path.join(CLAUDE_DIR, "whisky_products_repaired.csv")

OUT_DIR = "output/pre_pipeline_consolidated"
DATA_DIR = "data/input"

MAJOR_DISTILLERIES = [
    "Macallan", "Glenfarclas", "Highland Park", "Springbank", 
    "Bunnahabhain", "Bruichladdich", "Glendronach", "Benriach",
    "Tobermory", "Aberlour", "Nikka", "Redbreast",
    "Arran", "Ardbeg", "Port Ellen", "Glenrothes", "Kilchoman",
    "Tomatin", "Glen Garioch", "Singleton", "Jura", "Longrow",
    "AnCnoc", "Tullibardine", "Bladnoch", "Dalmore", "Glen Moray",
    "Caol Ila", "Benromach", "Balblair", "Glencadam", "Old Pulteney",
    "Tamdhu", "Glenmorangie", "Laphroaig", "Bowmore", "Lagavulin",
    "Talisker", "Oban", "Clynelish", "Dalwhinnie", "Cragganmore",
    "Glenkinchie", "Kavalan", "Amrut", "Paul John", "Yamazaki",
    "Hakushu", "Chichibu", "Yoichi", "Miyagikyo"
]

CUSTOM_DISTILLERIES = {
    "two brewers": ("Two Brewers", "Canada"),
    "barrell": ("Barrell Craft Spirits", "United States"),
    "j.p. wiser": ("Hiram Walker", "Canada"),
    "parker": ("Heaven Hill", "United States"),
    "stagg": ("Buffalo Trace", "United States")
}

def safe_mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def save_csv(path, data, fieldnames):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    safe_mkdir(OUT_DIR)
    
    # 1. Load Data
    master_products = load_csv(RAW_PRODUCTS)
    claude_products = load_csv(CLAUDE_PRODUCTS)
    master_distilleries = load_csv(RAW_DISTILLERIES)
    
    # Build Claude map by product name
    claude_map = {p['product_name'].lower(): p for p in claude_products if p.get('product_name')}
    
    # Reports data
    conflicts = []
    merged_count = 0
    filled_fields = 0
    distillery_patch_candidates = []
    bottler_patch_candidates = []
    source_url_audit = []
    
    # Distilleries lookup
    dist_name_to_id = {d['name'].lower(): d.get('distillery_id') for d in master_distilleries if d.get('name')}
    patched_dist_ids = {} # name -> new_id
    
    # Helper to add patch candidate
    def add_distillery_patch(name, country="Scotland"):
        if name.lower() not in dist_name_to_id and name.lower() not in patched_dist_ids:
            new_id = f"DPATCH_{len(distillery_patch_candidates)+1}"
            distillery_patch_candidates.append({
                "distillery_id": new_id,
                "name": name,
                "country": country,
                "status": "Active",
                "notes": "Patched from pre-pipeline script"
            })
            patched_dist_ids[name.lower()] = new_id
            return new_id
        elif name.lower() in patched_dist_ids:
            return patched_dist_ids[name.lower()]
        else:
            return dist_name_to_id[name.lower()]

    # 2. Process Products
    for p in master_products:
        pname = p.get('name', '').lower()
        orig_name = p.get('original_name', '').lower()
        
        # --- MERGE CLAUDE DATA ---
        c_prod = claude_map.get(pname) or claude_map.get(orig_name)
        if c_prod:
            merged_count += 1
            for k, v in c_prod.items():
                if not v or v.strip() == "":
                    continue
                
                # Map Claude fields to master fields if possible
                target_k = k
                if k == "brand_name": target_k = "brand"
                if k == "distillery_name": target_k = "distillery_id" # we will handle this via name patching
                if k == "product_name": target_k = "name"
                if k == "normalized_product_name": continue # Do not add this to master
                
                if target_k not in p:
                    p[target_k] = v
                    filled_fields += 1
                else:
                    m_val = p[target_k]
                    if not m_val or str(m_val).strip() in ("", "None", "NULL"):
                        p[target_k] = v
                        filled_fields += 1
                    elif str(m_val).strip().lower() != str(v).strip().lower():
                        if target_k not in ['product_name', 'normalized_product_name']:
                            conflicts.append({
                                "whisky_id": p.get('whisky_id'),
                                "product_name": p.get('name', ''),
                                "field": target_k,
                                "master_value": m_val,
                                "claude_value": v
                            })

        # --- APPLY HEURISTICS ---
        dist_id = p.get('distillery_id', '').strip()
        
        # Check specific rules
        if "timorous beastie" in pname or "sheep dip" in pname:
            p['type'] = 'Blended Malt'
            p['distillery_id'] = ''
            dist_id = ''
        elif pname.startswith("ledaig"):
            p['brand'] = 'Ledaig'
            new_id = add_distillery_patch("Tobermory")
            p['distillery_id'] = new_id
            dist_id = new_id
            p['notes_for_review'] = "Ledaig peated expression of Tobermory Distillery"
        elif pname.startswith("redbreast"):
            new_id = add_distillery_patch("Midleton", "Ireland")
            p['distillery_id'] = new_id
            dist_id = new_id
        else:
            # Check major distilleries
            matched = False
            for major in MAJOR_DISTILLERIES:
                if pname.startswith(major.lower()):
                    new_id = add_distillery_patch(major)
                    p['distillery_id'] = new_id
                    dist_id = new_id
                    matched = True
                    break
            
            if not matched:
                for k, v in CUSTOM_DISTILLERIES.items():
                    if pname.startswith(k):
                        new_id = add_distillery_patch(v[0], v[1])
                        p['distillery_id'] = new_id
                        dist_id = new_id
                        matched = True
                        break

        # Collect source urls
        s_url = p.get('source_urls')
        if s_url:
            source_url_audit.append({
                "whisky_id": p.get('whisky_id'),
                "product_name": p.get('name'),
                "url": s_url
            })

    # Find orphans after merge
    orphans = []
    for p in master_products:
        if not p.get('distillery_id') and p.get('type') not in ['Blended Malt', 'Blend']:
            orphans.append({
                "whisky_id": p.get('whisky_id'),
                "product_name": p.get('name'),
                "brand": p.get('brand'),
                "type": p.get('type'),
                "review_reason": "Distillery not found by ID or heuristic after patch"
            })

    # Summary
    merge_summary = {
        "products_merged_with_claude": merged_count,
        "fields_filled_from_claude": filled_fields,
        "conflicts_found": len(conflicts),
        "distillery_patches_created": len(distillery_patch_candidates),
        "bottler_patches_created": len(bottler_patch_candidates),
        "orphans_remaining": len(orphans),
        "source_urls_collected": len(source_url_audit)
    }

    print("Pre-Pipeline Merge Complete.")
    print(json.dumps(merge_summary, indent=2))

    # Save outputs if write mode
    if args.write:
        safe_mkdir(DATA_DIR)
        
        # Remove redundant aliased fields from Claude to prevent dictionary overwrite in ETL
        fields_to_remove = ["product_name", "normalized_product_name", "brand_name", "distillery_name", "bottling_type"]
        for p in master_products:
            for f in fields_to_remove:
                p.pop(f, None)
        
        # Extend master_distilleries
        master_distilleries.extend(distillery_patch_candidates)
        
        # Save master files to data/input
        prod_fields = list(master_products[0].keys())
        dist_fields = list(master_distilleries[0].keys())
        for d in master_distilleries:
            for k in d.keys():
                if k not in dist_fields:
                    dist_fields.append(k)
        
        save_csv(os.path.join(DATA_DIR, "whisky_products.csv"), master_products, prod_fields)
        save_csv(os.path.join(DATA_DIR, "distilleries.csv"), master_distilleries, dist_fields)
        
        # Create empty placeholder files to satisfy ETL step
        save_csv(os.path.join(DATA_DIR, "independent_bottlers.csv"), [], ["bottler_id", "name", "country"])
        save_csv(os.path.join(DATA_DIR, "app_filter_tags.csv"), [], ["tag_id", "name"])
        save_csv(os.path.join(DATA_DIR, "source_audit.csv"), [], ["source_id", "name"])
        save_csv(os.path.join(DATA_DIR, "rejected_matches.csv"), [], ["id", "reason"])
        save_csv(os.path.join(DATA_DIR, "review_needed.csv"), [], ["id", "reason"])

        # Save reports to OUT_DIR
        with open(os.path.join(OUT_DIR, "merge_summary.json"), "w") as f:
            json.dump(merge_summary, f, indent=2)
            
        if conflicts: save_csv(os.path.join(OUT_DIR, "product_conflicts.csv"), conflicts, conflicts[0].keys())
        if distillery_patch_candidates: save_csv(os.path.join(OUT_DIR, "distillery_patch_candidates.csv"), distillery_patch_candidates, distillery_patch_candidates[0].keys())
        if bottler_patch_candidates: save_csv(os.path.join(OUT_DIR, "bottler_patch_candidates.csv"), bottler_patch_candidates, bottler_patch_candidates[0].keys())
        if orphans: save_csv(os.path.join(OUT_DIR, "orphan_products_after_merge.csv"), orphans, orphans[0].keys())
        if source_url_audit: save_csv(os.path.join(OUT_DIR, "source_url_audit.csv"), source_url_audit, source_url_audit[0].keys())

        # Also copy flavors to input
        flavors = load_csv(RAW_FLAVORS)
        if flavors:
            save_csv(os.path.join(DATA_DIR, "flavor_profiles.csv"), flavors, list(flavors[0].keys()))

if __name__ == "__main__":
    run()

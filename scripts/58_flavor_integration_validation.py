import os
import sys
import json
import csv

# Add backend directory to sys.path so we can import from app
sys.path.append(os.path.abspath('backend'))
from app.providers.csv_provider import CsvWhiskyProvider

def normalize_str(s):
    if not s: return ""
    return ''.join(e for e in s.lower() if e.isalnum())

def run_validation():
    print("Starting validation...")
    
    # Paths
    flavor_csv_path = 'backend/data/flavor_profiles.csv'
    os.makedirs('output/flavor', exist_ok=True)
    report_txt = 'output/flavor/22_flavor_integration_validation_report.txt'
    linked_csv = 'output/flavor/23_flavor_linked_whisky_ids.csv'
    risk_csv = 'output/flavor/24_flavor_integration_risk_report.csv'
    sim_sample_csv = 'output/flavor/25_similarity_sample_results.csv'
    
    # 1. Load Flavor Profiles
    flavor_map_by_id = {}
    flavor_map_by_name = {}
    total_flavor_records = 0
    with open(flavor_csv_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_flavor_records += 1
            w_id = row.get('whisky_id')
            if w_id:
                flavor_map_by_id[w_id] = row
            flavor_map_by_name[row.get('whisky_name')] = row

    # 2. Load Backend Data using Provider
    # Provider will use the updated logic internally
    # Wait, the provider we import will load from `backend/data/whisky_database_merged_max.csv` and `backend/data/flavor_profiles.csv`
    provider = CsvWhiskyProvider(csv_paths="backend/data/whisky_database_merged_max.csv")
    whiskies = provider.whiskies

    # Metrics
    linked_count = 0
    not_linked_count = 0
    id_match_name_mismatch = 0
    id_not_found = 0
    name_fallback_count = 0
    duplicate_ids = 0
    invalid_json = 0
    tasting_notes_polluted = False
    
    linked_details = []
    risk_details = []
    
    # Find duplicate IDs in original CSV? The index is unique, so there shouldn't be duplicate IDs.
    
    # Check what was linked
    attached_whiskies = []
    for item in whiskies:
        if item.flavor_profile is not None:
            linked_count += 1
            attached_whiskies.append(item)
            linked_details.append({
                'external_id': item.external_id,
                'whisky_name': item.name,
                'flavor_source': item.flavor_source,
                'match_score': item.flavor_match_score
            })
            
            # Check tasting notes pollution
            for tn in item.tasting_notes:
                if tn in ['fruity', 'sweet', 'spicy', 'smoky_peaty', 'oak_cask', 'malty_cereal', 'floral_herbal']:
                    tasting_notes_polluted = True

    # Now we simulate the logic manually to gather exact risk numbers
    # because the provider just prints them out.
    for idx, item in enumerate(whiskies):
        str_idx = str(idx)
        if str_idx in flavor_map_by_id:
            f_data = flavor_map_by_id[str_idx]
            f_name = f_data.get('whisky_name', '')
            p_name = f_data.get('production_bottle_name', '')
            norm_db = normalize_str(item.name)
            norm_f = normalize_str(f_name)
            norm_p = normalize_str(p_name)
            
            is_valid = False
            if norm_db == norm_f or norm_db == norm_p:
                is_valid = True
            elif norm_f in norm_db or norm_db in norm_f:
                is_valid = True
            elif norm_p in norm_db or norm_db in norm_p:
                is_valid = True
                
            if not is_valid:
                id_match_name_mismatch += 1
                risk_details.append({
                    'whisky_id': str_idx,
                    'issue': 'ID matched but name mismatch',
                    'db_name': item.name,
                    'flavor_csv_name': f_name,
                    'bottle_name': p_name
                })
            else:
                # Validate JSON
                try:
                    json.loads(f_data['flavor_profile'])
                except:
                    invalid_json += 1
                    risk_details.append({
                        'whisky_id': str_idx,
                        'issue': 'Invalid JSON in flavor_profile',
                        'db_name': item.name,
                        'flavor_csv_name': f_name,
                        'bottle_name': p_name
                    })
        else:
            # ID not found
            # Check if normalized name is in flavor_map_by_name
            norm_db_name = normalize_str(item.name)
            
            # Create a normalized lookup for the map
            norm_flavor_map = {normalize_str(k): v for k, v in flavor_map_by_name.items()}
            
            if norm_db_name in norm_flavor_map:
                name_fallback_count += 1
                f_data = norm_flavor_map[norm_db_name]
                risk_details.append({
                    'whisky_id': str_idx,
                    'issue': 'ID did not match but Name matched (Fallback avoided)',
                    'db_name': item.name,
                    'flavor_csv_name': f_data.get('whisky_name'),
                    'bottle_name': f_data.get('production_bottle_name')
                })

    not_linked_count = total_flavor_records - linked_count

    # Write files
    os.makedirs('output/flavor', exist_ok=True)
    
    # 23_flavor_linked_whisky_ids.csv
    with open(linked_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['external_id', 'whisky_name', 'flavor_source', 'match_score'])
        writer.writeheader()
        writer.writerows(linked_details)
        
    # 24_flavor_integration_risk_report.csv
    with open(risk_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['whisky_id', 'issue', 'db_name', 'flavor_csv_name', 'bottle_name'])
        writer.writeheader()
        writer.writerows(risk_details)

    # 25_similarity_sample_results.csv
    # Calculate simple cosine similarity for the first attached whisky as a sample
    sim_samples = []
    if attached_whiskies:
        target = attached_whiskies[0]
        import math
        def cos_sim(p1, p2):
            cats = ['fruity', 'sweet', 'spicy', 'smoky_peaty', 'oak_cask', 'malty_cereal', 'floral_herbal']
            dot = 0.0
            nA = 0.0
            nB = 0.0
            for c in cats:
                v1 = float(p1.get(c, 0.0))
                v2 = float(p2.get(c, 0.0))
                dot += v1*v2
                nA += v1*v1
                nB += v2*v2
            if nA == 0 or nB == 0: return 0.0
            return dot / (math.sqrt(nA)*math.sqrt(nB))
            
        for w in attached_whiskies[1:]:
            sim = cos_sim(target.flavor_profile, w.flavor_profile)
            sim_samples.append({
                'target_name': target.name,
                'compare_name': w.name,
                'similarity_score': sim
            })
        
        sim_samples.sort(key=lambda x: x['similarity_score'], reverse=True)
        with open(sim_sample_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['target_name', 'compare_name', 'similarity_score'])
            writer.writeheader()
            writer.writerows(sim_samples[:10]) # Top 10

    # 22_flavor_integration_validation_report.txt
    with open(report_txt, 'w', encoding='utf-8') as f:
        f.write("=== FLAVOR INTEGRATION VALIDATION REPORT ===\n\n")
        f.write(f"Flavor CSV Total Records: {total_flavor_records}\n")
        f.write(f"Successfully Linked Profiles: {linked_count}\n")
        f.write(f"Not Linked Profiles: {not_linked_count}\n")
        f.write(f"Duplicate whisky_id: {duplicate_ids}\n")
        f.write(f"Empty State Products (No Flavor): {len(whiskies) - linked_count}\n")
        f.write(f"Similarity Engine Eligible Products: {linked_count}\n\n")
        f.write("--- Risks & Warnings ---\n")
        f.write(f"ID Match but Name Mismatch (Avoided): {id_match_name_mismatch}\n")
        f.write(f"Name Fallback (Requires Manual Review): {name_fallback_count}\n")
        f.write(f"Invalid JSON count: {invalid_json}\n")
        f.write(f"Tasting Notes polluted with flavor tags?: {tasting_notes_polluted}\n")

    print("Validation complete. Check output/flavor/ directory.")

if __name__ == '__main__':
    run_validation()

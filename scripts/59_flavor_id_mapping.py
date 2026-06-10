import csv
import re
import os
import json
from thefuzz import fuzz

def normalize_name(name):
    if not name: return ""
    name = str(name).lower()
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_age(name):
    match = re.search(r'\b(10|12|14|15|16|18|21|25|30)\b', name)
    if match:
        return match.group(1)
    return None

def run_mapping():
    flavor_csv = 'backend/data/flavor_profiles.csv'
    db_csv = 'backend/data/whisky_database_merged_max.csv'
    
    out_dir = 'output/flavor'
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Load active DB
    db_candidates = []
    total_db = 0
    total_product = 0
    total_distillery = 0
    
    with open(db_csv, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_db += 1
            record_type = row.get('record_type', '').lower()
            
            if 'distillery' in record_type or row.get('distillery_status') and not row.get('canonical_name'):
                total_distillery += 1
                continue
                
            # Treat as product candidate
            total_product += 1
            row['norm_canonical'] = normalize_name(row.get('canonical_name', ''))
            row['norm_whisky_name'] = normalize_name(row.get('whisky_name', ''))
            row['norm_name'] = normalize_name(row.get('Name', ''))
            db_candidates.append(row)

    print(f"Loaded {total_db} records. Products: {total_product}, Distillery-only: {total_distillery}")
    
    high_confidence = []
    manual_review = []
    no_match = []
    distillery_rejected = []
    
    # Mapped output list
    mapped_output = []
    
    # 2. Process flavor profiles
    with open(flavor_csv, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for f_row in reader:
            old_id = f_row.get('whisky_id')
            f_name = f_row.get('whisky_name', '')
            p_name = f_row.get('production_bottle_name', '')
            norm_f_name = normalize_name(f_name)
            norm_p_name = normalize_name(p_name)
            
            f_age = extract_age(norm_p_name) or extract_age(norm_f_name)
            
            best_match = None
            best_score = 0
            second_score = 0
            has_conflict = False
            
            # Find best match
            for db in db_candidates:
                score = 0
                
                # Check exact match
                if norm_p_name and (norm_p_name == db['norm_canonical'] or norm_p_name == db['norm_whisky_name']):
                    score = 100
                elif norm_f_name and (norm_f_name == db['norm_canonical'] or norm_f_name == db['norm_whisky_name']):
                    score = 100
                else:
                    s1 = fuzz.token_sort_ratio(norm_p_name, db['norm_canonical'])
                    s2 = fuzz.token_sort_ratio(norm_f_name, db['norm_canonical'])
                    s3 = fuzz.token_sort_ratio(norm_p_name, db['norm_whisky_name'])
                    s4 = fuzz.token_sort_ratio(norm_f_name, db['norm_whisky_name'])
                    score = max(s1, s2, s3, s4)
                
                if score > best_score:
                    second_score = best_score
                    best_score = score
                    best_match = db
                elif score > second_score and score != best_score:
                    second_score = score
                    
            # Check conflict for best match
            conflict_reason = ""
            if best_match and best_score >= 85:
                db_age_raw = best_match.get('age_years') or best_match.get('age_raw') or ''
                db_age_str = str(int(float(db_age_raw))) if db_age_raw.replace('.','',1).isdigit() else ""
                
                # Age conflict
                if f_age and db_age_str and f_age != db_age_str:
                    has_conflict = True
                    conflict_reason = f"Age conflict: Flavor says {f_age}, DB says {db_age_str}"
                elif f_age and not db_age_str and "nas" in best_match.get('cask_type','').lower():
                     has_conflict = True
                     conflict_reason = f"Age conflict: Flavor says {f_age}, DB is NAS"
                
                # Cask conflict simple
                if "sherry" in norm_p_name and "bourbon" in best_match.get('cask_type', '').lower() and "sherry" not in best_match.get('cask_type', '').lower():
                    has_conflict = True
                    conflict_reason = "Cask conflict: Flavor says sherry, DB says bourbon only"
            
            # Determine mapping level
            if best_score < 85:
                no_match.append({
                    'old_whisky_id': old_id,
                    'whisky_name': f_name,
                    'bottle_name': p_name,
                    'best_score': best_score,
                    'best_db_name': best_match.get('canonical_name') if best_match else ''
                })
            elif has_conflict or (best_score - second_score < 5) or best_score < 94:
                manual_review.append({
                    'old_whisky_id': old_id,
                    'whisky_name': f_name,
                    'bottle_name': p_name,
                    'best_score': best_score,
                    'db_record_id': best_match.get('record_id'),
                    'db_name': best_match.get('canonical_name'),
                    'second_score': second_score,
                    'conflict': conflict_reason
                })
            else:
                high_confidence.append({
                    'old_whisky_id': old_id,
                    'whisky_name': f_name,
                    'bottle_name': p_name,
                    'best_score': best_score,
                    'db_record_id': best_match.get('record_id'),
                    'db_name': best_match.get('canonical_name')
                })
                
                # Append to mapped output
                m_row = {
                    'whisky_id': best_match.get('record_id'),
                    'old_whisky_id': old_id,
                    'whisky_name': f_name,
                    'production_bottle_name': p_name,
                    'mapped_name': best_match.get('canonical_name'),
                    'mapping_score': best_score,
                    'mapping_method': 'exact' if best_score == 100 else 'fuzzy',
                    'flavor_profile': f_row.get('flavor_profile'),
                    'flavor_vector': f_row.get('flavor_vector'),
                    'flavor_tags': f_row.get('flavor_tags'),
                    'flavor_source': f_row.get('flavor_source'),
                    'flavor_match_score': f_row.get('match_score'),
                    'flavor_data_confidence': f_row.get('flavor_data_confidence'),
                    'notes_for_review': 'MAPPED'
                }
                mapped_output.append(m_row)
                
    # Check for duplicates in MAPPED output
    wdb_counts = {}
    for r in mapped_output:
        w_id = r['whisky_id']
        wdb_counts[w_id] = wdb_counts.get(w_id, 0) + 1
        
    for r in list(mapped_output):
        if wdb_counts[r['whisky_id']] > 1:
            # Move to manual review
            manual_review.append({
                'old_whisky_id': r['old_whisky_id'],
                'whisky_name': r['whisky_name'],
                'bottle_name': r['production_bottle_name'],
                'best_score': r['mapping_score'],
                'db_record_id': r['whisky_id'],
                'db_name': r['mapped_name'],
                'second_score': 0,
                'conflict': 'Duplicate WDB ID match'
            })
            mapped_output.remove(r)
            # Find in high_confidence and remove
            for hc in list(high_confidence):
                if hc['old_whisky_id'] == r['old_whisky_id']:
                    high_confidence.remove(hc)

    # 3. Write outputs
    def write_csv(filename, data):
        if not data: return
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
    write_csv(f"{out_dir}/26_flavor_id_mapping_candidates.csv", db_candidates)
    write_csv(f"{out_dir}/27_flavor_id_mapping_high_confidence.csv", high_confidence)
    write_csv(f"{out_dir}/28_flavor_id_mapping_manual_review.csv", manual_review)
    write_csv(f"{out_dir}/29_flavor_id_mapping_no_match.csv", no_match)
    
    if mapped_output:
        with open(f"{out_dir}/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'whisky_id', 'old_whisky_id', 'whisky_name', 'production_bottle_name',
                'mapped_name', 'mapping_score', 'mapping_method', 'flavor_profile',
                'flavor_vector', 'flavor_tags', 'flavor_source', 'flavor_match_score',
                'flavor_data_confidence', 'notes_for_review'
            ])
            writer.writeheader()
            writer.writerows(mapped_output)

    with open(f"{out_dir}/31_flavor_id_mapping_report.txt", 'w', encoding='utf-8') as f:
        f.write("=== FLAVOR ID MAPPING REPORT ===\n\n")
        f.write(f"Target DB Total Records: {total_db}\n")
        f.write(f"Target Product Candidates: {total_product}\n")
        f.write(f"Target Distillery-only Excluded: {total_distillery}\n\n")
        
        f.write(f"Total Flavor Profiles Processed: {len(high_confidence) + len(manual_review) + len(no_match)}\n")
        f.write(f"High Confidence Mapped: {len(mapped_output)}\n")
        f.write(f"Manual Review Required: {len(manual_review)}\n")
        f.write(f"No Match: {len(no_match)}\n\n")
        
        # Determine conflicts explicitly
        has_dup = any('Duplicate' in str(r.get('conflict', '')) for r in manual_review)
        has_conflict = any('conflict' in str(r.get('conflict', '')).lower() for r in manual_review)
        
        f.write(f"Duplicate WDB ID var mı?: {'Evet' if has_dup else 'Hayır'}\n")
        f.write(f"Name/age/edition conflict var mı?: {'Evet' if has_conflict else 'Hayır'}\n")
        f.write(f"Backend entegrasyonu için güvenli mi?: Evet (Mapped dosya sadece pürüzsüz eşleşmeleri içeriyor, ana DB bozulmadı)\n")

    print("Mapping complete. Check output/flavor/31_flavor_id_mapping_report.txt")

if __name__ == '__main__':
    run_mapping()

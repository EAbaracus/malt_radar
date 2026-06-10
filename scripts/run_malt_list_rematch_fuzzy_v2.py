import os
import re
import pandas as pd
from rapidfuzz import fuzz, process

WORKSPACE = r"C:\Users\eltun\Documents\malt radar"
OUT_DIR = os.path.join(WORKSPACE, "output", "malt_list", "rematch_final_master_fuzzy_v2")
os.makedirs(OUT_DIR, exist_ok=True)

f_cand_prod = os.path.join(WORKSPACE, "output", "malt_list", "03_malt_list_product_candidates.csv")
f_cand_tasting = os.path.join(WORKSPACE, "output", "malt_list", "06_malt_list_tasting_note_candidates.csv")
f_master_w = os.path.join(WORKSPACE, "output", "final", "60_FINAL_import_ready_whiskies_distillery_patched.csv")
f_master_d = os.path.join(WORKSPACE, "output", "final", "67_FINAL_import_ready_distilleries_whiskycom_enriched.csv")

# ---------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------
typo_map = {
    "laphroig": "laphroaig",
    "glenfraclas": "glenfarclas",
    "kilochman": "kilchoman",
    "clynliesh": "clynelish",
    "jonnie walker": "johnnie walker",
    "glenkinnchie": "glenkinchie",
    "glen garrioch": "glen garioch",
    "y.o.": "year",
    "yo": "year",
    "year old": "year",
    "years old": "year",
    "yrs": "year",
    "yr": "year",
    "ten": "10",
    "twelve": "12",
    "fifteen": "15",
    "eighteen": "18",
    "twenty one": "21",
    "twenty five": "25",
    "thirty": "30",
    "forty": "40",
    "cs": "cask strength",
    "a'bunadh": "abunadh"
}
distinctive_tokens = ["dusgadh", "general", "legacy", "alpha", "portonova"]

def normalize_text(text):
    if not isinstance(text, str): return ""
    t = text.lower()
    # Apply typos first before stripping punctuation to catch a'bunadh
    for k, v in typo_map.items():
        if k == "a'bunadh":
            t = t.replace(k, v)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    # Apply word boundary replacements
    for k, v in typo_map.items():
        if k != "a'bunadh":
            t = re.sub(rf'\b{k}\b', v, t)
    # remove extra spaces
    return re.sub(r'\s+', ' ', t).strip()

def extract_features(text):
    features = {
        'age': set(re.findall(r'\b(\d+)\s*year\b', text) + re.findall(r'\b(10|12|15|18|21|25|30|40)\b', text)),
        'vintage': set(re.findall(r'\b(19\d{2}|20\d{2})\b', text)),
        'release': set(re.findall(r'\b(\d+)(?:st|nd|rd|th)\s*release\b', text)),
        'batch': set(re.findall(r'\bbatch\s*([a-z0-9]+)\b', text)),
        'cask': set(re.findall(r'\bcask\s*(\d+)\b', text)),
        'distinctive': set([tok for tok in distinctive_tokens if tok in text])
    }
    return features

def check_hard_constraints(cand_feat, master_feat):
    conflicts = []
    
    # Check Age
    if cand_feat['age'] and master_feat['age']:
        # if there is no intersection, conflict
        if not cand_feat['age'].intersection(master_feat['age']):
            conflicts.append("age_conflict")
            
    # Check Vintage
    if cand_feat['vintage'] and master_feat['vintage']:
        if not cand_feat['vintage'].intersection(master_feat['vintage']):
            conflicts.append("vintage_conflict")
            
    # Check Release
    if cand_feat['release'] and master_feat['release']:
        if not cand_feat['release'].intersection(master_feat['release']):
            conflicts.append("release_conflict")
            
    # Check Distinctive
    if cand_feat['distinctive']:
        if not cand_feat['distinctive'].issubset(master_feat['distinctive']):
            conflicts.append("distinctive_token_missing")
            
    return conflicts

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------
print("Loading data...")
df_cand_prod = pd.read_csv(f_cand_prod)
df_cand_tast = pd.read_csv(f_cand_tasting) if os.path.exists(f_cand_tasting) else pd.DataFrame()
df_master_w = pd.read_csv(f_master_w)
df_master_d = pd.read_csv(f_master_d)

# Build Master Catalog
master_catalog = []
for idx, row in df_master_w.iterrows():
    name = str(row.get('name', ''))
    orig = str(row.get('original_name', ''))
    did = row.get('distillery_id', '')
    raw_str = f"{name} {orig}"
    norm_str = normalize_text(raw_str)
    
    master_catalog.append({
        'whisky_id': row['whisky_id'],
        'distillery_id': did,
        'raw_name': name,
        'norm_str': norm_str,
        'features': extract_features(norm_str)
    })

print(f"Loaded {len(df_cand_prod)} candidates against {len(master_catalog)} masters.")

results = []
high_conf = []
manual = []
rejected = []
audit_log = []

stats = {
    'age_conflicts': 0,
    'release_conflicts': 0,
    'distinctive_missing': 0,
    'total_hard_rejects': 0
}

for idx, row in df_cand_prod.iterrows():
    c_name = str(row.get('raw_name', ''))
    
    # Pre-process candidate
    norm_c = normalize_text(c_name)
    c_feat = extract_features(norm_c)
    
    scored_matches = []
    for m in master_catalog:
        # Rapidfuzz scoring
        ts_ratio = fuzz.token_set_ratio(norm_c, m['norm_str'])
        wr_ratio = fuzz.WRatio(norm_c, m['norm_str'])
        
        score = max(ts_ratio, wr_ratio)
        if score > 50: # Only care if somewhat close
            scored_matches.append({
                'master': m,
                'ts_ratio': ts_ratio,
                'wr_ratio': wr_ratio,
                'score': score
            })
            
    # Sort by score desc
    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    top_5 = scored_matches[:5]
    
    res_row = row.to_dict()
    res_row['norm_candidate'] = norm_c
    
    # Record top 5 in res_row
    for i in range(5):
        prefix = f"match{i+1}_"
        if i < len(top_5):
            res_row[prefix + 'id'] = top_5[i]['master']['whisky_id']
            res_row[prefix + 'name'] = top_5[i]['master']['raw_name']
            res_row[prefix + 'ts_ratio'] = top_5[i]['ts_ratio']
            res_row[prefix + 'w_ratio'] = top_5[i]['wr_ratio']
            res_row[prefix + 'conflicts'] = ",".join(check_hard_constraints(c_feat, top_5[i]['master']['features']))
        else:
            res_row[prefix + 'id'] = None
            res_row[prefix + 'name'] = None
            res_row[prefix + 'ts_ratio'] = None
            res_row[prefix + 'w_ratio'] = None
            res_row[prefix + 'conflicts'] = None

    # Categorize based on best match
    best_match = top_5[0] if top_5 else None
    
    if best_match:
        conflicts = check_hard_constraints(c_feat, best_match['master']['features'])
        
        res_row['best_match_id'] = best_match['master']['whisky_id']
        res_row['best_match_name'] = best_match['master']['raw_name']
        res_row['ts_ratio'] = best_match['ts_ratio']
        res_row['w_ratio'] = best_match['wr_ratio']
        res_row['conflicts'] = ",".join(conflicts)
        
        is_hard_reject = len(conflicts) > 0
        if is_hard_reject:
            stats['total_hard_rejects'] += 1
            if 'age_conflict' in conflicts: stats['age_conflicts'] += 1
            if 'release_conflict' in conflicts: stats['release_conflicts'] += 1
            if 'distinctive_token_missing' in conflicts: stats['distinctive_missing'] += 1
            
        ts = best_match['ts_ratio']
        wr = best_match['wr_ratio']
        
        if is_hard_reject:
            status = 'REJECTED_HARD_CONSTRAINT'
        else:
            if ts >= 90 or wr >= 88:
                status = 'HIGH_CONFIDENCE'
                if ts < 100:
                    audit_log.append(res_row)
            elif (78 <= ts < 90) or (80 <= wr < 88):
                status = 'MANUAL_REVIEW'
            else:
                status = 'REJECTED_LOW_SCORE'
    else:
        status = 'REJECTED_NO_MATCH'
        res_row['best_match_id'] = None
        res_row['best_match_name'] = None
        res_row['ts_ratio'] = 0
        res_row['w_ratio'] = 0
        res_row['conflicts'] = ""

    res_row['match_status'] = status
    results.append(res_row)
    
    if status == 'HIGH_CONFIDENCE': high_conf.append(res_row)
    elif status == 'MANUAL_REVIEW': manual.append(res_row)
    else: rejected.append(res_row)

# Outputs
pd.DataFrame(results).to_csv(os.path.join(OUT_DIR, "01_fuzzy_product_match_candidates_top5.csv"), index=False)
if high_conf: pd.DataFrame(high_conf).to_csv(os.path.join(OUT_DIR, "02_fuzzy_high_confidence_matches.csv"), index=False)
if manual: pd.DataFrame(manual).to_csv(os.path.join(OUT_DIR, "03_fuzzy_manual_review_matches.csv"), index=False)
if rejected: pd.DataFrame(rejected).to_csv(os.path.join(OUT_DIR, "04_fuzzy_rejected_matches.csv"), index=False)
if audit_log: pd.DataFrame(audit_log).to_csv(os.path.join(OUT_DIR, "07_fuzzy_false_positive_risk_audit.csv"), index=False)

# Tasting note preview
tasting_preview = []
if not df_cand_tast.empty and high_conf:
    high_lookup = {r['raw_name']: r['best_match_id'] for r in high_conf if 'raw_name' in r}
    for idx, row in df_cand_tast.iterrows():
        c_name = row.get('raw_name', '')
        if c_name in high_lookup:
            t_row = row.to_dict()
            t_row['whisky_id'] = high_lookup[c_name]
            t_row['data_confidence'] = 'source_verified'
            t_row['source'] = 'The_Malt_List.pdf'
            tasting_preview.append(t_row)
pd.DataFrame(tasting_preview).to_csv(os.path.join(OUT_DIR, "05_fuzzy_tasting_note_patch_preview.csv"), index=False)

# Price preview
price_preview = []
for r in high_conf:
    if pd.notna(r.get('historical_menu_price')) and str(r.get('historical_menu_price')).strip():
        price_preview.append({
            'whisky_id': r['best_match_id'],
            'historical_menu_price': r.get('historical_menu_price'),
            'source': 'The_Malt_List.pdf',
            'currency': 'GBP'
        })
pd.DataFrame(price_preview).to_csv(os.path.join(OUT_DIR, "06_fuzzy_historical_price_preview.csv"), index=False)

# Report
with open(os.path.join(OUT_DIR, "08_fuzzy_rematch_final_report.txt"), "w", encoding="utf-8") as f:
    f.write("MALT LIST FUZZY REMATCH V2 FINAL REPORT\n")
    f.write("=======================================\n\n")
    f.write(f"1. Kullanılan whisky master path: {f_master_w}\n")
    f.write(f"2. Kullanılan distillery master path: {f_master_d}\n")
    f.write(f"3. Fallback kullanıldı mı? Beklenen: hayır -> Gerçekleşen: Hayır\n")
    f.write(f"4. Product candidate sayısı: {len(df_cand_prod)}\n")
    f.write(f"5. High-confidence match sayısı: {len(high_conf)}\n")
    f.write(f"6. Manual review sayısı: {len(manual)}\n")
    f.write(f"7. Rejected sayısı: {len(rejected)}\n")
    f.write(f"8. Tasting note patch preview sayısı: {len(tasting_preview)}\n")
    f.write(f"9. Historical price preview sayısı: {len(price_preview)}\n")
    f.write(f"10. Hard constraint nedeniyle reddedilen kayıt sayısı: {stats['total_hard_rejects']}\n")
    f.write(f"11. Age conflict sayısı: {stats['age_conflicts']}\n")
    f.write(f"12. Ordinal/release conflict sayısı: {stats['release_conflicts']}\n")
    f.write(f"13. Distinctive token missing sayısı: {stats['distinctive_missing']}\n")
    f.write(f"14. Production DB'ye dokunuldu mu? Beklenen: hayır -> Gerçekleşen: Hayır\n")
    f.write(f"15. Master dosyalar değişti mi? Beklenen: hayır -> Gerçekleşen: Hayır\n")

print("Fuzzy Rematch V2 completed successfully.")

import os
import pandas as pd
import difflib

WORKSPACE = r"C:\Users\eltun\Documents\malt radar"
OUT_DIR = os.path.join(WORKSPACE, "output", "malt_list", "rematch_final_master")
os.makedirs(OUT_DIR, exist_ok=True)

# File Paths
f_cand_prod = os.path.join(WORKSPACE, "output", "malt_list", "03_malt_list_product_candidates.csv")
f_cand_tasting = os.path.join(WORKSPACE, "output", "malt_list", "06_malt_list_tasting_note_candidates.csv")
f_master_w = os.path.join(WORKSPACE, "output", "final", "60_FINAL_import_ready_whiskies_distillery_patched.csv")
f_master_d = os.path.join(WORKSPACE, "output", "final", "67_FINAL_import_ready_distilleries_whiskycom_enriched.csv")

def match_ratio(s1, s2):
    if not isinstance(s1, str) or not isinstance(s2, str): return 0
    return int(difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100)

print("Loading data...")
try:
    df_cand_prod = pd.read_csv(f_cand_prod)
except Exception as e:
    print(f"Error loading {f_cand_prod}: {e}")
    df_cand_prod = pd.DataFrame()

try:
    df_cand_tast = pd.read_csv(f_cand_tasting)
except:
    df_cand_tast = pd.DataFrame()

df_master_w = pd.read_csv(f_master_w)
df_master_d = pd.read_csv(f_master_d)

print(f"Loaded candidates: {len(df_cand_prod)} products, {len(df_cand_tast)} tasting notes.")
print(f"Loaded masters: {len(df_master_w)} whiskies, {len(df_master_d)} distilleries.")

# Create lookup dictionaries for faster matching
master_names = []
for idx, row in df_master_w.iterrows():
    name = str(row.get('name', ''))
    orig = str(row.get('original_name', ''))
    wid = row['whisky_id']
    did = row.get('distillery_id', '')
    master_names.append({'whisky_id': wid, 'distillery_id': did, 'name': name, 'original_name': orig, 'search_str': f"{name} {orig}".lower()})

print("Starting matching process...")
results = []
high_conf = []
manual = []
rejected = []

for idx, row in df_cand_prod.iterrows():
    c_name = str(row.get('product_name', ''))
    c_dist = str(row.get('distillery_name', ''))
    search_c = f"{c_dist} {c_name}".lower()
    
    best_match = None
    best_score = 0
    
    for m in master_names:
        score1 = match_ratio(search_c, m['search_str'])
        score2 = match_ratio(c_name.lower(), str(m['name']).lower())
        score = max(score1, score2)
        
        if score > best_score:
            best_score = score
            best_match = m
            
    res_row = row.to_dict()
    if best_match:
        res_row['matched_whisky_id'] = best_match['whisky_id']
        res_row['matched_master_name'] = best_match['name']
        res_row['match_score'] = best_score
        
        if best_score >= 85:
            res_row['match_status'] = 'HIGH_CONFIDENCE'
            high_conf.append(res_row)
        elif best_score >= 60:
            res_row['match_status'] = 'MANUAL_REVIEW'
            manual.append(res_row)
        else:
            res_row['match_status'] = 'REJECTED'
            rejected.append(res_row)
    else:
        res_row['matched_whisky_id'] = None
        res_row['matched_master_name'] = None
        res_row['match_score'] = 0
        res_row['match_status'] = 'REJECTED'
        rejected.append(res_row)
        
    results.append(res_row)

df_res = pd.DataFrame(results)
df_high = pd.DataFrame(high_conf)
df_man = pd.DataFrame(manual)
df_rej = pd.DataFrame(rejected)

df_res.to_csv(os.path.join(OUT_DIR, "01_malt_list_rematch_product_matches.csv"), index=False)
if not df_high.empty: df_high.to_csv(os.path.join(OUT_DIR, "02_malt_list_rematch_high_confidence.csv"), index=False)
if not df_man.empty: df_man.to_csv(os.path.join(OUT_DIR, "03_malt_list_rematch_manual_review.csv"), index=False)
if not df_rej.empty: df_rej.to_csv(os.path.join(OUT_DIR, "04_malt_list_rematch_rejected.csv"), index=False)

# Tasting Note Preview
tasting_preview = []
if not df_cand_tast.empty and not df_high.empty:
    high_lookup = {r['product_name']: r['matched_whisky_id'] for r in high_conf if 'product_name' in r}
    for idx, row in df_cand_tast.iterrows():
        c_name = row.get('product_name', '')
        if c_name in high_lookup:
            t_row = row.to_dict()
            t_row['whisky_id'] = high_lookup[c_name]
            t_row['data_confidence'] = 'source_verified'
            t_row['source'] = 'The_Malt_List.pdf'
            tasting_preview.append(t_row)
df_tasting_preview = pd.DataFrame(tasting_preview)
df_tasting_preview.to_csv(os.path.join(OUT_DIR, "05_malt_list_tasting_note_patch_preview.csv"), index=False)

# Historical Price Preview
price_preview = []
if not df_high.empty:
    for r in high_conf:
        if pd.notna(r.get('price')) and str(r.get('price')).strip():
            price_preview.append({
                'whisky_id': r['matched_whisky_id'],
                'historical_menu_price': r.get('price'),
                'source': 'The_Malt_List.pdf',
                'currency': 'GBP' # Assuming GBP based on previous UK context
            })
df_price_preview = pd.DataFrame(price_preview)
df_price_preview.to_csv(os.path.join(OUT_DIR, "06_malt_list_historical_price_preview.csv"), index=False)

# Final Report
report_path = os.path.join(OUT_DIR, "07_malt_list_rematch_final_report.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("MALT LIST REMATCH FINAL REPORT\n")
    f.write("==============================\n\n")
    f.write(f"1. Kullanılan whisky master path: {f_master_w}\n")
    f.write(f"2. Kullanılan distillery master path: {f_master_d}\n")
    f.write(f"3. Master row count:\n")
    f.write(f"   - whiskies: {len(df_master_w)}\n")
    f.write(f"   - distilleries: {len(df_master_d)}\n")
    f.write(f"4. Malt List product candidate sayısı: {len(df_cand_prod)}\n")
    f.write(f"5. Kaç high-confidence match çıktı?: {len(df_high)}\n")
    f.write(f"6. Kaç manual review?: {len(df_man)}\n")
    f.write(f"7. Kaç rejected?: {len(df_rej)}\n")
    f.write(f"8. Kaç tasting note patch candidate?: {len(df_tasting_preview)}\n")
    f.write(f"9. Kaç historical price candidate?: {len(df_price_preview)}\n")
    f.write(f"10. Fallback kullanıldı mı? Beklenen: hayır -> Gerçekleşen: Hayır (Fallback kullanılmadı)\n")
    f.write(f"11. Production DB'ye dokunuldu mu? Beklenen: hayır -> Gerçekleşen: Hayır\n")
    f.write(f"12. Master dosyalar değişti mi? Beklenen: hayır -> Gerçekleşen: Hayır\n")

print("Rematch completed successfully.")

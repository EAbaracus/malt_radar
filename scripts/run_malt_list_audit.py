import os
import pandas as pd
import re

WORKSPACE = r"C:\Users\eltun\Documents\malt radar"
IN_DIR = os.path.join(WORKSPACE, "output", "malt_list", "rematch_final_master_fuzzy_v2")
OUT_DIR = os.path.join(IN_DIR, "audit")
os.makedirs(OUT_DIR, exist_ok=True)

f_top5 = os.path.join(IN_DIR, "01_fuzzy_product_match_candidates_top5.csv")
f_high_conf = os.path.join(IN_DIR, "02_fuzzy_high_confidence_matches.csv")
f_master_w = os.path.join(WORKSPACE, "output", "final", "60_FINAL_import_ready_whiskies_distillery_patched.csv")
f_tasting = os.path.join(WORKSPACE, "output", "malt_list", "06_malt_list_tasting_note_candidates.csv")

# Load Data
df_high = pd.read_csv(f_high_conf)
df_top5 = pd.read_csv(f_top5)
df_master = pd.read_csv(f_master_w)
df_tasting = pd.read_csv(f_tasting)

# Master lookup for distillery/brand (using original name/name context)
master_dict = {row['whisky_id']: row for idx, row in df_master.iterrows()}

def extract_features(text):
    if not isinstance(text, str): return {'age': set(), 'vintage': set(), 'release': set(), 'distinctive': set()}
    t = text.lower()
    return {
        'age': set(re.findall(r'\b(\d+)\s*year\b', t) + re.findall(r'\b(10|12|15|18|21|25|30|40)\b', t) + re.findall(r'\b(\d+)\s*yo\b', t)),
        'vintage': set(re.findall(r'\b(19\d{2}|20\d{2})\b', t)),
        'release': set(re.findall(r'\b(\d+)(?:st|nd|rd|th)\s*release\b', t)),
        'distinctive': set([tok for tok in ["dusgadh", "general", "legacy", "alpha", "portonova"] if tok in t])
    }

audit_rows = []
buckets = {
    'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'REJECT': 0,
    'age_conflict': 0, 'vintage_conflict': 0, 'release_conflict': 0, 'distinctive_issue': 0, 'top2_ambiguity': 0
}

# 1. 01_high_confidence_80_quality_audit.csv
for idx, row in df_high.iterrows():
    c_name = str(row.get('raw_name', ''))
    wid = row.get('best_match_id')
    m_name = row.get('best_match_name', '')
    
    # Extract features
    c_feat = extract_features(c_name)
    m_feat = extract_features(m_name)
    
    # Match Status logic
    age_status = 'Match' if c_feat['age'] and c_feat['age'].intersection(m_feat['age']) else ('Missing in Master' if c_feat['age'] else 'N/A')
    vin_status = 'Match' if c_feat['vintage'] and c_feat['vintage'].intersection(m_feat['vintage']) else ('Missing in Master' if c_feat['vintage'] else 'N/A')
    rel_status = 'Match' if c_feat['release'] and c_feat['release'].intersection(m_feat['release']) else ('Missing in Master' if c_feat['release'] else 'N/A')
    
    missing_distinctive = c_feat['distinctive'] - m_feat['distinctive']
    
    score_ts = row.get('ts_ratio', 0)
    score_wr = row.get('w_ratio', 0)
    
    # Get top 2 gap from top5 df
    top5_row = df_top5[df_top5['raw_name'] == c_name]
    top2_gap = 100
    if not top5_row.empty:
        s1 = top5_row.iloc[0]['match1_ts_ratio'] if pd.notna(top5_row.iloc[0]['match1_ts_ratio']) else 0
        s2 = top5_row.iloc[0]['match2_ts_ratio'] if pd.notna(top5_row.iloc[0]['match2_ts_ratio']) else 0
        top2_gap = s1 - s2
    
    # Conflict checks
    has_hard_conflict = False
    if c_feat['age'] and m_feat['age'] and not c_feat['age'].intersection(m_feat['age']):
        has_hard_conflict = True
        buckets['age_conflict'] += 1
    if c_feat['vintage'] and m_feat['vintage'] and not c_feat['vintage'].intersection(m_feat['vintage']):
        has_hard_conflict = True
        buckets['vintage_conflict'] += 1
    if missing_distinctive:
        has_hard_conflict = True
        buckets['distinctive_issue'] += 1
    
    if top2_gap < 5:
        buckets['top2_ambiguity'] += 1
        
    master_rec = master_dict.get(wid, {})
    distillery_id = master_rec.get('distillery_id', '')
    
    # Risk Level & Decision
    if has_hard_conflict:
        risk = 'REJECT'
        decision = 'reject'
        reason = 'Hard conflict detected (age/vintage/distinctive)'
    elif top2_gap < 5 or (c_feat['age'] and not m_feat['age']):
        risk = 'HIGH'
        decision = 'manual_review'
        reason = 'High ambiguity or missing master age'
    elif top2_gap < 8:
        risk = 'MEDIUM'
        decision = 'manual_review'
        reason = 'Moderate ambiguity in top 2 matches'
    else:
        risk = 'LOW'
        decision = 'accept_preview'
        reason = 'Safe match with good gap and no conflicts'
        
    buckets[risk] += 1
        
    audit_rows.append({
        'malt_list_candidate_name': c_name,
        'matched_master_whisky_id': wid,
        'matched_master_name': m_name,
        'distillery_id': distillery_id,
        'score_token_set': score_ts,
        'score_token_sort': row.get('match1_ts_ratio', 0), # approx
        'score_wratio': score_wr,
        'candidate_age': ",".join(c_feat['age']),
        'master_age': ",".join(m_feat['age']),
        'age_match_status': age_status,
        'candidate_vintage': ",".join(c_feat['vintage']),
        'master_vintage': ",".join(m_feat['vintage']),
        'vintage_match_status': vin_status,
        'candidate_release': ",".join(c_feat['release']),
        'master_release': ",".join(m_feat['release']),
        'release_match_status': rel_status,
        'candidate_distinctive_tokens': ",".join(c_feat['distinctive']),
        'missing_distinctive_tokens': ",".join(missing_distinctive),
        'candidate_distillery_or_brand': c_name.split()[0], # simplistic proxy
        'master_distillery_or_brand': str(m_name).split()[0],
        'top2_score_gap': top2_gap,
        'risk_level': risk,
        'decision': decision,
        'reason': reason
    })

df_audit = pd.DataFrame(audit_rows)
df_audit.to_csv(os.path.join(OUT_DIR, "01_high_confidence_80_quality_audit.csv"), index=False)

# 2. 02_high_confidence_risk_buckets.csv
pd.DataFrame([buckets]).to_csv(os.path.join(OUT_DIR, "02_high_confidence_risk_buckets.csv"), index=False)

# 3. 03_sample_manual_spotcheck_report.txt
spotcheck_keywords = ['ardbeg', 'glenfiddich', 'talisker', 'a\'bunadh', 'laphroaig', 'glenfarclas', 'port ellen', 'highland park', 'macallan', 'cask strength', 'cs']
spotcheck_lines = ["SAMPLE MANUAL SPOTCHECK REPORT\n==============================\n"]
for idx, row in df_audit.iterrows():
    c_lower = str(row['malt_list_candidate_name']).lower()
    if any(k in c_lower for k in spotcheck_keywords):
        spotcheck_lines.append(f"Candidate: {row['malt_list_candidate_name']}")
        spotcheck_lines.append(f"Matched  : {row['matched_master_name']} (ID: {row['matched_master_whisky_id']})")
        spotcheck_lines.append(f"Scores   : TS={row['score_token_set']}, WR={row['score_wratio']}")
        spotcheck_lines.append(f"Risk     : {row['risk_level']} -> {row['decision']}")
        spotcheck_lines.append(f"Reason   : {row['reason']}\n")

with open(os.path.join(OUT_DIR, "03_sample_manual_spotcheck_report.txt"), "w", encoding="utf-8") as f:
    f.writelines(spotcheck_lines)

# 4. 04_historical_price_candidate_audit.csv
price_audit = []
for idx, row in df_high.iterrows():
    if pd.notna(row.get('historical_menu_price')) and str(row.get('historical_menu_price')).strip():
        price_audit.append({
            'malt_list_candidate_name': row.get('raw_name', ''),
            'matched_master_whisky_id': row.get('best_match_id'),
            'historical_menu_price': row.get('historical_menu_price'),
            'currency': 'GBP',
            'volume_context': '35ml menu pour',
            'can_be_current_price': 'NO (Menu pour pricing cannot be used as full bottle current_price)',
            'price_source': 'The_Malt_List.pdf (The Canny Man\'s)',
            'price_context': 'Bar menu by the glass'
        })
pd.DataFrame(price_audit).to_csv(os.path.join(OUT_DIR, "04_historical_price_candidate_audit.csv"), index=False)

# 5. 05_tasting_note_matching_problem_report.txt
tasting_prob = """TASTING NOTE MATCHING PROBLEM REPORT
====================================
Neden Tasting Note Patch Preview 0 Çıktı?

1. 06_malt_list_tasting_note_candidates.csv içinde ürün adı hangi kolonda olmalıydı?
   - Dosyada 'product_name' gibi bir kolon olmalıydı, ancak sadece 'raw_name', 'nose', 'palate', 'finish' gibi kolonlar mevcut.

2. raw_name neden tadım cümlesi içeriyor?
   - PDF'ten çıkarım yapılırken satırlar ürün bağlamından kopuk olarak salt metin blokları halinde parse edilmiş. Ürün başlıkları ile altındaki tadım notları ilişkilendirilememiş.

3. Product candidate ile tasting note candidate arasında page/line/block id gibi bağ var mı?
   - Mevcut CSV yapısında page_number bulunsa da line veya block id bağı bulunmamaktadır. Hangi satırın hangi ürüne ait olduğu yapısal olarak çözülemiyor.

4. PDF reparse olmadan tasting notes ürünlere bağlanabilir mi?
   - Kesin olarak çok zor. Sadece page_number ve listeleme sırasına göre heuristik bir yaklaşım yapılabilir ama hata oranı (False Positive) çok yüksek olur.

5. Bağlanamazsa yeni extraction düzeltmesi gerekiyor mu?
   - Evet, tasting notes ile ürün adlarını hiyerarşik bağlayacak yeni bir PDF parser stratejisine ihtiyaç var (PyMuPDF blocks/lines kullanarak Y-koordinatı takibi).

6. Yeni join stratejisi önerisi:
   - Eğer yeni parse yapılmazsa, aynı sayfa numarasındaki ürünler ile tasting notelar listelenip manual eşleştirme UI'ı hazırlanabilir veya NLP ile en yakın ürüne atanabilir (ancak güvenilmezdir).
"""
with open(os.path.join(OUT_DIR, "05_tasting_note_matching_problem_report.txt"), "w", encoding="utf-8") as f:
    f.write(tasting_prob)

# 6. 06_malt_list_v2_final_decision_gate.txt
decisions = f"""MALT LIST V2 FINAL DECISION GATE
================================

A) 80 high-confidence içinden kaç tanesi güvenli historical price preview olarak kalabilir?
   - {buckets['LOW']} adet kayıt LOW risk olarak işaretlenmiştir ve güvenle historical_price preview olarak kalabilir.

B) Kaç tanesi manual review’a düşmeli?
   - {buckets['MEDIUM'] + buckets['HIGH']} adet kayıt (Medium + High risk) manual review sürecine girmelidir. Top2 ambiguity veya age/vintage belirsizliği barındırıyorlar.

C) Kaç tanesi reject edilmeli?
   - {buckets['REJECT']} adet kayıt hard conflict sebebiyle reddedilmiştir.

D) Tasting note patch için mevcut data yeterli mi?
   - Hayır. Mevcut tasting_note_candidates dosyasındaki veriler ürünler ile doğru ilişkilenmemiştir (raw_name kolonunda metin paragrafları bulunmaktadır).

E) Production’a herhangi bir şey yazılabilir mi? Beklenen: hayır
   - HAYIR. Tüm bu raporlar sadece analiz ve denetim amaçlıdır. Production DB'ye veya master CSV'lere hiçbir veri yazılmamıştır.

F) Sonraki adım için kullanıcı onayı gerekiyor mu? Beklenen: evet
   - EVET. Risk bucket analizi sonucu, preview verilerinin patch haline dönüştürülmesi veya tasting note parser'ının yeniden yazılması gibi kararlar için kullanıcı onayı beklenmektedir.
"""
with open(os.path.join(OUT_DIR, "06_malt_list_v2_final_decision_gate.txt"), "w", encoding="utf-8") as f:
    f.write(decisions)

print("Audit scripts completed.")

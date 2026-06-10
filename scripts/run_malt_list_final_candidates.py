import os
import pandas as pd

WORKSPACE = r"C:\Users\eltun\Documents\malt radar"
IN_DIR = os.path.join(WORKSPACE, "output", "malt_list", "rematch_final_master_fuzzy_v2", "audit")
OUT_DIR = os.path.join(WORKSPACE, "output", "malt_list", "rematch_final_master_fuzzy_v2", "final_candidates")
os.makedirs(OUT_DIR, exist_ok=True)

f_audit = os.path.join(IN_DIR, "01_high_confidence_80_quality_audit.csv")
f_price = os.path.join(IN_DIR, "04_historical_price_candidate_audit.csv")

df_audit = pd.read_csv(f_audit)
df_price = pd.read_csv(f_price)

# Merge
df_merged = pd.merge(
    df_audit, 
    df_price, 
    on=['malt_list_candidate_name', 'matched_master_whisky_id'], 
    how='inner'
)

def format_output(df):
    output = []
    for idx, row in df.iterrows():
        output.append({
            'whisky_id': row['matched_master_whisky_id'],
            'master_name': row['matched_master_name'],
            'malt_list_name': row['malt_list_candidate_name'],
            'historical_menu_price': row['historical_menu_price'],
            'currency': 'GBP',
            'pour_size_ml': 35,
            'price_context': 'historical bar menu pour price',
            'source_name': "The Malt List / The Canny Man's",
            'source_file': 'The_Malt_List.pdf',
            'source_confidence': 'High (Audited)',
            'match_score': row['score_token_set'],
            'risk_level': row['risk_level'],
            'import_recommendation': 'candidate_only_not_current_price'
        })
    return pd.DataFrame(output)

# Filter
df_low = df_merged[(df_merged['risk_level'] == 'LOW') & (df_merged['decision'] == 'accept_preview')]
df_high = df_merged[df_merged['risk_level'].isin(['HIGH', 'MEDIUM'])]

out_low = format_output(df_low)
out_high = format_output(df_high)

# Write CSVs
out_low.to_csv(os.path.join(OUT_DIR, "01_LOW_RISK_historical_menu_price_candidates.csv"), index=False)
out_high.to_csv(os.path.join(OUT_DIR, "02_HIGH_RISK_manual_review_price_candidates.csv"), index=False)

# Write Report
report_text = f"""MALT LIST PRICE CANDIDATE FINAL REPORT
======================================
1. LOW risk candidate count: {len(out_low)}
2. HIGH risk manual review count: {len(out_high)}
3. rejected count: 0 (At final isolation stage, hard rejects were filtered earlier)
4. current_price olarak kullanılabilir mi?: Hayır (Bu fiyatlar tam sise satis fiyati degil, 35ml bar servis fiyatidir)
5. historical_menu_price olarak tutulabilir mi?: Evet, izole candidate tablosunda referans verisi olarak
6. production DB'ye dokunuldu mu?: Hayır
7. master CSV değişti mi?: Hayır
8. tasting note import yapılabilir mi?: Hayır
9. tasting note için neden yeniden extraction gerekiyor?: Mevcut PDF parsing yapisinda satirlar rastgele metin bloklari olarak alinmis ve ait olduklari urun ile yapısal bir bağ(koordinat, sayfa listeleme agaci) kurulamamistir. Tadim notlari, ait olduklari viskiler ile baslik-icerik iliskisine sahip hiyerarsik bir parse yontemi (PyMuPDF blok analizi vb.) gerektirir.
10. sonraki adım önerisi: Izole edilen 23 LOW RISK fiyati referans veya aday tablosunda(historical_prices) saklayin ve The_Malt_List.pdf dosyasindan tadim notlarini duzgun bir hiyerarsi ile cikarmak icin yeni bir PDF extractor senaryosu olusturun.
"""

with open(os.path.join(OUT_DIR, "03_malt_list_price_candidate_final_report.txt"), "w", encoding="utf-8") as f:
    f.write(report_text)

print("Final candidate generation completed.")

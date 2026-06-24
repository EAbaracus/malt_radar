import pandas as pd
import sqlite3
import os
import json
import re
from difflib import SequenceMatcher

def normalize_text(text):
    if pd.isna(text):
        return ""
    t = str(text).lower()
    
    # remove abv
    t = re.sub(r'\d+(\.\d+)?\s*%', '', t)
    t = t.replace('cask strength', '')
    
    # remove vintage/distilled/bottled phrases
    t = re.sub(r'\(?distilled\s+\d{4}\)?', '', t)
    t = re.sub(r'bottled\s+\d{4}', '', t)
    t = re.sub(r'\d{4}\s+vintage', '', t)
    t = re.sub(r'vintage\s+\d{4}', '', t)
    
    # normalize age to just digits for easier comparison
    t = re.sub(r'(\d+)\s*y(ears?)?\s*o(ld)?\.?', r'\1', t)
    t = re.sub(r'(\d+)\s*yo', r'\1', t)
    
    # remove generic words
    generics = ['whisky', 'whiskey', 'scotch', 'single malt', 'straight bourbon', 'kentucky', 'limited edition', 'release', 'blended', 'malt']
    for g in generics:
        t = re.sub(r'\b' + g + r'\b', '', t)
        
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def extract_age(text):
    # Try to extract from original raw text
    match = re.search(r'\b(\d+)\s*y(?:ears?)?\s*o(?:ld)?\b', str(text).lower())
    if match:
        return match.group(1)
    match = re.search(r'\b(\d+)\s*yo\b', str(text).lower())
    if match:
        return match.group(1)
    return None

def match_dataset():
    input_file = "data/output/structured_ml_whiskey_source/extracted_whiskey_data.csv"
    db_file = "output/import/production.db"
    output_dir = "data/output/structured_ml_whiskey_source"
    output_file = os.path.join(output_dir, "match_preview_tuned.csv")
    
    if not os.path.exists(input_file):
        print(json.dumps({"error": f"Extracted file not found: {input_file}"}))
        return
        
    if not os.path.exists(db_file):
        print(json.dumps({"error": f"Database not found: {db_file}"}))
        return

    try:
        df_extracted = pd.read_csv(input_file)
        
        conn = sqlite3.connect(db_file)
        df_production = pd.read_sql_query("SELECT whisky_id, name, age FROM whiskies", conn)
        conn.close()
        
        # Prepare targets
        targets = []
        for _, row in df_production.iterrows():
            norm_name = normalize_text(row['name'])
            targets.append({
                'whisky_id': row['whisky_id'],
                'name': row['name'],
                'norm_name': norm_name,
                'age': row['age']
            })
            
        results = []
        
        print("Starting fuzzy matching. This may take a moment...")
        for idx, row in df_extracted.iterrows():
            src_name = row['name']
            norm_src = normalize_text(src_name)
            src_first_word = norm_src.split()[0] if norm_src else ""
            src_age = extract_age(src_name)
            
            scores = []
            for tgt in targets:
                ratio = SequenceMatcher(None, norm_src, tgt['norm_name']).ratio()
                scores.append({
                    'whisky_id': tgt['whisky_id'],
                    'tgt_name': tgt['name'],
                    'norm_tgt': tgt['norm_name'],
                    'ratio': ratio,
                    'tgt_age': tgt['age']
                })
                
            scores.sort(key=lambda x: x['ratio'], reverse=True)
            best = scores[0]
            second = scores[1] if len(scores) > 1 else None
            
            best_score = best['ratio']
            second_score = second['ratio'] if second else 0
            margin = best_score - second_score
            
            status = 'no_match'
            if best_score >= 0.94 and margin >= 0.03:
                status = 'high'
            elif best_score >= 0.88 and margin >= 0.04:
                status = 'review'
            elif best_score >= 0.82:
                status = 'manual'
                
            # age conflict rule
            if status in ['high', 'review']:
                tgt_age = best['tgt_age']
                if pd.isna(tgt_age):
                    tgt_age = extract_age(best['tgt_name'])
                else:
                    if tgt_age == int(tgt_age):
                        tgt_age = str(int(tgt_age))
                    else:
                        tgt_age = str(tgt_age)
                        
                if src_age and tgt_age and str(src_age) != str(tgt_age):
                    status = 'manual'
                    
            # brand rule
            if status == 'high' and src_first_word and src_first_word not in best['norm_tgt']:
                status = 'review'
                
            results.append({
                'src_name': src_name,
                'tgt_name': best['tgt_name'],
                'whisky_id': best['whisky_id'],
                'status': status,
                'best_score': best_score,
                'second_score': second_score,
                'margin': margin,
                'rating': row.get('rating', ''),
                'price': row.get('price', ''),
                'currency': row.get('currency', ''),
                'description': row.get('description', ''),
                'norm_src': norm_src,
                'norm_tgt': best['norm_tgt']
            })
            
            if (idx + 1) % 500 == 0:
                print(f"Processed {idx + 1}/{len(df_extracted)} rows.")

        df_results = pd.DataFrame(results)
        os.makedirs(output_dir, exist_ok=True)
        df_results.to_csv(output_file, index=False)
        
        counts = df_results['status'].value_counts().to_dict()
        
        # Prepare report
        os.makedirs("output/reports", exist_ok=True)
        with open("output/reports/312_structured_ml_whiskey_source_match_tuning_report.md", "w", encoding="utf-8") as f:
            f.write("# 312 - Structured ML Whiskey Source Match Tuning Report\n\n")
            f.write("## Ne yaptım\n")
            f.write("AŞAMA 13B-FUZZY-MATCH kuralları gereği normalizasyon (abv, yaş, vintage ve jenerik kelime temizliği) ve bulanık (fuzzy) eşleşme algoritmaları eklendi.\n")
            f.write(f"Eşleşme skorlamaları sonucunda `{output_file}` oluşturuldu.\n\n")
            
            f.write("## Değişen dosyalar\n")
            f.write(f"- [MODIFY] `scripts/external_sources/match_structured_ml_whiskey_source_to_production.py`\n")
            f.write(f"- [NEW] `{output_file}`\n\n")
            
            f.write("## Test sonucu\n")
            f.write(f"- Toplam Satır: {len(df_extracted)}\n")
            for k in ['high', 'review', 'manual', 'no_match']:
                f.write(f"- {k.upper()} count: {counts.get(k, 0)}\n")
            f.write("\n")
            
            f.write("### Sample HIGH (25 adete kadar)\n")
            high_samples = df_results[df_results['status'] == 'high'].head(25)
            for _, r in high_samples.iterrows():
                f.write(f"- {r['src_name']} => {r['tgt_name']} (score: {r['best_score']:.2f}, margin: {r['margin']:.2f})\n")
                
            f.write("\n### Sample REVIEW/MANUAL (25 adete kadar)\n")
            rev_samples = df_results[df_results['status'].isin(['review', 'manual'])].head(25)
            for _, r in rev_samples.iterrows():
                f.write(f"- {r['src_name']} => {r['tgt_name']} (score: {r['best_score']:.2f}, status: {r['status']})\n")
                
            f.write("\n### Suspicious Examples (Şüpheli Düşürmeler / Margin İhlalleri)\n")
            suspicious = df_results[(df_results['status'] == 'manual') & (df_results['best_score'] >= 0.90)].head(10)
            if not suspicious.empty:
                for _, r in suspicious.iterrows():
                    f.write(f"- {r['src_name']} => {r['tgt_name']} (score: {r['best_score']:.2f}, margin: {r['margin']:.2f}) [age conflict or small margin]\n")
            else:
                f.write("- Bulunamadı.\n")
                
            f.write("\n## GO / WARN_GO / NO-GO\n")
            if counts.get('high', 0) > 0:
                f.write("**GO_REVIEW_CSV**\n")
            else:
                f.write("**NO-GO_MATCH_TUNING**\n")
                
            f.write("\n## Sonraki önerilen komut\n")
            f.write("Gözden geçirme tamamlandıysa, `high` kayıtları staging'e almak için insert scripti hazırlanabilir.\n")
            
        print("Tuning match completed successfully.")
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    match_dataset()

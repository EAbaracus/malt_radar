import pandas as pd
import sqlite3
import os
import json
import re

def extract_age(text):
    match = re.search(r'\b(\d+)\s*y(?:ears?)?\s*o(?:ld)?\b', str(text).lower())
    if match:
        return match.group(1)
    match = re.search(r'\b(\d+)\s*yo\b', str(text).lower())
    if match:
        return match.group(1)
    return None

def normalize_first_word(text):
    if pd.isna(text): return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower().split()[0])

def is_suspicious(row):
    reasons = []
    
    src_name = str(row.get('src_name', '')).lower()
    tgt_name = str(row.get('tgt_name', '')).lower()
    desc = str(row.get('description', ''))
    
    # Empty description
    if pd.isna(row.get('description')) or desc.strip() == '' or desc.lower() == 'nan':
        reasons.append('empty_description')
        
    # Age conflict
    src_age = extract_age(src_name)
    tgt_age_db = row.get('tgt_age', None)  # might not be in match_preview, we can fetch from db or extract from tgt_name
    tgt_age_extracted = extract_age(tgt_name)
    
    if src_age:
        # Check against extracted age if DB age is not available
        if tgt_age_extracted and str(src_age) != str(tgt_age_extracted):
            reasons.append('age_conflict')
            
    # Brand / First word missing
    src_fw = normalize_first_word(src_name)
    if src_fw and src_fw not in re.sub(r'[^a-z0-9\s]', '', tgt_name):
        reasons.append('brand_missing_in_target')
        
    # Extra qualifiers in source missing in target (vintage, single cask, batch, edition)
    qualifiers = ['vintage', 'cask', 'batch', 'edition', 'reserve', 'signatory', 'gordon', 'macphail', 'smws']
    found_quals_src = [q for q in qualifiers if q in src_name]
    found_quals_tgt = [q for q in qualifiers if q in tgt_name]
    for q in found_quals_src:
        if q not in found_quals_tgt:
            reasons.append(f'missing_qualifier_{q}')
            
    # Name length difference (source much longer)
    src_words = len(src_name.split())
    tgt_words = len(tgt_name.split())
    if src_words > tgt_words + 3:
        reasons.append('source_name_too_long')
        
    return reasons

def qa_high_matches():
    input_file = "data/output/structured_ml_whiskey_source/match_preview_tuned.csv"
    output_dir = "data/output/structured_ml_whiskey_source"
    pack_out = os.path.join(output_dir, "high_match_qa_pack.csv")
    safe_out = os.path.join(output_dir, "high_match_safe_preview.csv")
    suspicious_out = os.path.join(output_dir, "high_match_suspicious.csv")
    
    if not os.path.exists(input_file):
        print(json.dumps({"error": f"Tuned match file not found: {input_file}"}))
        return

    try:
        df_all = pd.read_csv(input_file)
        
        # We also need the original category from extracted if not in tuned? 
        # tuned match file has src_name, tgt_name, whisky_id, status, best_score, second_score, margin, rating, price, currency, description
        # We need to filter 'high'
        df_high = df_all[df_all['status'] == 'high'].copy()
        
        if len(df_high) == 0:
            print("No high matches found to QA.")
            return

        qa_results = []
        all_reasons_counter = {}
        
        for idx, row in df_high.iterrows():
            reasons = is_suspicious(row)
            is_safe = len(reasons) == 0
            
            for r in reasons:
                all_reasons_counter[r] = all_reasons_counter.get(r, 0) + 1
                
            qa_results.append({
                'src_name': row.get('src_name'),
                'tgt_name': row.get('tgt_name'),
                'whisky_id': row.get('whisky_id'),
                'score': row.get('best_score'),
                'margin': row.get('margin'),
                'rating': row.get('rating'),
                'price': row.get('price'),
                'currency': row.get('currency'),
                'description': row.get('description'),
                'qa_status': 'safe' if is_safe else 'suspicious',
                'suspicious_reasons': '|'.join(reasons)
            })

        df_qa = pd.DataFrame(qa_results)
        
        df_safe = df_qa[df_qa['qa_status'] == 'safe']
        df_suspicious = df_qa[df_qa['qa_status'] == 'suspicious']
        
        # Save output
        os.makedirs(output_dir, exist_ok=True)
        df_qa.to_csv(pack_out, index=False)
        df_safe.to_csv(safe_out, index=False)
        df_suspicious.to_csv(suspicious_out, index=False)
        
        # Reporting
        os.makedirs("output/reports", exist_ok=True)
        with open("output/reports/313_structured_ml_whiskey_source_high_qa_report.md", "w", encoding="utf-8") as f:
            f.write("# 313 - Structured ML Whiskey Source High Match QA Report\n\n")
            f.write("## Ne yaptım\n")
            f.write("`high` etiketli eşleşmeler kalite kontrolünden (QA) geçirildi. Yaş çelişkisi, spesifik özellik eksikliği, isim uzunluk farkı ve boş açıklamalar denetlendi.\n\n")
            
            f.write("## Değişen dosyalar\n")
            f.write(f"- [NEW] `{pack_out}`\n")
            f.write(f"- [NEW] `{safe_out}`\n")
            f.write(f"- [NEW] `{suspicious_out}`\n\n")
            
            f.write("## Çalıştırılan komutlar\n")
            f.write("- `python scripts/external_sources/qa_high_structured_ml_whiskey_source.py`\n\n")
            
            f.write("## Test sonucu\n")
            f.write(f"- Total HIGH Matches: {len(df_qa)}\n")
            f.write(f"- SAFE Count: {len(df_safe)}\n")
            f.write(f"- SUSPICIOUS Count: {len(df_suspicious)}\n\n")
            
            if all_reasons_counter:
                f.write("### Top Suspicious Reasons\n")
                for reason, count in sorted(all_reasons_counter.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- {reason}: {count}\n")
            f.write("\n")
            
            f.write("### Sample SAFE (25 adete kadar)\n")
            for _, r in df_safe.head(25).iterrows():
                f.write(f"- {r['src_name']} => {r['tgt_name']} (score: {r['score']:.2f})\n")
                
            f.write("\n### Sample SUSPICIOUS (25 adete kadar)\n")
            for _, r in df_suspicious.head(25).iterrows():
                f.write(f"- {r['src_name']} => {r['tgt_name']} (reasons: {r['suspicious_reasons']})\n")
                
            f.write("\n## GO / WARN_GO / NO-GO\n")
            safe_ratio = len(df_safe) / len(df_qa) if len(df_qa) > 0 else 0
            if len(df_safe) > 0 and safe_ratio > 0.3:
                f.write("**GO_DRY_RUN**\n")
            else:
                f.write("**REVIEW_REQUIRED** (Safe ratio too low)\n")
                
            f.write("\n## Sonraki önerilen komut\n")
            f.write("Safe liste için DB insert / staging aktarımı planlanabilir.\n")
            
        print("QA completed successfully.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    qa_high_matches()

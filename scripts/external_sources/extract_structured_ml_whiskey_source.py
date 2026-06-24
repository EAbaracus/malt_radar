import pandas as pd
import os
import json

def extract_dataset():
    input_file = "external_repos/structured_ml_whiskey_source/whiskey_data.csv"
    output_dir = "data/output/structured_ml_whiskey_source"
    output_file = os.path.join(output_dir, "extracted_whiskey_data.csv")
    
    if not os.path.exists(input_file):
        print(json.dumps({"error": f"File not found: {input_file}"}))
        return

    try:
        df = pd.read_csv(input_file)
        
        # Clean unnamed columns
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
            
        # Clean price column (remove commas if any)
        if 'price' in df.columns:
            df['price'] = df['price'].astype(str).str.replace(',', '').str.strip()
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            
        if 'rating' in df.columns:
            df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        
        os.makedirs(output_dir, exist_ok=True)
        df.to_csv(output_file, index=False)
        
        extract_results = {
            "output_file": output_file,
            "total_rows_extracted": len(df),
            "columns": list(df.columns)
        }
        
        print(json.dumps(extract_results, indent=2))
        
        # Write report
        os.makedirs("output/reports", exist_ok=True)
        with open("output/reports/310_structured_ml_whiskey_source_extract_report.md", "w", encoding="utf-8") as f:
            f.write("# 310 - Structured ML Whiskey Source Extract Report\n\n")
            f.write("## Ne yaptım\n")
            f.write(f"Veri '{input_file}' konumundan okunup temizlendi (`Unnamed: 0` kolonu silindi, `price` ve `rating` sayısal tipe dönüştürüldü) ve `{output_file}` konumuna kaydedildi.\n\n")
            f.write("## Değişen dosyalar\n")
            f.write(f"- [NEW] `{output_file}`\n\n")
            f.write("## Çalıştırılan komutlar\n")
            f.write("- `python scripts/external_sources/extract_structured_ml_whiskey_source.py`\n\n")
            f.write("## Test sonucu\n")
            f.write(f"- Çıkarılan Satır Sayısı: {len(df)}\n")
            f.write(f"- Çıkarılan Kolonlar: {', '.join(df.columns)}\n\n")
            f.write("## GO / WARN_GO / NO-GO\n")
            f.write("**GO_MATCH_PREVIEW**\n")
            f.write("\n## Sonraki önerilen komut\n")
            f.write("`python scripts/external_sources/match_structured_ml_whiskey_source_to_production.py`\n")
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    extract_dataset()

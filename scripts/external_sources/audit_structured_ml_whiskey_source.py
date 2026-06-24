import pandas as pd
import os
import json

def audit_dataset():
    input_file = "external_repos/structured_ml_whiskey_source/whiskey_data.csv"
    
    if not os.path.exists(input_file):
        print(json.dumps({"error": f"File not found: {input_file}"}))
        return

    try:
        df = pd.read_csv(input_file)
        
        audit_results = {
            "file_path": input_file,
            "total_rows": len(df),
            "columns": list(df.columns),
            "null_counts": df.isnull().sum().to_dict(),
            "sample_data": df.head(3).to_dict(orient='records')
        }
        
        required_columns = ["name", "category", "rating", "price", "currency", "description"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        audit_results["missing_required_columns"] = missing_columns
        audit_results["status"] = "SUCCESS" if not missing_columns else "FAILED"
        
        print(json.dumps(audit_results, indent=2))
        
        # Write report
        os.makedirs("output/reports", exist_ok=True)
        with open("output/reports/309_structured_ml_whiskey_source_audit.md", "w", encoding="utf-8") as f:
            f.write("# 309 - Structured ML Whiskey Source Audit\n\n")
            f.write("## Ne yaptım\n")
            f.write(f"Makine öğrenmesi için hazırlanmış whiskey dataseti incelendi: `{input_file}`.\n\n")
            f.write("## Değişen dosyalar\n")
            f.write("- Hiçbir veri dosyası değişmedi.\n\n")
            f.write("## Çalıştırılan komutlar\n")
            f.write("- `python scripts/external_sources/audit_structured_ml_whiskey_source.py`\n\n")
            f.write("## Test sonucu\n")
            f.write(f"- Toplam Satır: {len(df)}\n")
            f.write(f"- Kolonlar: {', '.join(df.columns)}\n")
            f.write(f"- Eksik Kolonlar: {', '.join(missing_columns) if missing_columns else 'Yok'}\n\n")
            f.write("## GO / WARN_GO / NO-GO\n")
            if not missing_columns:
                f.write("**GO_EXTRACT**\n")
            else:
                f.write("**NO-GO** (Eksik kolonlar var)\n")
            f.write("\n## Sonraki önerilen komut\n")
            f.write("`python scripts/external_sources/extract_structured_ml_whiskey_source.py`\n")
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    audit_dataset()

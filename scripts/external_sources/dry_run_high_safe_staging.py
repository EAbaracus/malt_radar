import pandas as pd
import sqlite3
import os
import json

def dry_run_staging():
    input_file = "data/output/structured_ml_whiskey_source/high_match_safe_preview.csv"
    db_file = "output/import/production.db"
    output_dir = "data/output/structured_ml_whiskey_source"
    planned_out = os.path.join(output_dir, "high_safe_staging_dry_run.csv")
    blocked_out = os.path.join(output_dir, "high_safe_staging_dry_run_blocked.csv")
    report_file = "output/reports/314_structured_ml_whiskey_source_high_safe_staging_dry_run.md"
    
    if not os.path.exists(input_file):
        print(json.dumps({"error": f"Input file not found: {input_file}"}))
        return

    try:
        df_safe = pd.read_csv(input_file)
        
        # Connect read-only
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        
        # Get valid whisky IDs
        valid_whiskies = set(row[0] for row in conn.execute("SELECT whisky_id FROM whiskies").fetchall())
        
        # Get existing staging records for duplicates check
        # Assuming staging_tasting_notes has columns: source_system, source_name, whisky_id
        # Let's check what columns it actually has
        staging_schema = [row[1] for row in conn.execute("PRAGMA table_info(staging_tasting_notes)").fetchall()]
        
        existing_staging = []
        staging_total_count = 0
        existing_source_count = 0
        
        if len(staging_schema) > 0:
            staging_total_count = conn.execute("SELECT COUNT(*) FROM staging_tasting_notes").fetchone()[0]
            if 'source_system' in staging_schema:
                existing_source_count = conn.execute("SELECT COUNT(*) FROM staging_tasting_notes WHERE source_system='structured_ml_whiskey_source'").fetchone()[0]
                
                # Build duplicate check set based on source_name and whisky_id
                if 'original_name' in staging_schema and 'whisky_id' in staging_schema:
                    existing_staging = set(
                        (row[0], row[1]) for row in conn.execute(
                            "SELECT original_name, whisky_id FROM staging_tasting_notes WHERE source_system='structured_ml_whiskey_source'"
                        ).fetchall()
                    )
        
        conn.close()
        
        planned = []
        blocked = []
        block_reasons_counter = {}
        
        for idx, row in df_safe.iterrows():
            reasons = []
            
            # 1. FK check
            wid = row.get('whisky_id')
            if pd.isna(wid) or wid not in valid_whiskies:
                reasons.append('invalid_whisky_id')
                
            # 2. Description check
            desc = str(row.get('description', ''))
            if pd.isna(row.get('description')) or desc.strip() == '' or desc.lower() == 'nan':
                reasons.append('empty_description')
                
            # 3. Duplicate check
            src_name = row.get('src_name')
            if existing_staging and (src_name, wid) in existing_staging:
                reasons.append('duplicate_in_staging')
                
            # 4. Required columns
            # We assume we need at least whisky_id, description, and source_name
            if pd.isna(src_name) or str(src_name).strip() == '':
                reasons.append('missing_source_name')
                
            row_dict = row.to_dict()
            if reasons:
                row_dict['block_reasons'] = '|'.join(reasons)
                blocked.append(row_dict)
                for r in reasons:
                    block_reasons_counter[r] = block_reasons_counter.get(r, 0) + 1
            else:
                row_dict['status'] = 'ready_for_staging'
                row_dict['source_system'] = 'structured_ml_whiskey_source'
                planned.append(row_dict)
                
        df_planned = pd.DataFrame(planned)
        df_blocked = pd.DataFrame(blocked)
        
        os.makedirs(output_dir, exist_ok=True)
        if not df_planned.empty:
            df_planned.to_csv(planned_out, index=False)
        else:
            # Create empty file
            pd.DataFrame(columns=df_safe.columns).to_csv(planned_out, index=False)
            
        if not df_blocked.empty:
            df_blocked.to_csv(blocked_out, index=False)
        else:
            pd.DataFrame(columns=list(df_safe.columns) + ['block_reasons']).to_csv(blocked_out, index=False)
            
        # Write report
        os.makedirs("output/reports", exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 314 - Structured ML Whiskey Source High Safe Staging Dry Run\n\n")
            f.write("## Ne yaptım\n")
            f.write("Güvenli (SAFE) eşleşmeler için `staging_tasting_notes` tablosuna insert simülasyonu (dry-run) yapıldı.\n")
            f.write("Yabancı anahtar (FK), açıklama (description), zorunlu alanlar ve duplicate kontrolleri uygulandı.\n\n")
            
            f.write("## Değişen dosyalar\n")
            f.write(f"- [NEW] `{planned_out}`\n")
            f.write(f"- [NEW] `{blocked_out}`\n\n")
            
            f.write("## Çalıştırılan komutlar\n")
            f.write("- `python scripts/external_sources/dry_run_high_safe_staging.py`\n\n")
            
            f.write("## Test sonucu\n")
            f.write(f"- Input Rows: {len(df_safe)}\n")
            f.write(f"- Planned Insert: {len(planned)}\n")
            f.write(f"- Blocked: {len(blocked)}\n\n")
            
            f.write(f"- Staging Mevcut Toplam Kayıt: {staging_total_count}\n")
            f.write(f"- Staging Aynı Kaynak (structured_ml_whiskey_source) Kayıt Sayısı: {existing_source_count}\n\n")
            
            if block_reasons_counter:
                f.write("### Block Reasons\n")
                for reason, count in block_reasons_counter.items():
                    f.write(f"- {reason}: {count}\n")
            f.write("\n")
            
            f.write("## GO / WARN_GO / NO-GO\n")
            if len(planned) > 0 and len(blocked) == 0:
                f.write("**GO_APPLY_AFTER_12UB**\n")
            elif len(planned) > 0 and len(blocked) > 0:
                f.write("**REVIEW_BLOCKED**\n")
            else:
                f.write("**NO-GO**\n")
                
            f.write("\n## Sonraki önerilen komut\n")
            f.write("12UB hattı tamamlandığında, `planned_insert` kayıtları için insert işlemi gerçekleştirilebilir.\n")
            
        print("Dry run completed successfully.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    dry_run_staging()

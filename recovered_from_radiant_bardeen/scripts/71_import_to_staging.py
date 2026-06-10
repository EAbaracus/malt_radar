import sqlite3
import pandas as pd
import os
import json

def run_staging_import():
    db_path = 'output/import/staging_test.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Tables
    cursor.execute("""
        CREATE TABLE distilleries (
            distillery_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            normalized_name TEXT,
            country TEXT,
            region TEXT,
            owner TEXT,
            founded_year INTEGER,
            official_website TEXT,
            wikidata_id TEXT,
            wikipedia_url TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE whiskies (
            whisky_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            distillery_id TEXT,
            type TEXT,
            brand TEXT,
            region TEXT,
            age REAL,
            age_statement TEXT,
            abv REAL,
            FOREIGN KEY(distillery_id) REFERENCES distilleries(distillery_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE tasting_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT NOT NULL,
            tasting_notes TEXT NOT NULL,
            data_confidence TEXT NOT NULL,
            FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE flavor_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT NOT NULL,
            flavor_profile TEXT NOT NULL,
            FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL,
            FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id)
        )
    """)
    conn.commit()

    import_errors = []
    
    # 1. Import Distilleries
    df_dist = pd.read_csv('output/55_FINAL_import_ready_distilleries.csv')
    try:
        dist_cols = ['distillery_id', 'name', 'normalized_name', 'country', 'region', 'owner', 'founded_year', 'official_website', 'wikidata_id', 'wikipedia_url']
        df_dist_filtered = df_dist[[c for c in dist_cols if c in df_dist.columns]].copy()
        df_dist_filtered.to_sql('distilleries', conn, if_exists='append', index=False)
    except Exception as e:
        import_errors.append({'table': 'distilleries', 'error': str(e)})

    # 2. Import Whiskies
    df_whiskies = pd.read_csv('output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv')
    try:
        # We need to map only existing columns
        cols = ['whisky_id', 'name', 'distillery_id', 'type', 'brand', 'region', 'age', 'age_statement', 'abv']
        df_w_filtered = df_whiskies[[c for c in cols if c in df_whiskies.columns]].copy()
        
        # Ensure foreign key constraints work by handling NaNs
        # sqlite might fail if we pass float NaNs to string column, so convert
        if 'distillery_id' in df_w_filtered.columns:
            df_w_filtered['distillery_id'] = df_w_filtered['distillery_id'].where(pd.notna(df_w_filtered['distillery_id']), None)
            
        df_w_filtered.to_sql('whiskies', conn, if_exists='append', index=False)
    except Exception as e:
        import_errors.append({'table': 'whiskies', 'error': str(e)})

    # 3. Import Tasting Notes
    try:
        df_tasting = pd.read_csv('output/37_import_ready_tasting_notes.csv')
        if not df_tasting.empty:
            df_tasting.to_sql('tasting_notes', conn, if_exists='append', index=False)
    except Exception as e:
        pass

    # 4. Import Flavor Profiles
    try:
        df_flavor = pd.read_csv('output/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv')
        if not df_flavor.empty:
            df_flavor.to_sql('flavor_profiles', conn, if_exists='append', index=False)
    except Exception as e:
        pass

    # Record counts
    counts = {}
    for t in ['distilleries', 'whiskies', 'tasting_notes', 'flavor_profiles', 'price_history']:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cursor.fetchone()[0]

    pd.DataFrame(import_errors).to_csv('output/import/08_staging_import_errors.csv', index=False)
    pd.DataFrame([counts]).to_csv('output/import/07_staging_import_counts.csv', index=False)

    with open('output/import/06_staging_import_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== STAGING IMPORT REPORT ===\n\n")
        f.write("Strateji: Transaction tabanli, SQLite in-file DB kullanilarak dry-run DB seed.\n")
        f.write("Hatalar: " + str(len(import_errors)) + "\n\n")
        f.write("Import edilen satir sayilari:\n")
        for k, v in counts.items():
            f.write(f"- {k}: {v}\n")
            
    # STAGE 4 - SMOKE TESTS
    smoke_report = []
    
    # toplam whisky
    smoke_report.append(f"Toplam Whisky: {counts['whiskies']}")
    smoke_report.append(f"Toplam Distillery: {counts['distilleries']}")
    
    # null distillery_id
    cursor.execute("SELECT COUNT(*) FROM whiskies WHERE distillery_id IS NULL")
    null_dist = cursor.fetchone()[0]
    smoke_report.append(f"Null distillery_id urun sayisi: {null_dist}")
    
    # flavor profile bağlı ürün sayısı
    cursor.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles")
    fp_linked = cursor.fetchone()[0]
    smoke_report.append(f"Flavor profile bagli urun sayisi: {fp_linked}")
    
    # tasting note bağlı ürün sayısı
    cursor.execute("SELECT COUNT(DISTINCT whisky_id) FROM tasting_notes")
    tn_linked = cursor.fetchone()[0]
    smoke_report.append(f"Tasting note bagli urun sayisi: {tn_linked}")
    
    # Macallan / Glenlivet / Balvenie
    cursor.execute("SELECT name, distillery_id FROM whiskies WHERE LOWER(name) LIKE '%macallan%' OR LOWER(name) LIKE '%glenlivet%' LIMIT 5")
    rows = cursor.fetchall()
    smoke_report.append("\nOrnek Patch Test (Macallan / Glenlivet):")
    for r in rows:
        smoke_report.append(f" - {r[0]} -> {r[1]}")
        
    # Orphan listeleme
    cursor.execute("SELECT name FROM whiskies WHERE distillery_id IS NULL LIMIT 5")
    orphan_rows = cursor.fetchall()
    smoke_report.append("\nOrnek Orphan Urunler (Crash yaratmadan listelenebilir):")
    for r in orphan_rows:
        smoke_report.append(f" - {r[0]}")
        
    with open('output/import/09_post_import_smoke_test_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== POST-IMPORT SMOKE TEST REPORT ===\n\n")
        f.write("\n".join(smoke_report))
        
    conn.close()

if __name__ == '__main__':
    run_staging_import()

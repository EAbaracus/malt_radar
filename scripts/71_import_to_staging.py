"""
LEGACY SCRIPT / DO NOT RUN AGAINST PRODUCTION
This script belongs to older phases (Phase 2/3) and is NOT part of the new Phase 5/6 pipeline.
It directly mutates tables without proper safety guards and should only be used
for testing/recreating an isolated staging DB, not for the real staging ingestion.
"""

import sqlite3
import pandas as pd
import os
import sys
import argparse

def run_staging_import():
    parser = argparse.ArgumentParser(description="Legacy Staging DB Import Script")
    parser.add_argument('--i-understand-this-is-legacy-staging-only', action='store_true', help='Acknowledge legacy status')
    parser.add_argument('--force-recreate-staging', action='store_true', help='Allow deletion of existing DB')
    parser.add_argument('--db-path', type=str, default='output/import/staging_test.db', help='Target DB path')
    args = parser.parse_args()

    if not args.i_understand_this_is_legacy_staging_only:
        sys.exit("Error: This is a legacy script. You must explicitly provide --i-understand-this-is-legacy-staging-only flag to run.")

    db_path = args.db_path

    if "production.db" in db_path:
        sys.exit("CRITICAL ERROR: Refusing to run against production.db!")

    if os.path.exists(db_path):
        if args.force_recreate_staging:
            os.remove(db_path)
        else:
            sys.exit("Error: DB exists and --force-recreate-staging not provided.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("CREATE TABLE distilleries (distillery_id TEXT PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT, country TEXT, region TEXT, owner TEXT, founded_year INTEGER, official_website TEXT, wikidata_id TEXT, wikipedia_url TEXT)")
    cursor.execute("CREATE TABLE whiskies (whisky_id TEXT PRIMARY KEY, name TEXT NOT NULL, distillery_id TEXT, type TEXT, brand TEXT, region TEXT, age REAL, age_statement TEXT, abv REAL, FOREIGN KEY(distillery_id) REFERENCES distilleries(distillery_id))")
    cursor.execute("CREATE TABLE tasting_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, whisky_id TEXT NOT NULL, tasting_notes TEXT NOT NULL, data_confidence TEXT NOT NULL, FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id))")
    cursor.execute("CREATE TABLE flavor_profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, whisky_id TEXT NOT NULL, flavor_profile TEXT NOT NULL, FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id))")
    cursor.execute("CREATE TABLE price_history (id INTEGER PRIMARY KEY AUTOINCREMENT, whisky_id TEXT NOT NULL, price REAL NOT NULL, currency TEXT NOT NULL, FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id))")
    conn.commit()

    import_errors = []

    try:
        cursor.execute("BEGIN TRANSACTION")

        dist_path = 'output/55_FINAL_import_ready_distilleries.csv'
        if os.path.exists(dist_path):
            df_dist = pd.read_csv(dist_path)
            dist_cols = ['distillery_id', 'name', 'normalized_name', 'country', 'region', 'owner', 'founded_year', 'official_website', 'wikidata_id', 'wikipedia_url']
            df_dist_filtered = df_dist[[c for c in dist_cols if c in df_dist.columns]].copy()
            df_dist_filtered.to_sql('distilleries', conn, if_exists='append', index=False)
        else:
            import_errors.append({'table': 'distilleries', 'error': 'File not found'})

        whisk_path = 'output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv'
        if os.path.exists(whisk_path):
            df_whiskies = pd.read_csv(whisk_path)
            cols = ['whisky_id', 'name', 'distillery_id', 'type', 'brand', 'region', 'age', 'age_statement', 'abv']
            df_w_filtered = df_whiskies[[c for c in cols if c in df_whiskies.columns]].copy()
            if 'distillery_id' in df_w_filtered.columns:
                df_w_filtered['distillery_id'] = df_w_filtered['distillery_id'].where(pd.notna(df_w_filtered['distillery_id']), None)
            df_w_filtered.to_sql('whiskies', conn, if_exists='append', index=False)
        else:
            import_errors.append({'table': 'whiskies', 'error': 'File not found'})

        tn_path = 'output/37_import_ready_tasting_notes.csv'
        if os.path.exists(tn_path):
            df_tasting = pd.read_csv(tn_path)
            if not df_tasting.empty:
                df_tasting.to_sql('tasting_notes', conn, if_exists='append', index=False)
        else:
            import_errors.append({'table': 'tasting_notes', 'error': 'File not found'})

        fp_path = 'output/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv'
        if os.path.exists(fp_path):
            df_flavor = pd.read_csv(fp_path)
            if not df_flavor.empty:
                df_flavor.to_sql('flavor_profiles', conn, if_exists='append', index=False)
        else:
            import_errors.append({'table': 'flavor_profiles', 'error': 'File not found'})

        conn.commit()
    except Exception as e:
        conn.rollback()
        import_errors.append({'table': 'transaction', 'error': f"Rolled back due to: {str(e)}"})

    counts = {}
    for t in ['distilleries', 'whiskies', 'tasting_notes', 'flavor_profiles', 'price_history']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cursor.fetchone()[0]
        except Exception:
            counts[t] = 0

    if import_errors:
        pd.DataFrame(import_errors).to_csv('output/import/08_staging_import_errors.csv', index=False)
    pd.DataFrame([counts]).to_csv('output/import/07_staging_import_counts.csv', index=False)

    with open('output/import/06_staging_import_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== STAGING IMPORT REPORT ===\n\n")
        f.write("Strateji: Transaction tabanli, SQLite in-file DB kullanilarak dry-run DB seed.\n")
        f.write("Hatalar: " + str(len(import_errors)) + "\n\n")
        f.write("Import edilen satir sayilari:\n")
        for k, v in counts.items():
            f.write(f"- {k}: {v}\n")

    conn.close()
    print("Legacy staging import completed. Check output/import/06_staging_import_report.txt")

if __name__ == '__main__':
    run_staging_import()

import pandas as pd
import os

def run_dry_run_validation():
    os.makedirs('output/import', exist_ok=True)
    
    f_dist = 'output/55_FINAL_import_ready_distilleries.csv'
    f_whiskies = 'output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv'
    f_tasting = 'output/37_import_ready_tasting_notes.csv'
    f_flavor = 'output/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv'
    f_price = 'output/36_import_ready_price_history.csv'

    try: df_dist = pd.read_csv(f_dist, low_memory=False)
    except: df_dist = pd.DataFrame()

    try: df_whiskies = pd.read_csv(f_whiskies, low_memory=False)
    except: df_whiskies = pd.DataFrame()

    try: df_tasting = pd.read_csv(f_tasting, low_memory=False)
    except: df_tasting = pd.DataFrame()

    try: df_flavor = pd.read_csv(f_flavor, low_memory=False)
    except: df_flavor = pd.DataFrame()

    try: df_price = pd.read_csv(f_price, low_memory=False)
    except: df_price = pd.DataFrame()

    fk_errors = []
    dup_errors = []

    # Check primary keys
    if not df_dist.empty and df_dist['distillery_id'].duplicated().any():
        dups = df_dist[df_dist['distillery_id'].duplicated()]['distillery_id'].tolist()
        dup_errors.extend([{'table': 'distilleries', 'key': d, 'issue': 'Duplicate Primary Key'} for d in dups])

    if not df_whiskies.empty and df_whiskies['whisky_id'].duplicated().any():
        dups = df_whiskies[df_whiskies['whisky_id'].duplicated()]['whisky_id'].tolist()
        dup_errors.extend([{'table': 'whiskies', 'key': d, 'issue': 'Duplicate Primary Key'} for d in dups])

    # Check foreign keys
    valid_dist_ids = set(df_dist['distillery_id'].dropna().astype(str)) if not df_dist.empty else set()
    valid_whisky_ids = set(df_whiskies['whisky_id'].dropna().astype(str)) if not df_whiskies.empty else set()

    orphan_count = 0
    if not df_whiskies.empty:
        orphan_count = df_whiskies['distillery_id'].isna().sum()
        invalid_dists = df_whiskies[~df_whiskies['distillery_id'].isna() & ~df_whiskies['distillery_id'].astype(str).isin(valid_dist_ids)]
        for _, row in invalid_dists.iterrows():
            fk_errors.append({'table': 'whiskies', 'key': row['whisky_id'], 'fk_column': 'distillery_id', 'fk_value': row['distillery_id']})

    if not df_tasting.empty and 'whisky_id' in df_tasting.columns:
        invalid_whisky_tasting = df_tasting[~df_tasting['whisky_id'].astype(str).isin(valid_whisky_ids)]
        for _, row in invalid_whisky_tasting.iterrows():
            fk_errors.append({'table': 'tasting_notes', 'key': 'N/A', 'fk_column': 'whisky_id', 'fk_value': row['whisky_id']})

    if not df_flavor.empty and 'whisky_id' in df_flavor.columns:
        invalid_whisky_flavor = df_flavor[~df_flavor['whisky_id'].astype(str).isin(valid_whisky_ids)]
        for _, row in invalid_whisky_flavor.iterrows():
            fk_errors.append({'table': 'flavor_profiles', 'key': 'N/A', 'fk_column': 'whisky_id', 'fk_value': row['whisky_id']})

    # Output CSVs
    pd.DataFrame(fk_errors, columns=['table', 'key', 'fk_column', 'fk_value']).to_csv('output/import/03_import_fk_errors.csv', index=False)
    pd.DataFrame(dup_errors, columns=['table', 'key', 'issue']).to_csv('output/import/04_import_duplicate_errors.csv', index=False)
    pd.DataFrame([{'table': 'whiskies', 'column': 'distillery_id', 'null_count': orphan_count}]).to_csv('output/import/05_import_nullable_summary.csv', index=False)

    # Output Report
    with open('output/import/02_import_dry_run_validation_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== DRY-RUN IMPORT VALIDATION REPORT ===\n\n")
        f.write(f"Distilleries rows: {len(df_dist)}\n")
        f.write(f"Whiskies rows: {len(df_whiskies)} (Beklenen: 1829)\n")
        f.write(f"Orphan Whiskies: {orphan_count} (Beklenen: 1151)\n")
        f.write(f"Flavor Profiles: {len(df_flavor)}\n")
        f.write(f"FK Errors: {len(fk_errors)} (Beklenen: 0)\n")
        f.write(f"Duplicate PK Errors: {len(dup_errors)} (Beklenen: 0)\n")

if __name__ == '__main__':
    run_dry_run_validation()

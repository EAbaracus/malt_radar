import pandas as pd
import os
import sys

def run_dry_run_validation():
    os.makedirs('output/import', exist_ok=True)

    f_dist = 'output/55_FINAL_import_ready_distilleries.csv'
    f_whiskies = 'output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv'
    f_tasting = 'output/37_import_ready_tasting_notes.csv'
    f_flavor = 'output/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv'
    f_price = 'output/36_import_ready_price_history.csv'

    validation_errors = []

    def safe_read(path, name):
        if not os.path.exists(path):
            validation_errors.append(f"{name} file not found: {path}")
            return pd.DataFrame()
        try:
            return pd.read_csv(path, low_memory=False)
        except Exception as e:
            validation_errors.append(f"Error reading {name} file: {e}")
            return pd.DataFrame()

    df_dist = safe_read(f_dist, "Distilleries")
    df_whiskies = safe_read(f_whiskies, "Whiskies")
    df_tasting = safe_read(f_tasting, "Tasting Notes")
    df_flavor = safe_read(f_flavor, "Flavor Profiles")
    df_price = safe_read(f_price, "Prices")

    fk_errors = []
    dup_errors = []

    if not df_dist.empty and df_dist['distillery_id'].duplicated().any():
        dups = df_dist[df_dist['distillery_id'].duplicated()]['distillery_id'].tolist()
        dup_errors.extend([{'table': 'distilleries', 'key': d, 'issue': 'Duplicate Primary Key'} for d in dups])

    if not df_whiskies.empty and df_whiskies['whisky_id'].duplicated().any():
        dups = df_whiskies[df_whiskies['whisky_id'].duplicated()]['whisky_id'].tolist()
        dup_errors.extend([{'table': 'whiskies', 'key': d, 'issue': 'Duplicate Primary Key'} for d in dups])

    valid_dist_ids = set(df_dist['distillery_id'].dropna().astype(str)) if not df_dist.empty else set()
    valid_whisky_ids = set(df_whiskies['whisky_id'].dropna().astype(str)) if not df_whiskies.empty else set()

    orphan_count = 0
    if not df_whiskies.empty:
        orphan_count = df_whiskies['distillery_id'].isna().sum()
        invalid_dist_mask = ~df_whiskies['distillery_id'].isna() & ~df_whiskies['distillery_id'].astype(str).isin(valid_dist_ids)
        invalid_dists = df_whiskies[invalid_dist_mask]
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

    pd.DataFrame(fk_errors, columns=['table', 'key', 'fk_column', 'fk_value']).to_csv('output/import/03_import_fk_errors.csv', index=False)
    pd.DataFrame(dup_errors, columns=['table', 'key', 'issue']).to_csv('output/import/04_import_duplicate_errors.csv', index=False)
    pd.DataFrame([{'table': 'whiskies', 'column': 'distillery_id', 'null_count': orphan_count}]).to_csv('output/import/05_import_nullable_summary.csv', index=False)

    expected_whiskies = 1829
    expected_orphans = 1151

    gate_failed = False

    if len(df_whiskies) != expected_whiskies:
        validation_errors.append(f"Whiskies count mismatch: {len(df_whiskies)} != {expected_whiskies}")
        gate_failed = True

    if orphan_count != expected_orphans:
        validation_errors.append(f"Orphan whiskies mismatch: {orphan_count} != {expected_orphans}")
        gate_failed = True

    if len(fk_errors) > 0:
        validation_errors.append(f"FK errors found: {len(fk_errors)}")
        gate_failed = True

    if len(dup_errors) > 0:
        validation_errors.append(f"Duplicate PK errors found: {len(dup_errors)}")
        gate_failed = True

    if validation_errors:
        gate_failed = True

    with open('output/import/02_import_dry_run_validation_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== DRY-RUN IMPORT VALIDATION REPORT ===\n\n")
        f.write(f"Distilleries rows: {len(df_dist)}\n")
        f.write(f"Whiskies rows: {len(df_whiskies)} (Beklenen: {expected_whiskies})\n")
        f.write(f"Orphan Whiskies: {orphan_count} (Beklenen: {expected_orphans})\n")
        f.write(f"Flavor Profiles: {len(df_flavor)}\n")
        f.write(f"FK Errors: {len(fk_errors)} (Beklenen: 0)\n")
        f.write(f"Duplicate PK Errors: {len(dup_errors)} (Beklenen: 0)\n")

        if gate_failed:
            f.write("\nGATE FAILED!\nErrors:\n")
            f.write("\n".join(validation_errors))

    if gate_failed:
        print("Dry-run validation FAILED. See output/import/02_import_dry_run_validation_report.txt")
        sys.exit(1)
    else:
        print("Dry-run validation SUCCESS.")
        sys.exit(0)

if __name__ == '__main__':
    run_dry_run_validation()

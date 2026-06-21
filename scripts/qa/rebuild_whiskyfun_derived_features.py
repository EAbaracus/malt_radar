import os
import glob
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")
db_path = os.path.join(base_dir, "output", "import", "production.db")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

output_csv = os.path.join(output_dir, "whiskyfun_derived_features_with_identity.csv")
report_md = os.path.join(reports_dir, "311_12p_file_fix_whiskyfun_identity_report.md")
gate_txt = os.path.join(reports_dir, "312_12p_file_fix_whiskyfun_identity_gate.txt")

FORBIDDEN_COLS = {'review_text', 'nose', 'mouth', 'finish', 'comments', 'nmf', 'review_text_original'}
EXPECTED_ROWS = 11149

def main():
    downloads_dir = "C:/Users/eltun/Downloads"
    # Find düzeltilmis.csv
    duz_files = glob.glob(os.path.join(downloads_dir, "*zeltilmi*.csv"))
    if not duz_files:
        raise Exception("Could not find düzeltilmiş.csv")
    
    # Raw tokenized file from the zip we extracted
    raw_file = os.path.join(downloads_dir, "whiskyfun_tmp", "whiskyfun_tokenized.csv")
    if not os.path.exists(raw_file):
        raise Exception("Could not find raw tokenized CSV")

    df_fixed = pd.read_csv(duz_files[0])
    df_raw = pd.read_csv(raw_file)

    # Clean raw to only identity cols + dedupe_hash
    identity_cols = ['dedupe_hash', 'whisky_name_raw', 'review_date', 'source_url']
    df_raw_id = df_raw[identity_cols].drop_duplicates(subset=['dedupe_hash'])

    # Merge
    df_merged = pd.merge(df_fixed, df_raw_id, on="dedupe_hash", how="left")

    # Ensure no forbidden cols
    cols_to_drop = [c for c in df_merged.columns if c in FORBIDDEN_COLS]
    if cols_to_drop:
        df_merged.drop(columns=cols_to_drop, inplace=True)

    # Reorder columns to put identity at front
    cols = list(df_merged.columns)
    # Move whisky_name_raw, review_date, source_url after dedupe_hash
    for c in ['source_url', 'review_date', 'whisky_name_raw']:
        if c in cols:
            cols.remove(c)
            cols.insert(1, c)

    df_merged = df_merged[cols]

    # Validations
    row_count = len(df_merged)
    duplicate_hash_count = df_merged['dedupe_hash'].duplicated().sum()
    forbidden_found = [c for c in FORBIDDEN_COLS if c in df_merged.columns]
    
    has_name = 'whisky_name_raw' in df_merged.columns
    has_date = 'review_date' in df_merged.columns
    has_url = 'source_url' in df_merged.columns
    
    empty_name_pct = (df_merged['whisky_name_raw'].isna().sum() / row_count * 100) if has_name else 100.0
    empty_url_pct = (df_merged['source_url'].isna().sum() / row_count * 100) if has_url else 100.0
    
    # Check parseability of review_date
    date_parse_success = pd.to_datetime(df_merged['review_date'], errors='coerce').notna().sum()
    date_parse_pct = (date_parse_success / row_count * 100) if has_date else 0.0

    df_merged.to_csv(output_csv, index=False)

    gate = "GO_IDENTITY_ADDED"
    reasons = []

    if row_count != EXPECTED_ROWS:
        gate = "NO_GO_ROW_COUNT_CHANGED"
        reasons.append(f"Row count is {row_count}, expected {EXPECTED_ROWS}")
    if duplicate_hash_count > 0:
        gate = "NO_GO_DUPLICATE_HASH"
        reasons.append(f"Found {duplicate_hash_count} duplicate dedupe_hash")
    if forbidden_found:
        gate = "NO_GO_FULL_TEXT_LEAK"
        reasons.append(f"Forbidden columns found: {forbidden_found}")

    with open(gate_txt, "w", encoding="utf-8") as f:
        f.write(f"GATE: {gate}\n")
        if gate == "GO_IDENTITY_ADDED":
            f.write("REASON: Identity columns restored successfully without full text.\n")
        for r in reasons:
            f.write(f"REASON: {r}\n")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# 311 12P File Fix Whiskyfun Identity Report\n\n")
        f.write(f"- row_count: {row_count}\n")
        f.write(f"- has_whisky_name_raw: {has_name}\n")
        f.write(f"- has_review_date: {has_date}\n")
        f.write(f"- has_source_url: {has_url}\n")
        f.write(f"- forbidden_columns_found: {forbidden_found}\n")
        f.write(f"- duplicate_dedupe_hash: {duplicate_hash_count}\n")
        f.write(f"- empty_whisky_name_raw_pct: {empty_name_pct:.2f}%\n")
        f.write(f"- empty_source_url_pct: {empty_url_pct:.2f}%\n")
        f.write(f"- review_date_parse_success_pct: {date_parse_pct:.2f}%\n")
        f.write("- production_db_changed: NO\n")

if __name__ == "__main__":
    main()

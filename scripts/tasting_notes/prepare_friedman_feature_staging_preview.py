import pandas as pd
import hashlib
from datetime import datetime
import os

# Constants
INPUT_MATCHED_FEATURES = 'data/output/friedman_derived_feature_product_match_preview.csv'
INPUT_FEATURE_DETAILS = 'data/output/friedman_derived_features_with_identity.csv'
OUTPUT_AGGREGATE_PREVIEW = 'data/output/friedman_feature_staging_aggregate_preview.csv'
OUTPUT_REVIEW_LEVEL_AUDIT = 'data/output/friedman_feature_staging_review_level_audit.csv'
SQL_CREATE_STAGING_TABLE = 'output/import/sql_preview/create_staging_friedman_feature_profiles.sql'
SQL_INSERT_STAGING_DATA = 'output/import/sql_preview/insert_staging_friedman_feature_profiles_preview.sql'
REPORT_STAGING_PREVIEW = 'output/reports/325_12u_friedman_feature_staging_preview_report.md'
GATE_FILE = 'output/reports/326_12u_friedman_feature_staging_preview_gate.txt'

# Function to create output directories
def ensure_output_directories():
    os.makedirs(os.path.dirname(OUTPUT_AGGREGATE_PREVIEW), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_REVIEW_LEVEL_AUDIT), exist_ok=True)
    os.makedirs(os.path.dirname(SQL_CREATE_STAGING_TABLE), exist_ok=True)
    os.makedirs(os.path.dirname(SQL_INSERT_STAGING_DATA), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_STAGING_PREVIEW), exist_ok=True)
    os.makedirs(os.path.dirname(GATE_FILE), exist_ok=True)

# Function to hash a file
def hash_file(filename):
    hasher = hashlib.sha256()
    with open(filename, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

# Ensure output directories exist
ensure_output_directories()

try:
    # Print current working directory
    print(f"Current Working Directory: {os.getcwd()}")

    # Check and print whether each input file exists
    if os.path.exists(INPUT_MATCHED_FEATURES):
        print(f"{INPUT_MATCHED_FEATURES} exists.")
    else:
        raise FileNotFoundError(f"{INPUT_MATCHED_FEATURES} does not exist.")

    if os.path.exists(INPUT_FEATURE_DETAILS):
        print(f"{INPUT_FEATURE_DETAILS} exists.")
    else:
        raise FileNotFoundError(f"{INPUT_FEATURE_DETAILS} does not exist.")

    # Read input files
    match_df = pd.read_csv(INPUT_MATCHED_FEATURES)
    detail_df = pd.read_csv(INPUT_FEATURE_DETAILS)

    # Print shapes and columns of input dataframes
    print(f"match_df shape: {match_df.shape}")
    print(f"match_df columns: {list(match_df.columns)}")
    print(f"detail_df shape: {detail_df.shape}")
    print(f"detail_df columns: {list(detail_df.columns)}")

    # Filter rows where decision is KEEP_PRODUCT_FEATURE
    filtered_match_df = match_df[match_df['decision'] == 'KEEP_PRODUCT_FEATURE']

    # Print shape of keep_df
    print(f"keep_df shape: {filtered_match_df.shape}")

    # Merge filtered match_df with detail_df on dedupe_hash
    merged_df = filtered_match_df.merge(detail_df, on='dedupe_hash', how='left')

    # Rename columns to remove suffixes
    merged_df.rename(columns={
        'source_score_x': 'source_score',
        'rating_points_x': 'rating_points',
        'review_year_x': 'review_year',
        'internal_source_url_x': 'internal_source_url'
    }, inplace=True)

    # Print shape and columns of merged dataframe after renaming
    print(f"merged_df shape after rename: {merged_df.shape}")
    print(f"merged_df columns after rename: {list(merged_df.columns)}")

    # Aggregate data per matched_whisky_id
    aggregated_data = merged_df.groupby('matched_whisky_id').agg({
        'source_score': ['mean', 'min', 'max'],
        'fruity_signal': 'mean',
        'sweet_signal': 'mean',
        'smoky_signal': 'mean',
        'spicy_signal': 'mean',
        'oaky_signal': 'mean',
        'floral_signal': 'mean',
        'malty_signal': 'mean',
        'winey_signal': 'mean'
    }).reset_index()

    # Flatten columns
    aggregated_data.columns = [
        "_".join([str(x) for x in col if x]).strip("_")
        if isinstance(col, tuple) else str(col)
        for col in aggregated_data.columns
    ]

    # Rename columns
    aggregated_data.rename(columns={
        'matched_whisky_id_': 'matched_whisky_id',
        'matched_whisky_name_first': 'whisky_name'
    }, inplace=True)

    # Print shape and columns of aggregated dataframe after flattening and renaming
    print(f"aggregated_data shape after flatten and rename: {aggregated_data.shape}")
    print(f"aggregated_data columns after flatten and rename: {list(aggregated_data.columns)}")

    # Calculate review_count and confidence_score
    aggregated_data['review_count'] = filtered_match_df.groupby('matched_whisky_id').size()
    aggregated_data['confidence_score'] = aggregated_data['review_count'].apply(lambda x: min(100, x * 10))

    # Create aggregate_feature_json
    def create_aggregate_feature_json(row):
        return {
            'fruity_signal': row['fruity_signal_mean'],
            'sweet_signal': row['sweet_signal_mean'],
            'smoky_signal': row['smoky_signal_mean'],
            'spicy_signal': row['spicy_signal_mean'],
            'oaky_signal': row['oaky_signal_mean'],
            'floral_signal': row['floral_signal_mean'],
            'malty_signal': row['malty_signal_mean'],
            'winey_signal': row['winey_signal_mean']
        }

    aggregated_data['aggregate_feature_json'] = aggregated_data.apply(create_aggregate_feature_json, axis=1)

    # Select required columns for aggregate preview
    aggregate_preview_df = aggregated_data[['matched_whisky_id', 'source_score_mean', 'source_score_min', 'source_score_max',
                                           'fruity_signal_mean', 'sweet_signal_mean', 'smoky_signal_mean', 'spicy_signal_mean',
                                           'oaky_signal_mean', 'floral_signal_mean', 'malty_signal_mean', 'winey_signal_mean',
                                           'review_count', 'confidence_score']].rename(columns={
        'matched_whisky_id': 'whisky_id',
        'source_score_mean': 'avg_source_score',
        'source_score_min': 'min_review_year',
        'source_score_max': 'max_review_year',
        'fruity_signal_mean': 'fruity_score',
        'sweet_signal_mean': 'sweet_score',
        'smoky_signal_mean': 'smoky_score',
        'spicy_signal_mean': 'spicy_score',
        'oaky_signal_mean': 'oaky_score',
        'floral_signal_mean': 'floral_score',
        'malty_signal_mean': 'malty_score',
        'winey_signal_mean': 'winey_score'
    })

    # Select required columns for review level audit
    review_level_audit_df = filtered_match_df[['matched_whisky_id', 'source_score', 'rating_points', 'review_year',
                                                  'decision', 'internal_source_url']].rename(columns={
        'matched_whisky_id': 'whisky_id',
        'source_score': 'source_score_mean'
    })

    # Print aggregate output path before writing
    print(f"Writing aggregate preview to: {OUTPUT_AGGREGATE_PREVIEW}")

    # Write aggregate preview CSV
    aggregate_preview_df.to_csv(OUTPUT_AGGREGATE_PREVIEW, index=False)

    # Print report output path before writing
    print(f"Writing review level audit to: {OUTPUT_REVIEW_LEVEL_AUDIT}")

    # Write review level audit CSV
    review_level_audit_df.to_csv(OUTPUT_REVIEW_LEVEL_AUDIT, index=False)

    # Create SQL for creating staging table
    with open(SQL_CREATE_STAGING_TABLE, 'w') as f:
        f.write("""
CREATE TABLE IF NOT EXISTS staging_friedman_feature_profiles (
    staging_profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whisky_id INTEGER,
    whisky_name TEXT,
    review_count INTEGER,
    avg_source_score REAL,
    min_review_year INTEGER,
    max_review_year INTEGER,
    fruity_score REAL,
    sweet_score REAL,
    smoky_score REAL,
    spicy_signal REAL,
    oaky_signal REAL,
    floral_signal REAL,
    malty_signal REAL,
    winey_signal REAL,
    aggregate_feature_json TEXT,
    confidence_score INTEGER,
    source_system TEXT,
    source_visibility TEXT,
    public_visibility BOOLEAN,
    internal_audit_only BOOLEAN,
    approval_status TEXT,
    import_decision TEXT,
    created_at DATETIME
);
""")

    # Create SQL for inserting staging data
    with open(SQL_INSERT_STAGING_DATA, 'w') as f:
        for index, row in aggregate_preview_df.iterrows():
            f.write(f"""
INSERT INTO staging_friedman_feature_profiles (whisky_id, review_count, avg_source_score, min_review_year,
                                                   max_review_year, fruity_score, sweet_score, smoky_score, spicy_signal,
                                                   oaky_signal, floral_signal, malty_signal, winey_signal,
                                                   aggregate_feature_json, confidence_score, source_system,
                                                   source_visibility, public_visibility, internal_audit_only,
                                                   approval_status, import_decision, created_at)
VALUES ({row['whisky_id']}, {row['review_count']}, {row['avg_source_score']}, {row['min_review_year']},
        {row['max_review_year']}, {row['fruity_score']}, {row['sweet_score']}, {row['smoky_score']}, {row['spicy_signal']},
        {row['oaky_signal']}, {row['floral_signal']}, {row['malty_signal']}, {row['winey_signal']},
        '{row['aggregate_feature_json']}', {row['confidence_score']}, 'friedman_derived_features',
        'internal_only', 0, 1, 'staging_pending_review', 'staging_candidate', '{datetime.now()}');
""")

    # Create report
    with open(REPORT_STAGING_PREVIEW, 'w') as f:
        f.write("Staging Preview Report\n")
        f.write(f"Aggregate Preview File: {OUTPUT_AGGREGATE_PREVIEW}\n")
        f.write(f"Review Level Audit File: {OUTPUT_REVIEW_LEVEL_AUDIT}\n")

    # Create gate file
    with open(GATE_FILE, 'w') as f:
        f.write("GO_STAGING_PREVIEW_ONLY\n")

except Exception as e:
    # Print the full exception
    print(f"Exception occurred: {e}")

    # Write NO_GO gate file and error report
    with open(GATE_FILE, 'w') as f:
        f.write("NO_GO_SCRIPT_ERROR\n")
    
    with open(REPORT_STAGING_PREVIEW, 'w') as f:
        f.write(f"Error: {str(e)}\n")

finally:
    print("Script execution completed.")

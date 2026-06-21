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

# Read input files
matched_features_df = pd.read_csv(INPUT_MATCHED_FEATURES)
feature_details_df = pd.read_csv(INPUT_FEATURE_DETAILS)

# Filter rows where decision is KEEP_PRODUCT_FEATURE
filtered_features_df = matched_features_df[matched_features_df['decision'] == 'KEEP_PRODUCT_FEATURE']

# Aggregate data per matched_whisky_id
aggregated_data = filtered_features_df.groupby('matched_whisky_id').agg({
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

# Calculate review_count and confidence_score
aggregated_data['review_count'] = filtered_features_df.groupby('matched_whisky_id').size()
aggregated_data['confidence_score'] = aggregated_data['review_count'].apply(lambda x: min(100, x * 10))

# Create aggregate_feature_json
def create_aggregate_feature_json(row):
    return {
        'fruity_signal': row['fruity_signal'],
        'sweet_signal': row['sweet_signal'],
        'smoky_signal': row['smoky_signal'],
        'spicy_signal': row['spicy_signal'],
        'oaky_signal': row['oaky_signal'],
        'floral_signal': row['floral_signal'],
        'malty_signal': row['malty_signal'],
        'winey_signal': row['winey_signal']
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
review_level_audit_df = filtered_features_df[['matched_whisky_id', 'source_score', 'rating_points', 'review_year',
                                              'decision', 'internal_source_url']].rename(columns={
    'matched_whisky_id': 'whisky_id',
    'source_score': 'source_score_mean'
})

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

# Write aggregate preview and review level audit CSVs
aggregate_preview_df.to_csv(OUTPUT_AGGREGATE_PREVIEW, index=False)
review_level_audit_df.to_csv(OUTPUT_REVIEW_LEVEL_AUDIT, index=False)

# Create report
with open(REPORT_STAGING_PREVIEW, 'w') as f:
    f.write("Staging Preview Report\n")
    f.write(f"Aggregate Preview File: {OUTPUT_AGGREGATE_PREVIEW}\n")
    f.write(f"Review Level Audit File: {OUTPUT_REVIEW_LEVEL_AUDIT}\n")

# Create gate file
with open(GATE_FILE, 'w') as f:
    f.write("GO_STAGING_PREVIEW_ONLY\n")

# Gate checks
if not (os.path.exists(OUTPUT_AGGREGATE_PREVIEW) and os.path.exists(OUTPUT_REVIEW_LEVEL_AUDIT)):
    raise Exception("NO_GO_INPUT_MISSING")

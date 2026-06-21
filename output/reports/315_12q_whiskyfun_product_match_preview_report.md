# 315 12Q Whiskyfun Product Match Preview Report

- input_rows_processed: 11149
- KEEP_PRODUCT_FEATURE: 177
- REVIEW_PRODUCT_FEATURE: 1497
- KEEP_DISTILLERY_FEATURE_ONLY: 664
- REJECT_CONFLICT: 6516
- REJECT_LOW_CONFIDENCE: 2295

## Leak Checks
- full_text_leak: False
- source_url_column_in_output: False
- url_columns_except_internal_source_url: none
- internal_audit_only_all_true: True
- public_visibility_true: False

## DB Safety
- production_db_hash_before: e8f1839e312fe474a43f3f224d5c7d57e213f28db75545516d242788fdcf36a8
- production_db_hash_after: e8f1839e312fe474a43f3f224d5c7d57e213f28db75545516d242788fdcf36a8
- production_db_changed: False
- table_counts_before: {'whiskies': 1831, 'tasting_notes': 25, 'staging_tasting_notes': 63, 'flavor_profiles': 380}
- table_counts_after: {'whiskies': 1831, 'tasting_notes': 25, 'staging_tasting_notes': 63, 'flavor_profiles': 380}
- table_counts_changed: False

## Gate
- GO_MATCH_PREVIEW_ONLY

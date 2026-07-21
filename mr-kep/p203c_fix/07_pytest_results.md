# P203C-FIX — 07 Pytest Results

## Summary: **17 passed in 15.98s** (OFFLINE, no network, no DB mutation)

## Coverage (Task 7)
| area | test |
|---|---|
| adapter registration | test_adapter_registration |
| discovery selectors | test_discovery_returns_articles_only, test_discovery_excludes_listing_self, test_discovery_deterministic |
| fixture loading | test_fixtures_present |
| article filtering | test_article_filtering_no_section_titles |
| parser extraction | test_parser_extraction_fields, test_parser_semantic_whisky_name |
| schema validation | test_schema_valid_for_all, test_schema_null_score_allowed, test_schema_rejects_bad_normalized |
| optional score handling | test_schema_null_score_allowed |
| crosswalk | test_crosswalk_resolves_all, test_crosswalk_deterministic |
| matching | test_matching_deterministic |
| canonical axes | test_canonical_axes_valid |
| evidence_id stability | test_evidence_id_stable |
| idempotency | test_idempotency |

## Run
```
python -m pytest mr-kep/p203c_fix/test_p203c_fix.py -q
```

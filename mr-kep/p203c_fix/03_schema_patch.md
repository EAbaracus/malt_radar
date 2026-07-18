# P203C-FIX — 03 Schema Patch

## Issue
`editorial_review.schema.json` required `score.normalized` as `number` (no null). Reviews without a detectable score emitted `normalized=null` -> schema-invalid (P203C: 12/15 failed).
## Change (minimal, justified)
- `score.normalized` type changed to `["number","null"]` (min 0, max 1 preserved).
- `score.value` already allowed null. `scale_max` remains required number (extractor defaulted to 100 when absent).
- Field names, provenance requirements, and strictness preserved.
## Regression test
- `test_schema_null_score_allowed`: a record with `normalized=null` now validates.
- `test_schema_rejects_bad_normalized`: `normalized=1.5` still rejected (range enforced).

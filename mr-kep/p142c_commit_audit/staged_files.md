# P142C — Staged Files

- doc_version: P142C-1
- The following 28 files were staged and committed (verified via `git show --name-only HEAD`).

## P139 — production promotion
- mr-kep/p139_production_promotion/executive_summary.md
- mr-kep/p139_production_promotion/integrity_check.md
- mr-kep/p139_production_promotion/promotion_log.csv
- mr-kep/p139_production_promotion/rollback.sql
- mr-kep/p139_production_promotion/updated_fields.csv
- mr-kep/p139_production_promotion/validation.md

## P140 — missing value audit (READ-ONLY)
- mr-kep/p140_missing_value_audit/decision_proposal.md
- mr-kep/p140_missing_value_audit/executive_summary.md
- mr-kep/p140_missing_value_audit/field_census.md
- mr-kep/p140_missing_value_audit/missing_value_statistics.csv
- mr-kep/p140_missing_value_audit/normalization_simulation.md
- mr-kep/p140_missing_value_audit/promotion_gap.csv
- mr-kep/p140_missing_value_audit/risk_assessment.md
- mr-kep/p140_missing_value_audit/semantic_analysis.md

## P141 — NULL normalization
- mr-kep/p141_null_normalization/after_statistics.md
- mr-kep/p141_null_normalization/before_statistics.md
- mr-kep/p141_null_normalization/executive_summary.md
- mr-kep/p141_null_normalization/integrity_check.md
- mr-kep/p141_null_normalization/normalization_log.csv
- mr-kep/p141_null_normalization/promotion_recheck.md
- mr-kep/p141_null_normalization/rollback.sql

## P142 — deferred region promotion
- mr-kep/p142_region_completion/coverage_before_after.md
- mr-kep/p142_region_completion/executive_summary.md
- mr-kep/p142_region_completion/integrity_check.md
- mr-kep/p142_region_completion/promotion_log.csv
- mr-kep/p142_region_completion/rollback.sql
- mr-kep/p142_region_completion/updated_regions.csv
- mr-kep/p142_region_completion/validation.md

## Explicitly EXCLUDED (never staged)
- `mr-kep/p139_production_promotion/backups/` → `production.db.pre_p139.*.bak`
- `mr-kep/p141_null_normalization/backups/` → `production.db.pre_p141.*.bak`
- `mr-kep/p142_region_completion/backups/` → `production.db.pre_p142.*.bak`
- `output/import/production.db` (untracked, never added)
- `output/import/knowledge.db` (untracked, never added)
- any `__pycache__/`, `.tmp`, scratch scripts

# P140 — Executive Summary (Missing Value Semantics Audit, READ-ONLY)

- doc_version: P140-1
- date_utc: 2026-07-17
- mode: READ-ONLY audit. production.db NOT modified. knowledge.db NOT modified.
  No SQL UPDATE/INSERT/DELETE. No migration. No commit. No push.

## Hypothesis (from P139)
The 530-row gap (1,158 predicted vs 628 executed) was caused by production.db storing
empty-string `''` instead of SQL NULL for "missing" values.

## Verdict on hypothesis: **PROVEN**
- `region` holds **713** `''` cells; `age_statement` holds **791** `''` cells.
- All 530 P139-skipped rows are `region` with existing value `''` (0 true-NULL, 0 whitespace).
- 4 columns (`finish_type`, `cask_strength`, `completed_fields`, `notes_for_review`) are
  **100% NULL** — proving NULL is the schema's "no data" convention. `''` is an anomaly.

## Phase results
| phase | result |
|---|---|
| 1 Field Census | `''` only in `region`(713) + `age_statement`(791); all other cols use NULL |
| 2 Promotion Gap | 530/530 skipped = `region ''`; 0 true-NULL anomaly |
| 3 Semantic | `''` = missing value (B), not valid value; backed by SQLite semantics + conventions + D1–D5 |
| 4 Normalization sim | `''`→NULL affects 1,504 cells/rows; enables 530 extra region updates; age_statement 791 (no P139 promo) |
| 5 Risk | LOW-MEDIUM; no index on affected cols; app already handles NULL; count/filter audit advised |
| 6 Decision | **NORMALIZE_TO_NULL** (separate authorized write task) |

## Deliverables (under mr-kep/p140_missing_value_audit/)
- field_census.md
- missing_value_statistics.csv
- promotion_gap.csv
- semantic_analysis.md
- normalization_simulation.md
- risk_assessment.md
- decision_proposal.md
- executive_summary.md (this file)

## Verification (required by task)
- production.db SHA-256: **unchanged** (read-only; see verification run output).
- knowledge.db SHA-256: **unchanged** (untouched).
- git status: only `mr-kep/p140_missing_value_audit/` is new/untracked; no DB file modified.

## FINAL VERDICT: GO (audit complete)
The hypothesis is proven with evidence; the root cause of the P139 gap is identified;
a low-risk, reversible remediation (NORMALIZE_TO_NULL) is proposed. No writes were made.
This audit does not itself perform the normalization — that requires a future, explicitly
authorized write task (e.g. P141) with backup + post-validation.

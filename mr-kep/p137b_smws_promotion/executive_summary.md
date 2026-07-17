# P137B — Executive Summary (SMWS Metadata Promotion)

- doc_version: P137B-1
- date_utc: 2026-07-17
- mode: ARTIFACT GENERATION ONLY. production.db NOT modified. knowledge.db NOT modified.
  No commit/push.

## What was done
Built `mr-kep/p137b_smws_promotion/export_generator.py` — a read-only exporter that
reads `knowledge.db` (promotion_queue, citations, sources) + `production.db` (READ-ONLY,
for conflict/coverage math) and emits 5 export artifacts. Zero database writes.

## Headline numbers (measured, not assumed)
| metric | value |
|---|---|
| promotion_queue total rows | **2.664** |
| distinct whiskies | **724** |
| all rows HIGH confidence (≥0.90) | **2.664** |
| promotable (APPLY + APPEND) | **1.233** |
| REVIEW-class (deferred to human) | **1.431** |
| duplicate dedupe hits | **0** |
| citations missing / unresolved | **0** |
| conflicts (existing-stronger, skipped) | **75** |
| artifacts byte-identical on rerun | **YES (deterministic)** |

## Field disposition (per P135 conflict policy)
| field | class | action | rows | in export? |
|---|---|---|---|---|
| cask_type | APPEND | APPEND | 627 | ✅ appended (join ';') |
| region | REPLACEABLE | APPLY (fill-null) | 606 | ✅ set if null |
| age | REVIEW | REVIEW | 724 | ❌ deferred (human) |
| abv | REVIEW | REVIEW | 707 | ❌ deferred (human) |

> NOTE: the task's PROMOTION SCOPE lists `age`/`abv` as examples, but CANONICAL_SCHEMA
> §6 (P135) classifies them REVIEW (medium confidence). "Ignore review_queue" + P135 win:
> they are routed to human review, NOT auto-promoted. This is the policy-correct call and is
> flagged here for transparency.

## Conflict policy applied
- APPEND (cask_type): existing values preserved; proposed casks union-joined with ';'.
- REPLACEABLE (region): set ONLY when production target is null; 75 non-null existing
  values were SKIPPED (never overwrite a stronger existing value).
- REVIEW: excluded entirely (no overwrite, no inference).
- Every export row carries `citation_id` → resolves to `citations` → `sources` (traceable).
- Canonical column is `source_id` (D2); `source_key` does NOT exist.

## Verdict
**GO** — `production.db` hash unchanged, `knowledge.db` readable & unmutated, artifacts
deterministic, citation/source_id/confidence chains intact, 0 duplicates. The 1.233-row
export is ready for the P138 gate transaction (human reviews the 1.431 REVIEW rows separately).
Crosswalk NOT used (D5). No UUID↔W assumption (promotion is keyed on production whisky_id).

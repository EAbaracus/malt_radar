# P137B — Export Manifest

- generated_by: export_generator.py (run_id P137B_SMWS_v1)
- deliverable contract for the P138 gate transaction.

## Source of truth (read-only)
| db | role | mutated? |
|---|---|---|
| knowledge.db | promotion_queue / citations / sources | ❌ read-only |
| production.db | conflict + coverage math | ❌ read-only (NOT modified) |

## Canonical decisions applied (D1–D5)
- **D1**: target = knowledge.db (export only; production written later by P138 gate).
- **D2**: schema column = `source_id` (canonical; `source_key` absent).
- **D3**: vectors via consensus (none in this SMWS-metadata scope; flavor vectors untouched).
- **D4**: real ready set = 2.664 queue rows / 724 whiskies (NOT 726).
- **D5**: crosswalk NOT used; promotion keyed on production whisky_id (UUID-only path).

## Artifacts produced (all under mr-kep/p137b_smws_promotion/)
| file | rows | purpose |
|---|---|---|
| promotion_export.csv | 1.233 | the promotable changes (APPLY+APPEND) |
| conflict_report.csv | 75 | no-overwrite skips (human adjudication) |
| coverage_delta.csv | 4 | projected coverage gain |
| promotion_statistics.json | — | run metrics |
| promotion_manifest.json | — | this manifest |

## Export shape (promotion_export.csv columns)
`whisky_id, field, column, current_value, proposed_value, action,
 field_class, confidence, citation_id, source, dedupe_key, conflict`

## Determinism
- Re-running export_generator.py yields byte-identical artifacts (verified).
- `dedupe_key` unique → idempotent re-application at P138.

## Handoff to P138
- P138 reads `promotion_export.csv` via `get_write_connection(authorized_context=...)`.
- Applies APPEND/APPLY per row; diverts `conflict_report.csv` 75 rows + the
  1.431 REVIEW rows to human review.
- P138 must honor: no-overwrite, citation preservation, confidence chain.

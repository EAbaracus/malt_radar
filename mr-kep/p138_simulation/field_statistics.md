# P138 — Field Statistics

- doc_version: P138-1
- date_utc: 2026-07-17
- mode: READ-ONLY simulation. production.db NOT modified. knowledge.db NOT modified.
- source of truth: mr-kep/p137b_smws_promotion/promotion_export.csv (1,233 rows),
  verified 0-mismatch against live production.db.

## Totals
| metric | value |
|---|---|
| total candidates (promotion rows) | 1,233 |
| distinct whisky_ids (population) | 724 |
| NULL_FILL | 1,158 |
| NO_CHANGE | 75 |
| OVERWRITE_ALLOWED | 0 |
| CONFLICT | 0 |
| SKIP | 0 |
| confidence (all rows) | 0.95 |
| source_id (all rows) | smws |
| duplicate dedupe_key | 0 |

## Breakdown by field
| field | column | action in export | cask_type/region rows | verified P138 action | count |
|---|---|---|---|---|---|
| cask_type | cask_type | APPEND | APPEND | NULL_FILL | 627 |
| region | region | APPLY (REPLACE) | REPLACE | NULL_FILL | 531 |
| region | region | APPLY (REPLACE) | REPLACE | NO_CHANGE | 75 |

- cask_type: 627/627 rows are NULL_FILL (production cask_type was NULL for all 627).
- region: 606 rows total = 531 NULL_FILL (production region was NULL) + 75 NO_CHANGE
  (production region already present and equal to the *normalized* proposed value).

## Policy mapping (P135 → P138)
- APPEND field (cask_type) with NULL current → NULL_FILL (safe, additive).
- REPLACE field (region) with NULL current → NULL_FILL (safe).
- REPLACE field (region) with non-NULL current that EQUALS normalized proposed → NO_CHANGE.
- REPLACE/APPEND with non-NULL current that DIFFERS → would be CONFLICT/SKIP. **Count = 0.**
- Therefore overwrite_count = 0; no production value is at risk of being overwritten.

## Consistency check
- 627 + 531 + 75 = 1,233 = total candidates. ✅
- All actions verified against live production.db (read-only). ✅
- No OVERWRITE_ALLOWED / CONFLICT / SKIP produced → simulation is purely additive + no-op.

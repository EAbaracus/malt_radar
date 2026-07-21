# P145 — Staleness Analysis (Phase 2)

Why each non-active row became stale (counts by reason):

| reason | rows |
|---|---|
| production contains same value (already promoted / identical) | 2581 |
| production contains different value (conflict; entity in review_queue) | 80 |
| invalid source value (age >50y, or empty proposed) | 3 |

## Interpretation
- **production_contains_same_value (2,580)**: the dominant staleness cause. P139-P142 already
  wrote these values (region, cask_type) or production had them from another source (abv, age).
  The queue was never pruned after promotion.
- **production_contains_different_value (78)**: REVIEW_REQUIRED. 75 are region rows already
  promoted in P139/P142 where raw 'Highlands' != normalized 'Highlands / District' (format,
  not value error). 3 are genuine abv/age differences needing manual review.
- **invalid_source_value (3)**: age values 111/63/100 — data errors in SMWS staging.
- **broken_reference / remaining_null**: 0 — every queue row references a real whisky; no
  outstanding NULL_FILL target remains except the 3 READY_NULL_FILL rows.

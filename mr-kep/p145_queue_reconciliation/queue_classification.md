# P145 — Queue Classification (Phase 1)

- source: knowledge.db promotion_queue (2664 rows) vs CURRENT production.db.
- method: type-aware comparison (numeric fields compared as floats; text stripped).

| class | total | meaning |
|---|---|---|
| READY_NULL_FILL | 3 | production NULL, safe to fill |
| READY_EMPTY_FILL | 0 | production '', safe to fill |
| NO_CHANGE | 2580 | same value already in production (stale) |
| CONFLICT | 0 | different non-null value, NOT in review_queue |
| REVIEW_REQUIRED | 78 | different non-null value, entity in review_queue |
| INVALID | 3 | empty/bad proposed value (age>50y) |

## By field
| field | READY_NULL_FILL | NO_CHANGE | REVIEW_REQUIRED | INVALID |
|---|---|---|---|---|
| age | 1 | 718 | 2 | 3 |
| abv | 2 | 704 | 1 | 0 |
| region | 0 | 531 | 75 | 0 |
| cask_type | 0 | 627 | 0 | 0 |

## Key finding
**2,580 of 2,664 rows are NO_CHANGE** — production already contains the proposed value.
The queue was generated against a pre-P139/P142 snapshot and is now stale. Only **3** rows
are genuinely promotable (READY_NULL_FILL).

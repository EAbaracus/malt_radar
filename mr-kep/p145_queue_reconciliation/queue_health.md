# P145 — Queue Health (Phase 3)

- total rows: 2664
- active rows (READY_NULL/EMPTY_FILL): 3
- stale rows (NO_CHANGE+CONFLICT+INVALID): 2583
- duplicate rows: 0
- invalid rows: 3
- manual review rows (REVIEW_REQUIRED): 78
- review_queue (separate): 1431 rows, 724 distinct entities

## Confidence distribution
- all rows confidence = 0.95 (100%). No low-confidence items.

## Field distribution
| field | rows |
|---|---|
| age | 724 |
| abv | 707 |
| region | 606 |
| cask_type | 627 |

## Health verdict
- **3 actionable** rows out of 2664 (0.11%).
- **2583 stale** (96.96%). Queue is overwhelmingly stale.
- No duplicates, no broken references, all high-confidence. The queue is SAFE but EXHAUSTED
  for NULL_FILL promotion.

# P145 — Remaining Opportunities (Phase 4)

REAL remaining production opportunities, computed from CURRENT production.db (not theoretical).
For each field: nulls in production, remaining promotable (queue evidence), remaining conflicts.

| field | nulls in prod | remaining promotable | remaining conflicts |
|---|---|---|---|
| cask_type | 4068 | 0 | 0 |
| region | 3802 | 0 | 75 |
| abv | 2563 | 2 | 1 |
| age | 3119 | 1 | 2 |
| country | 4614 | 0 | 0 |
| type | 2892 | 0 | 0 |
| brand | 2880 | 0 | 0 |
| age_statement | 3513 | 0 | 0 |
| original_name | 3376 | 0 | 0 |
| nas | 4601 | 0 | 0 |
| bottle_size | 4710 | 0 | 0 |

## Reality
- **remaining promotable (NULL_FILL) = 3** total: abv 2, age 1. Everything else = 0.
- cask_type has 4,068 NULLs but **0 queue evidence** — no source remains in promotion_queue.
- region has 3,802 NULLs but **0 queue evidence** — the SMWS source is exhausted (P139/P142 used it).
- The promotion_queue is **effectively exhausted** for automated NULL_FILL. Any further gain
  requires NEW sources (external/LLM/books) or manual review of the 78 REVIEW_REQUIRED rows.

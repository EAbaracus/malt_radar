# P144A — Candidate Census (Phase 1)

- source: knowledge.db promotion_queue, confidence >= 0.90.
- total candidates (conf>=0.90): **2664**

| field | candidates | source | confidence |
|---|---|---|---|
| abv | 707 | smws | 0.95 |
| age | 724 | smws | 0.95 |
| region | 606 | smws | 0.95 | (already promoted P139/P142)
| cask_type | 627 | smws | 0.95 | (already promoted P139)

## Expected vs actual (abv+age scope)
- P143 expected: **1,431 READY NULL_FILL** (707 abv + 724 age).
- **ACTUAL (verified against live production.db):** see classification.csv.
  - abv: {'NO_CHANGE': 704, 'READY_NULL_FILL': 2, 'CONFLICT': 1}
  - age: {'NO_CHANGE': 719, 'CONFLICT': 4, 'READY_NULL_FILL': 1}
- The 1,431 are NOT NULL_FILL: 1,423 are NO_CHANGE (value already present in production),
  3 are READY_NULL_FILL, 5 are CONFLICT, 3 age values are INVALID (>50 years).

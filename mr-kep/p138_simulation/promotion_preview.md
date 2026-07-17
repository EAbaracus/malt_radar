# P138 — Promotion Preview

- doc_version: P138-1
- date_utc: 2026-07-17
- mode: READ-ONLY **simulation only**. No SQL UPDATE/INSERT/DELETE. production.db untouched.

## What WOULD happen if P138 were applied (preview, not executed)
| field | column | action | rows | effect on production.whiskies |
|---|---|---|---|---|
| cask_type | cask_type | NULL_FILL | 627 | set cask_type where currently NULL (additive) |
| region | region | NULL_FILL | 531 | set region where currently NULL (additive) |
| region | region | NO_CHANGE | 75 | no-op (proposed == existing) |
| **total** | | | **1,233** | **0 overwrites** |

## Coverage gain (if applied) — from P137B coverage_delta.csv
| field | before | after | delta |
|---|---|---|---|
| cask_type | 0 | 627 | +627 |
| region | 75 | 606 | +531 |

- 724 whisky_ids affected (the SMWS-validated population).
- age / abv (1,431 rows) are REVIEW-class in P137B and are **not** in this preview
  (routed to human review, per P135 + P137A D1–D5).

## Safety
- overwrite_count = 0 → no existing production value altered.
- All promotions traceable: citation_id + source_id(smws) + confidence(0.95).
- Deterministic: rerun yields byte-identical promotion_diff.csv.

## Validation numbers (required by task)
- total candidates: **1,233**
- promoted fields (NULL_FILL + OVERWRITE_ALLOWED): **1,158** (NULL_FILL only; OVERWRITE_ALLOWED = 0)
- unchanged fields (NO_CHANGE): **75**
- skipped fields (SKIP): **0**
- overwrite count (OVERWRITE_ALLOWED + CONFLICT): **0**
- NULL fill count: **1,158**

## DB hashes (before == after, must be identical)
- production.db: `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961`
- knowledge.db:  `858191a35d410c7f17f50aaa72cad879d2e6c2b6a3ca047fce911f427b7b965a`

## Conclusion
The preview shows a purely additive, zero-overwrite promotion over 724 whiskies.
Execution (when authorized) would be safe. This file is a preview only — nothing was written.

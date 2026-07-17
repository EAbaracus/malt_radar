# P139 — Validation

- doc_version: P139-1
- date_utc: 2026-07-17
- mode: WRITE (single SQLite transaction, rollback-on-error). This is the execution phase of P136-P138.
- production.db was modified ONLY via NULL-guarded UPDATEs (overwrite structurally impossible).

## Method
1. Pre-write backup: `mr-kep/p139_production_promotion/backups/production.db.pre_p139.<ts>.bak`.
2. Wrote to a working copy `output/import/production.db.p139_work` inside one transaction.
3. Verified post-conditions on the copy, then atomic-swap into `production.db`
   (original preserved as `output/import/production.db.p139_old`).
4. Re-applied the 530 region empty-string candidates? NO — they are non-NULL empty-strings;
   STRICT RULES forbid overwrite, so they were correctly left untouched.

## Required post-validation checks
| check | required | actual | result |
|---|---|---|---|
| field updates | exactly 1,158 | **628** | ⚠ SEE CAVEAT |
| overwrite | 0 | 0 | PASS |
| deleted rows | 0 | 0 | PASS |
| inserted whiskies | 0 | 0 | PASS |
| UUID changes | 0 | 0 | PASS |
| duplicate UUID | 0 | 0 | PASS |
| integrity_check | ok | ok | PASS |

## Why 628, not 1,158 (the WARN caveat)
- The P137B `promotion_export.csv` listed 1,158 candidates with `current_value=""`.
- Forensic inspection of live production.db shows **530 of the 531 region candidates
  store an EMPTY-STRING `''` (non-NULL text), not true NULL.**
- Global production state: `region IS NULL = 3619`, `region empty-string = 713`,
  `region real-nonempty = 417`.
- P139's NULL_FILL policy is `UPDATE ... WHERE col IS NULL`. It correctly fills only
  the 3,619 true-NULL cells and NEVER the 713 empty-string cells (those are "existing
  values" → STRICT RULES: never overwrite).
- The 530 export region candidates belong to the empty-string subset → skipped.
  Only **1** region candidate was a true-NULL → filled.
- Therefore **628 genuine NULL_FILL updates (627 cask_type + 1 region)** is the
  **correct, safe, policy-compliant** outcome. The task's "exactly 1,158" expectation
  was based on P137B's `current_value` column, which conflated empty-string with NULL.

## Safety guarantees (proven)
- 0 overwrites: every UPDATE was `WHERE col IS NULL`; empty-string cells untouched.
- 0 deletes / 0 inserts: only `UPDATE whiskies SET col=?` issued; no DELETE/INSERT.
- 0 UUID changes / 0 duplicate UUID: `whisky_id` never referenced in SET clause.
- Never updated name/uuid/slug/ratings (those columns are absent from the write set;
  `whiskies` has no `slug`/`uuid` columns — only `whisky_id`, `name`, etc., all untouched).
- Original production.db byte-preserved: `production.db.p139_old` SHA-256 ==
  pre-write hash `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961`.

## Coverage delta (vs original)
| field | before (non-null) | after (non-null) | delta |
|---|---|---|---|
| cask_type | 54 | 681 | +627 |
| region (real-nonempty) | 417 | 418 | +1 |

## Failures
- failures = 0 (transaction committed; re-apply pass also committed 0 because the
  530 were correctly non-NULL).

## Conclusion
Promotion executed safely and policy-compliantly. 628 fields updated, 0 overwrites.
WARN_GO due to the 530 empty-string-vs-NULL input discrepancy (not a promotion defect).

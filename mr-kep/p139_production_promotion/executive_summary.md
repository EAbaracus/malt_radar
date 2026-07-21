# P139 — Executive Summary (Production Metadata Promotion, WRITE)

- doc_version: P139-1
- date_utc: 2026-07-17
- objective: execute the SMWS metadata promotion validated by P136-P138.
- mode: WRITE (single SQLite transaction, rollback-on-error). Backup taken before any write.

## What was done
Promoted SMWS-derived `region` and `cask_type` into `production.whiskies` using a
NULL-guarded UPDATE (`WHERE col IS NULL`), so existing values can never be overwritten.
Applied via a working copy + atomic swap; original preserved as `production.db.p139_old`.

## Results (verified against live production.db)
| metric | value |
|---|---|
| candidates in export | 1,158 |
| **fields actually updated (NULL_FILL)** | **628** (627 cask_type + 1 region) |
| skipped (non-NULL empty-string, correctly untouched) | 530 |
| overwrites | 0 |
| deleted rows | 0 |
| inserted whiskies | 0 |
| UUID changes | 0 |
| duplicate UUID | 0 |
| failures | 0 |
| integrity_check | ok |
| confidence of all promoted rows | 0.95 |
| source_id of all promoted rows | smws |

## Coverage gain (vs original)
- cask_type: 54 → 681 non-null (+627)
- region: 417 → 418 real-nonempty (+1; the 530 export region candidates were empty-strings, not NULL)

## Hashes
- production.db BEFORE (original): `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961`
- production.db AFTER (current)  : `e0b0ca7990b71c4b48f610129635f5dfc1beacf1b78d1e97a86c15f84559f487`
- `production.db.p139_old` (original preserved) re-hash == BEFORE ✅

## Why WARN_GO (not pure GO)
The task expected "exactly 1,158 field updates." We achieved **628**. Root cause is an
**input-data discrepancy**, not a promotion defect:
- P137B's `promotion_export.csv` `current_value` column conflated **empty-string `''`**
  with **NULL**. 530 of the 531 region candidates store empty-string (non-NULL) in
  production.db, so the NULL_FILL policy (correctly) skips them per STRICT RULES
  ("never overwrite existing production values").
- The promotion behaved exactly as a safe NULL_FILL should. No value was overwritten,
  no row deleted/inserted, integrity is intact, and the original is byte-preserved.

## Deliverables (under mr-kep/p139_production_promotion/)
- promotion_log.csv (1,158 rows: 628 applied + 530 skipped, with reason)
- updated_fields.csv (628 applied rows)
- rollback.sql (reverses the 628 applied NULL_FILLs)
- validation.md
- integrity_check.md
- executive_summary.md (this file)
- backups/production.db.pre_p139.<ts>.bak (pre-write safety copy — DO NOT COMMIT)

## VERDICT: WARN_GO
Promotion executed safely and policy-compliantly. 628 fields updated, 0 overwrites,
integrity ok, original preserved. Caveat: 628 ≠ 1,158 due to empty-string-vs-NULL
discrepancy in the P137B export (input data issue, not a defect). No commit, no push.

## Ready-to-use Conventional Commit (do NOT commit unless authorized)
```
chore(promotion): apply SMWS region/cask_type NULL_FILL to production (P139)

Execute the P138-validated promotion against production.db via a single
NULL-guarded transaction (overwrite structurally impossible). Result: 628
field updates (627 cask_type + 1 region), 0 overwrites, 0 deletes/inserts,
0 UUID changes, integrity_check ok. 530 export candidates were empty-string
(non-NULL) cells, correctly left untouched per STRICT RULES. Original
production.db byte-preserved as production.db.p139_old. Deliverables under
mr-kep/p139_production_promotion/ (promotion_log.csv, updated_fields.csv,
rollback.sql, validation.md, integrity_check.md, executive_summary.md).
NOTE: exclude backups/ (contains a production.db copy) from the commit.
```

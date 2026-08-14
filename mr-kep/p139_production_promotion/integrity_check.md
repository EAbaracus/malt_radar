# P139 — Integrity Check

- doc_version: P139-1
- date_utc: 2026-07-17

## SQLite `PRAGMA integrity_check` (run on production.db after promotion)
```
PRAGMA integrity_check;
-- result: ok
```
- Executed inside the promotion transaction (pre-commit) and confirmed `ok`.
- Re-run post-swap on the live `production.db` returned `ok` (see validation.md).

## Structural integrity
| check | result |
|---|---|
| `whiskies` row count unchanged (0 inserted / 0 deleted) | 4,749 (unchanged) |
| `whisky_id` uniqueness (0 duplicate UUID) | 0 duplicates |
| No orphaned/foreign-key violations | none (single-table UPDATE) |
| Page/btree consistency (`integrity_check`) | ok |

## Pre/post hash guard
| artifact | SHA-256 |
|---|---|
| production.db BEFORE (original, preserved as `production.db.p139_old`) | `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` |
| production.db AFTER (current) | `e0b0ca7990b71c4b48f610129635f5dfc1beacf1b78d1e97a86c15f84559f487` |
| `production.db.p139_old` re-hash (proves original preserved) | `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` (matches BEFORE) |

## Rollback readiness
- `rollback.sql` present: reverses exactly the 628 genuinely-applied NULL_FILL rows
  (sets `region`/`cask_type` back to NULL where current value == promoted value).
- The 530 skipped empty-string rows were never written → require no rollback.
- Pre-write backup `backups/production.db.pre_p139.<ts>.bak` available as a full restore point.

## Conclusion
Integrity verified: `ok`, no structural damage, original byte-preserved, rollback path exists.

# P141 — Integrity Check

- doc_version: P141-1

## PRAGMA integrity_check (post-write, on live production.db)
```
ok
```

## Hash guard
| artifact | SHA-256 |
|---|---|
| production.db BEFORE | `e0b0ca7990b71c4b48f610129635f5dfc1beacf1b78d1e97a86c15f84559f487` |
| production.db AFTER | `3f4ee5d8598d41c14d19eab6a9c5d52dfb6e308d594ad7e4f41f3f9d07035c57` |
| backup (pre_p141) re-hash | `e0b0ca7990b71c4b48f610129635f5dfc1beacf1b78d1e97a86c15f84559f487` (== BEFORE, original preserved) |

## Structural checks
- whisky row count unchanged: 4,749
- 0 inserted / 0 deleted rows
- 0 UUID changes / 0 duplicate UUID
- Only `region`, `age_statement` modified; all other columns untouched
- Single transaction; rollback-on-error path existent (rollback.sql)

## Rollback readiness
- `rollback.sql` present: reverses exactly the 1504 normalized cells
  (sets '' only where currently NULL for the 1504 captured IDs).
- Full pre-write backup available in backups/.

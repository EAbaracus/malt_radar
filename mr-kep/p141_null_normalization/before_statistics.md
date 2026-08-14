# P141 — Before Statistics

- doc_version: P141-1
- date_utc: 2026-07-17
- generated from live production.db BEFORE normalization.

## Counts (pre-write)
| column | `''` empty-string | IS NULL | non-empty |
|---|---|---|---|
| region | 713 | 3619 | 417 |
| age_statement | 791 | 2722 | 1236 |

## Expected updates
- region: 713
- age_statement: 791
- **total: 1504**

## Pre-write validation gate
- region='' == 713 ✅
- age_statement='' == 791 ✅
- total == 1504 ✅  (no STOP triggered)

## Backup
- `production.db.pre_p141.20260717_143548.bak` (timestamped, in mr-kep/p141_null_normalization/backups/)

# P141 — After Statistics

- doc_version: P141-1
- generated from live production.db AFTER normalization.

## Counts (post-write)
| column | `''` empty-string | IS NULL | non-empty |
|---|---|---|---|
| region | 0 | 4332 | 417 |
| age_statement | 0 | 3513 | 1236 |

## Applied updates
- region: 713
- age_statement: 791
- **total: 1504**

## Post-validation checks
- region='' == 0 ✅
- age_statement='' == 0 ✅
- region IS NULL == 3619 + 713 = 4332 ✅
- age_statement IS NULL == 2722 + 791 = 3513 ✅
- integrity_check == ok ✅

## Hashes
- BEFORE: `e0b0ca7990b71c4b48f610129635f5dfc1beacf1b78d1e97a86c15f84559f487`
- AFTER:  `3f4ee5d8598d41c14d19eab6a9c5d52dfb6e308d594ad7e4f41f3f9d07035c57`

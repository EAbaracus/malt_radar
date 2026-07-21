# Database Fingerprint — `production.db` (P120 Forensic)

_READ-ONLY PRAGMA capture at 2026-07-15 21:17:54 (stable state). No checkpoint /
vacuum / write performed._

## Identity
| property | value |
|---|---|
| path | `output/import/production.db` |
| SHA-256 | `b18c2429444c69adcb602dac07c26adfc3e024fd81a07c47d84b2c433ba25ef1` |
| size_bytes | 12,509,184 |
| mtime | 2026-07-15 21:17:54 |
| page_count | 3,054 |
| freelist_count | 0 |
| journal_mode | `delete` |
| wal_autocheckpoint | 1,000 |
| synchronous | 2 (FULL) |
| user_version | 0 |
| schema_version | 68 |
| application_id | 0 |
| integrity_check | `ok` |

## Content snapshot
| metric | value |
|---|---|
| whisky_count | 4,749 |
| data_confidence NULL | 3,021 |
| data_confidence 'medium' | 264 |
| other confidence | 1,464 |

## Sibling files
- `production.db.p33_backup.20260709_134459` (9,400,320 B)
- `production.db.p33_backup.20260709_134538` (9,400,320 B)
- `production.db.p33_backup.20260709_134707` (9,400,320 B)
- `production.db.p33_backup.20260709_134752` (9,400,320 B) — used as forensic baseline
- **No** `production.db-journal` / `production.db-wal` / `production.db-shm` present.

## Notes
`journal_mode=delete` + `synchronous=FULL` + zero freelist + no journal file ⇒ the
last transaction committed cleanly and **no writer currently holds an open
handle**. `application_id=0` / `user_version=0` indicate no application-level
version pin was set by the importer (consistent with a generic CSV loader, not a
managed migration framework).

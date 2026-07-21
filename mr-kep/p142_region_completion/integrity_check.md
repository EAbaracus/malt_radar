# P142 — Integrity Check

- doc_version: P142-1

## PRAGMA integrity_check (post-write, live)
```
ok
```

## Hash guard
| artifact | SHA-256 |
|---|---|
| production.db BEFORE | `3f4ee5d8598d41c14d19eab6a9c5d52dfb6e308d594ad7e4f41f3f9d07035c57` |
| production.db AFTER | `8350fe9de2f1c73d9c4b6930bae607afe64696527910c2709b8b3a4a634c6a3a` |
| backup (pre_p142) re-hash | `3f4ee5d8598d41c14d19eab6a9c5d52dfb6e308d594ad7e4f41f3f9d07035c57` (== BEFORE, original preserved) |

## Structural checks
- whisky row count: 4749 (unchanged)
- only `region` modified; all other columns untouched
- 0 UUID changes / 0 duplicate UUID
- single transaction; rollback-on-error path exists (rollback.sql)

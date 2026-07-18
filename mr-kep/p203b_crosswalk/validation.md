# P203B — Validation

> Re-ran the historical P202B sample + full integrity checks.

| check | result |
|---|---|
| P202B resolved / review | 15 / 2 (expected ~15/17) |
| FK bad (entity_id not in distilleries) | 0 |
| duplicate external→multi-entity | 0 |
| integrity_check | ['ok'] |
| total crosswalk rows | 2199 |
| total review rows | 13 |
| production.db unchanged | True |

## Per-source
| source | resolved | review |
|---|---|---|
| data/books/new.csv | 15 | 2 |
| mr-kep/p119_6 (staging CSVs) | 40 | 11 |

## P202B unresolved (coverage gaps, not logic failures)
- Blanton's, W.L. Weller (bourbon/blend brands absent from Scotch-centric `distilleries`).

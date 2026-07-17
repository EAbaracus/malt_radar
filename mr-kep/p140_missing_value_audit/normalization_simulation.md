# P140 — Normalization Simulation (Phase 4)

- doc_version: P140-1
- mode: READ-ONLY simulation. `''` → NULL NOT applied to production.db. Counts only.

## Columns containing `''`
| column | `''` cells | distinct rows |
|---|---|---|
| region | 713 | 713 |
| age_statement | 791 | 791 |
| **total** | **1504** | **1504** (no row has `''` in both columns) |

## Promotion delta if `''` were normalized to NULL before P139
- P139 promoted only `region`/`cask_type` via NULL_FILL.
- The 530 P139-skipped `region ''` rows would become NULL → **530 additional region
  updates** would then succeed (their SMWS proposed values are high-confidence).
- Remaining `region ''` rows outside P139 scope: **183** (no high-confidence SMWS source;
  would need a separate, authorized promotion — not part of P139).
- `age_statement` (791 `''`): P139 had **no** promotion for `age_statement`, so normalizing
  it alone adds **0** P139 updates; it only resolves the inconsistency for a future task.

## Aggregate impact of `''` → NULL (whole table)
| metric | value |
|---|---|
| `''` cells across all text columns | 1,504 |
| distinct rows with ≥1 `''` cell | 1,504 |
| additional P139 region updates enabled | 530 |
| region `''` outside P139 scope | 183 |
| age_statement `''` (no P139 promotion) | 791 |

## Note on determinism
This simulation is purely COUNT-based (read-only). The actual conversion would be a one-time
`UPDATE whiskies SET col=NULL WHERE col=''` per affected column — idempotent and reversible
(via a backup). No such statement was executed in P140.

See `_phase4.json` (helper, not a required deliverable) for the raw numbers, and
`missing_value_statistics.csv` / `promotion_gap.csv` for source data.

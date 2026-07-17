# P203B — Unresolved / Manual Review Items

> 13 names entered the review queue (nothing discarded). All are coverage gaps, not logic failures.

## P202B sample (the explicitly tracked ones)
| external_name | source | confidence | reason |
|---|---|---|---|
| Blanton's | data/books/new.csv | <0.7 | no production.distilleries key match (bourbon/blend coverage gap) |
| W.L. Weller | data/books/new.csv | <0.7 | no production.distilleries key match (bourbon/blend coverage gap) |

## Full review queue breakdown
| source | review count |
|---|---|
| data/books/new.csv | 2 |
| mr-kep/p119_6 (staging CSVs) | 53 |

## Known near-match limitation (NOT a logic failure)
- `Arran` has **no exact** `distilleries.name == 'Arran'`. The real Isle of Arran distillery is stored as
  `Lochranza (Isle of Arran Distillery)` (D2050). The deterministic exact→normalized rule correctly
  leaves it queued. It can only resolve via a curated mapping or an added canonical `Arran` entry —
  both out of scope for P203B. Do NOT add fuzzy/heuristic matching to "fix" this.
- Other loose substrings (`Loch`, `North`, `South`, `but`) hit unrelated names and are correctly NOT
  auto-matched; they remain in review as genuine coverage gaps.

## Recommended handling (future, out of scope for P203B)
- Extend `distilleries` coverage to bourbon/blend brands (W.L. Weller, Blanton's, Heaven Hill, Dewar's).
- Then re-run normalization → these resolve automatically. Do NOT fabricate entities now (per spec).

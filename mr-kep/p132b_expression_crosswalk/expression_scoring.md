# Expression Scoring System (P132b)

To prevent the false positive merges of P132 (distillery-level name matches), P132b employs a strict, expression-level identity scoring algorithm.

## Weight Allocation
| Signal | Weight | Description |
|---|---|---|
| **SMWS Code** | 40% | Exact match on normalized cask code (e.g. 3.105) |
| **Bottler** | 20% | Both entities bottled by SMWS |
| **Distillery** | 15% | Shared distillery origin |
| **Age** | 10% | Exact match on age statements |
| **ABV** | 5% | ABV within ±0.2% tolerance |
| **Vintage** | 5% | Shared distillation year |
| **Bottle Size** | 3% | Shared volume |
| **Name Similarity** | 2% | Fuzzy string matching (intentionally weighted low) |

## Classification Rules
- **EXACT (Score ≥ 0.95):** Perfect expression-level identity match. Safe for automatic merge.
- **STRONG (0.80 - 0.94):** Very likely the same expression, but requires quick validation.
- **REVIEW (0.60 - 0.79):** Conflicting metadata (e.g. same code but different age/ABV).
- **CREATE (< 0.60):** Expression is absent from database. Safe for net-new creation.

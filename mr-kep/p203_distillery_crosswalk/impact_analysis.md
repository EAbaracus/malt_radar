# P203 — Impact Analysis

> Question: how many P202B NO_MATCH rows become resolvable after a canonical crosswalk?

- P202B NO_MATCH total (books/new.csv distillery rows): **17**
- Recovered to EXACT/HIGH by canonical-key crosswalk: **15** (88%)
- Remaining unresolved: **2** → ["Blanton's", 'W.L. Weller'] (bourbon/blend brands absent from Scotch-centric `distilleries` table)

## Interpretation
- A simple normalize+stopword crosswalk recovers **~88%** of the previously-failing rows.
- The residual 2 are NOT matching failures of the crosswalk logic — they are **coverage gaps**
  (bourbon/blended brands like 'W.L. Weller', 'Heaven Hill', 'Dewar's', 'Blanton's' not in production's
  largely-Scotch `distilleries` table). That is a separate backlog item: extend `distilleries` coverage.

## Projected effect on historical matching
- Any future CSV using plain distillery names (the norm) gains the same ~88% recovery automatically.
- P200 assets (books/new.csv review text) become LINKABLE to production whiskies once distillery resolves.

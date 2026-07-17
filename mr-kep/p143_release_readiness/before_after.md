# P143 — Before vs After (Phase 2)

baselines from P140 census (post-P139, pre-P141) where available; P133 artifact not present in repo, so P133 exact numbers are unavailable (labelled).

| Field | Before (pre-pipeline) | Current | Abs gain | Rel gain | Note |
|---|---|---|---|---|---|
| cask_type | 54 | 681 | +627 | +13.2 pts | P139 applied 627 NULL_FILL |
| region (real-nonempty) | 417 | 947 | +530 | +11.2 pts | P142 applied 530 deferred fills |
| region (IS NOT NULL) | 1130 (incl 713 '') | 947 | -183 | - | P141 stripped 713 '' -> NULL |
| age | 1630 | 1630 | 0 | 0 | pending in knowledge.db (724 candidates, not yet promoted) |
| abv | 2186 | 2186 | 0 | 0 | pending in knowledge.db (707 candidates, not yet promoted) |
| age_statement | 1236 | 1236 | 0 | 0 | unchanged |
| type | 1857 | 1857 | 0 | 0 | unchanged |
| brand | 1869 | 1869 | 0 | 0 | unchanged |
| country | 135 | 135 | 0 | 0 | unchanged (only 135) |
| name | 4749 | 4749 | 0 | 0 | complete |

## Materially improved fields
- **cask_type**: 54 -> 681 (+627, +13.2 pts) — P139.
- **region**: 417 -> 947 real-nonempty (+530, +11.2 pts) — P142; plus P141 removed 713 inconsistent '' values.

## Fields with high-conf source available but NOT yet promoted
- **abv**: 707 candidates in knowledge.db promotion_queue (current 46.03%).
- **age**: 724 candidates in knowledge.db promotion_queue (current 34.32%).
These would lift coverage but require a separate authorized promotion task.

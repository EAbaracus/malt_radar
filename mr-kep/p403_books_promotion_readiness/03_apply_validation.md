# P404 — 03 Apply Validation (post-simulated-apply)

| Check | Result |
|---|---|
| No duplicate (whisky_id, source='book') | True |
| Exactly one book row per whisky | True |
| No orphan whisky (all ids valid) | True |
| No evidence loss | True |
| Idempotent rerun → zero additional changes | True |

All post-apply checks PASS. The simulated final state contains 64 book rows, 0 duplicates, and is reproducible with zero drift on rerun.

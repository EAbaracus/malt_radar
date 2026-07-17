# P141 — P139 Promotion Recheck (simulation only)

- doc_version: P141-1
- mode: READ-ONLY simulation. NO promotion executed.

## Method
Re-evaluated the unchanged P137B `promotion_export.csv` (region + cask_type rows) against
the now-normalized production.db. A row is "NULL-eligible" if its target column is now NULL
(and thus a future NULL_FILL promotion could fill it). Overwrite-risk = a row whose current
value is non-null AND differs from the proposed value (would require clobbering a real value).

## Results
| metric | value |
|---|---|
| export rows evaluated (region+cask_type) | 1233 |
| now NULL-eligible (can be filled by NULL_FILL) | 530 |
| still skipped (genuinely non-null real value) | 703 |
| **overwrite-risk rows** | **0** |

## Previously-skipped P139 region rows (the 530 gap)
| metric | value |
|---|---|
| P139 region rows originally skipped | 530 |
| now NULL (eligible for future NULL_FILL) | 530 |
| still non-null | 0 |

## Conclusion
All 530 previously-skipped region rows are now NULL → a future NULL_FILL promotion (same
P139 harness) would fill them, closing the 1,158 → 628 gap. **0 overwrite-risk rows** — no
real value can be clobbered. This recheck did NOT execute any promotion; it only recalculates
eligibility. A separate, authorized promotion task is required to apply the 530 fills.

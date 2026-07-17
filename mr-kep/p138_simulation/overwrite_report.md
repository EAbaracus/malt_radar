# P138 — Overwrite Report

- doc_version: P138-1
- date_utc: 2026-07-17
- mode: READ-ONLY simulation. production.db NOT modified.

## Result
| action | count |
|---|---|
| OVERWRITE_ALLOWED | 0 |
| CONFLICT | 0 |
| SKIP | 0 |
| **overwrite_count** | **0** |

## Interpretation
- overwrite_count = 0 means **no production value would be modified or overwritten**
  by this promotion. production.db is fully safe under this plan.
- The P135 conflict policy ("never overwrite stronger existing values; preserve
  provenance/citations/confidence") is satisfied with zero exceptions.
- Every one of the 1,233 candidates is either a NULL_FILL (1,158) or a NO_CHANGE
  (75) — both are non-destructive.

## Why no CONFLICT occurred
- A CONFLICT would require a non-NULL current production value that DIFFERS from the
  normalized proposed value, on a REPLACE/APPEND field.
- Inspection of live production.db shows: for all 1,233 candidates the current value
  is either NULL (→ NULL_FILL) or exactly equal to the normalized proposed value
  (→ NO_CHANGE). Thus CONFLICT = 0.

## Note on the 75 "conflict_report.csv" rows
- P137B's conflict_report.csv lists 75 region rows as `no_overwrite` with raw proposed
  value `Highland` (un-normalized SMWS string).
- In promotion_export.csv the SAME 75 whiskies carry the normalized proposed value
  `Highland / District`, which equals the existing production value → NO_CHANGE.
- Verified: 75 NO_CHANGE region IDs == 100% of conflict_report.csv IDs.
- Therefore, in the P138 simulation, those 75 are NO_CHANGE (no-op), NOT a live conflict.
  The discrepancy is a P137B artifact inconsistency (raw vs normalized proposed value),
  not a real overwrite risk. Flagged for transparency.

## Conclusion
overwrite_count = 0. No production metadata is at risk. READ-ONLY contract honored.

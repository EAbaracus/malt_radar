# P144A — Data Quality (Phase 4)

## ABV (707 candidates)
- numeric check: all parse as float.
- plausible (30-75%): **all 707 valid** (0 invalid).
- distinct proposed values: see classification.csv.

## Age (724 candidates)
- integer check: all parse as number.
- NAS excluded: no 'NAS' strings present.
- plausible (1-50 years): **3 INVALID** ->
  - whisky_id b4df6f56... proposed age=111.0 (>50, implausible) -> EXCLUDE
  - whisky_id 3b9fddcc... proposed age=63.0 (>50, implausible) -> EXCLUDE
  - whisky_id 96cf9554... proposed age=100.0 (>50, implausible) -> EXCLUDE

## Anomalies
- 3 age values exceed 50 years (111.0, 63.0, 100.0). These are data errors in the SMWS
  staging and must be EXCLUDED from any promotion.
- The 75 region 'conflicts' are normalization-format differences (raw 'Highlands' vs
  normalized 'Highlands / District'), not value errors.

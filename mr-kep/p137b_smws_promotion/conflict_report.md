# P137B — Conflict Report

- source: conflict_report.csv (75 rows)
- these are the rows where production.whiskies already had a non-null value for
  the proposed field, and P135 policy FORBIDS overwriting a stronger existing value.
- ALL are `region` (REPLACEABLE, fill-null-only). 0 for cask_type (APPEND never conflicts).

## Rule applied
```
if existing_value IS NOT NULL:
    KEEP existing          # no_overwrite
    log to conflict_report  # for human adjudication
else:
    SET proposed_value     # fill_null
```

## Sample conflicts (verbatim from conflict_report.csv)
| whisky_id | field | proposed (SMWS) | existing (production) | policy |
|---|---|---|---|---|
| 02a86d9a… | region | Highland | Highland / District | no_overwrite |
| 086f622f… | region | Highlands | "Highlands\n District" | no_overwrite |
| 09f3e5e3… | region | Highland | Highland District | no_overwrite |
| 0b9d77e4… | region | Islay | Islay District | no_overwrite |

## Why these are NOT auto-applied
- The existing values are the OLD production regions (often `X District` compound forms).
- SMWS proposal is the cleaner canonical region (e.g. `Highland`, `Islay`).
- P135: "Never overwrite stronger existing values." An already-populated field is
  considered stronger than an external fill. The 75 are deferred to human review
  (a future P138 task), where a maintainer can choose to normalize `X District`
  → `X` if desired.

## No conflict for cask_type
- cask_type is APPEND (union-join). Existing + proposed are merged uniquely, so
  there is never a destructive overwrite → 0 cask_type conflicts.

## Counts
- total conflicts logged: **75** (all region, all no_overwrite).
- citations preserved: each conflict row carries its `citation_id` for traceability.

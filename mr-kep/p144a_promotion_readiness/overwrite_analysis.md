# P144A — Overwrite Analysis (Phase 2 & 3)

Classification of every candidate vs live production.db (type-aware comparison; numeric fields
compared as floats to avoid false CONFLICT from REAL-vs-string coercion).

| class | count | meaning |
|---|---|---|
| READY_NULL_FILL | 3 | production NULL -> safe to fill |
| READY_EMPTY_FILL | 0 | production '' -> safe to fill |
| NO_CHANGE | 2581 | same value already present |
| CONFLICT | 80 | different non-null value exists |
| INVALID | 0 | empty/bad proposed value |
| UNRESOLVED | 0 | whisky_id not in production |

## Overwrite count (CONFLICT)
- **All fields: 80** conflicts.
- By field: {'region': 75, 'age': 4, 'abv': 1}
- The 75 region conflicts are ALREADY-PROMOTED rows (P139/P142) whose SMWS raw value
  ('Highlands') differs from the normalized production value ('Highlands / District'). These are
  OUT OF abv/age SCOPE and were already written; they are not new overwrites.
- **abv/age scope conflicts: 5** (4 age + 1 abv) — genuine value differences.

## STOP condition (spec: overwrite != 0 -> STOP)
- The spec's expected overwrite count was 0. Actual all-field overwrite = 80.
- For the **abv/age scope specifically**, overwrite = 5 (not 0).
- **This triggers the STOP condition for the stated P144 objective.**

## Conflicting UUIDs (abv/age scope, 5)
- Listed in classification.csv (classification=CONFLICT, field in abv/age).

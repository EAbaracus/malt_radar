# P137B — Field Delta

- source: promotion_export.csv (1.233 rows) + conflict_report.csv (75 rows)
- field-by-field change detail for the P138 gate transaction.

## cask_type (APPEND, 627 rows)
- action: APPEND (union-join with ';').
- existing production value preserved; proposed casks added uniquely.
- example: `003ad896…` → current `""` + proposed `refill` → `refill`.
- example: `00746183…` → current `""` + proposed `butt;refill` → `butt;refill`.
- 0 conflicts (null-fill or append-merge only).

## region (REPLACEABLE→APPLY fill-null, 606 rows)
- action: APPLY ONLY when production.region IS NULL.
- 75 rows had a non-null existing region → **skipped** (no_overwrite), logged to conflict_report.
- examples (all `no_overwrite`):
  - `02a86d9a…` proposed `Highland`, existing `Highland / District` → kept existing.
  - `086f622f…` proposed `Highlands`, existing `Highlands\n District` → kept existing.
  - `09f3e5e3…` proposed `Highland`, existing `Highland District` → kept existing.
  - `0b9d77e4…` proposed `Islay`, existing `Islay District` → kept existing.
- The 75 existing values are the OLD production regions (often `X District`);
  the SMWS proposal is the cleaner canonical region. Policy P135 forbids overwriting
  a stronger (already-present) value, so these wait for human adjudication.

## age / abv (REVIEW — NOT in this export)
- 724 + 707 = 1.431 rows exist in promotion_queue but are REVIEW-class.
- Excluded per P135 + "ignore review_queue". They require human sign-off
  before any production write. Documented for the P138 human-review workstream.

## Traceability (every row)
- `citation_id` → `citations` → `sources` (source_id canonical, D2).
- `confidence` 0.95 carried on every row.
- `dedupe_key` unique (0 collisions) → idempotent re-application.

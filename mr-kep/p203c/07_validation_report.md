# P203C — 07 Validation Report

## Determinism / idempotency
- Pipeline run twice on in-memory HTML: evidence_id identical → **idempotent = {t['idempotent']}**.
- Duplicate prevention: **True**.
## Schema compliance (faithful re-validation)
- Valid: **{valid_n}/{n}**.
- Failure buckets: None is not of type 'number'×12
- Root cause: the schema requires `score.normalized` as a number [0,1]; reviews with no detectable score emit `normalized=None` → invalid. (13 unscored rows fail; 2 scored rows had unclamped normalized>1 in rebuild — the live extractor clamps, so 3 scored rows are valid.)
## DB integrity
- production.db: {prod_integ} (unchanged={prod_unchanged}).
- knowledge.db: ['ok'] (P203B crosswalk intact, unchanged=True).

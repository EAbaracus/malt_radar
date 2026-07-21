# P143 — Existing Asset Potential (Phase 4)

Estimate max achievable completion WITHOUT downloading anything new, using only existing local assets.
Assets inspected: knowledge.db (promotion_queue 2664, review_queue 1431), P137B export, p119_6 staging CSVs.

| Field | Current | Max (apply existing high-conf pool) | Gap to max | Automation difficulty |
|---|---|---|---|---|
| abv | 46.03% (2186) | 60.92% (2893) | 707 | LOW (reuse P139 harness) |
| age | 34.32% (1630) | 49.57% (2354) | 724 | LOW (reuse P139 harness) |
| region | 19.94% (947) | 19.94% (already promoted all 606 SMWS) | 0 | N/A (exhausted SMWS source) |
| cask_type | 14.34% (681) | 14.34% (already promoted all 627 SMWS) | 0 | N/A (exhausted SMWS source) |
| tasting_notes/flavour | ABSENT (no column) | ABSENT | n/a | BLOCKED: schema lacks column |

## Knowledge DB pool (not yet promoted)
- promotion_queue high-conf pending (excluding already-promoted cask_type/region): abv 707, age 724 = 1,431 candidates.
- review_queue: 1431 rows need manual review (NOT auto-promotable; lower confidence / conflict).

## Staging assets (p119_6)
- canonical_vectors_staging.csv (792 rows) — flavour vectors; no flavour_vector column in production schema.
- staging_smws_tasting_notes.csv (803 rows) — tasting text; no tasting_notes/description column in schema.
  => These assets CANNOT lift current schema coverage; they require a schema extension (migration) which is out of P143 scope.

## Maximum achievable (no new download, no migration)
- Applying abv + age pool: abv 46%->61%, age 34%->49%. All other fields capped at current (no source).
- Without schema migration, text assets (tasting_notes/flavour) contribute 0 to coverage.

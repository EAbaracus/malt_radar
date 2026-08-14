# Import Priority Matrix — Sprint 05

> READ-ONLY planning output. Ranking for a FUTURE intake sprint (Sprint 05 itself does NOT ingest).

## Priority tiers

- **HIGH** — unique whisky entities + flavor/tasting data, or missing production coverage (ABV/age/distillery).
- **MEDIUM** — metadata enrichment (distillery/brand/region), no flavor/ABV.
- **LOW** — duplicate / catalog-only sources.

## Ranked sources

| Rank | Priority | Source | Rows | Reason | Entity fields |
|-----:|:--------|--------|-----:|--------|-------------|
| 1 | HIGH | `catalogue.csv` | 374 | whisky entities + ABV/age + distillery metadata (production coverage gap filler) | whisky_name, distillery, brand, region, age, rating, type |
| 2 | HIGH | `manual_curated_tasting_notes_url_extract_draft.csv` | 1 | unique whisky entities + flavor/tasting data present | whisky_name, age, flavor_tasting, rating, type |
| 3 | HIGH | `whiskybase_export_sample.csv` | 5 | whisky entities + ABV/age + distillery metadata (production coverage gap filler) | whisky_name, distillery, region, abv, age, rating, type |
| 4 | MEDIUM | `brands.csv` | 263 | metadata enrichment (distillery/brand/region), no flavor/ABV | whisky_name, distillery, brand, region, type |
| 5 | MEDIUM | `distilleries.csv` | 351 | whisky name metadata only | whisky_name, brand, region, type |
| 6 | MEDIUM | `htfw_world_whisky_brands.csv` | 276 | whisky name metadata only | whisky_name, brand, region, type |
| 7 | MEDIUM | `htfw_world_whisky_brands_enriched.csv` | 276 | whisky name metadata only | whisky_name, brand, region, type |

## Recommended intake order (future CSV ingestion sprint)

1. **HIGH** `whiskybase_export_sample.csv` — whisky + distillery + region + ABV + age. Expand to full export.
2. **HIGH** `manual_curated_tasting_notes_url_extract_draft.csv` — unique flavor/tasting (1 row; needs full set).
3. **MEDIUM** `htfw_world_whisky_brands_enriched.csv` — brand/distillery/region (enriched only).
4. **MEDIUM** `distilleries.csv` — distillery metadata.
5. **MEDIUM** `brands.csv` / `catalogue.csv` — brand/owner/rating catalog.

## Notes

- 665 net-new names await production.db seeding before knowledge.db enrichment.
- Future intake MUST reuse frozen source-scoped ID loader (FACT_{SOURCE_ID}_…, CIT_{SOURCE_ID}_…, BEGIN IMMEDIATE, NO INSERT OR IGNORE).
- STOP: Sprint 05 is analysis-only. No CSV ingestion performed.

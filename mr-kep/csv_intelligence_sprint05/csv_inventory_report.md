# CSV Inventory Report — Sprint 05 (Legacy CSV Intelligence Intake)

> **READ-ONLY ANALYSIS.** No knowledge.db / production.db mutations. No schema changes.

## Summary

- **Total CSV files scanned:** 548
- **Genuine enrichment sources:** 7
- **Derived pipeline artifacts (excluded as sources):** 541

## Genuine Sources (candidate enrichment datasets)

| # | Path | Rows | Cols | Encoding | Entity fields present |
|---|------|-----:|-----:|----------|------------------------|
| 1 | `data\books\yeni veriler\brands.csv` | 263 | 7 | utf-8-sig | whisky_name, distillery, brand, region, type |
| 2 | `data\books\yeni veriler\catalogue.csv` | 374 | 8 | utf-8-sig | whisky_name, distillery, brand, region, age, rating, type |
| 3 | `data\books\yeni veriler\distilleries.csv` | 351 | 10 | utf-8-sig | whisky_name, brand, region, type |
| 4 | `data\input\htfw_world_whisky_brands.csv` | 276 | 13 | utf-8-sig | whisky_name, brand, region, type |
| 5 | `data\input\htfw_world_whisky_brands_enriched.csv` | 276 | 17 | utf-8-sig | whisky_name, brand, region, type |
| 6 | `data\input\manual_curated_tasting_notes_url_extract_draft.csv` | 1 | 18 | utf-8-sig | whisky_name, age, flavor_tasting, rating, type |
| 7 | `data\input\whiskybase_export_sample.csv` | 5 | 11 | utf-8-sig | whisky_name, distillery, region, abv, age, rating, type |

## Derived Artifact Directories (NOT sources)

- `data/output/**` — P2–P61 bulk harvest / apply / audit CSVs
- `data/staging/**` — staging reviews / traceability holding
- `data/queue/`, `data/registries/`, `data/templates/` — merge queues, registries, templates
- `data/manual_sources/` — P2 manual review packs (not raw sources)

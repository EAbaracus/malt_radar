# Duplicate Analysis — Sprint 05

> READ-ONLY. Duplicates DETECTED only — nothing merged or removed.

## Per-source duplicate detection

| Source | Entity key | Total rows | Identical rows | Dup entity keys | Dup distillery/product combos |
|--------|-----------|-----------:|--------------:|---------------:|------------------------------:|
| `brands.csv` | name | 263 | 0 | 0 | 0 |
| `catalogue.csv` | name | 374 | 0 | 1 | 1 |
| `distilleries.csv` | name | 351 | 0 | 1 | 1 |
| `htfw_world_whisky_brands.csv` | name | 276 | 0 | 0 | 0 |
| `htfw_world_whisky_brands_enriched.csv` | name | 276 | 0 | 0 | 0 |
| `manual_curated_tasting_notes_url_extract_draft.csv` | whisky_name | 1 | 0 | 0 | 0 |
| `whiskybase_export_sample.csv` | name | 5 | 0 | 0 | 0 |

## Findings

- **`brands.csv`**: no internal duplicates detected.
- **`catalogue.csv`**: 0 identical rows, 1 duplicate entity keys, 1 duplicate combos.
- **`distilleries.csv`**: 0 identical rows, 1 duplicate entity keys, 1 duplicate combos.
- **`htfw_world_whisky_brands.csv`**: no internal duplicates detected.
- **`htfw_world_whisky_brands_enriched.csv`**: no internal duplicates detected.
- **`manual_curated_tasting_notes_url_extract_draft.csv`**: no internal duplicates detected.
- **`whiskybase_export_sample.csv`**: no internal duplicates detected.

## Cross-source duplication
- `yeni veriler/brands.csv` and `htfw_world_whisky_brands*.csv` overlap on brand/owner/distillery metadata.
- `htfw_world_whisky_brands.csv` vs `_enriched.csv` are the same base; ingest only the enriched variant.
- `distilleries.csv` and `htfw_world_whisky_brands.csv` share distillery rows.
## Probable batch duplicates
- The `htfw_*` enriched `match_status` flags already-matched rows — exclude those from a fresh intake.
- No de-duplication or merge was performed (per Sprint 05 constraints).
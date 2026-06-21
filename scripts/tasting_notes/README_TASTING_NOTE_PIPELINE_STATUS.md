# Tasting Note Pipeline Status
**Status:** Web scraping pipeline FROZEN
**Reason:** 12W HTTP 403/anti-bot blocks, 12U fallback/no-result issues, and ToS/legal risks.

## Active Recommended Paths
1. Manual curated CSV/file import
2. In-app user-generated tasting notes (UGC)

## Frozen Scripts
The automated web scraping and extraction scripts have been moved to `scripts/archive/12y_frozen_web_scraping_pipeline/` to prevent accidental execution and injection of mock/fallback data.
Frozen outputs will not be applied to production.

## DB Status
- `production.db` -> `tasting_notes` remains 25
- `production.db` -> `staging_web_tasting_notes` remains 0

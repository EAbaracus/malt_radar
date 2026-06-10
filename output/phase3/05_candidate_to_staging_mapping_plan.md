# Candidate to Staging Mapping Plan

This document defines how data from isolated candidate files will map to the new database staging tables.

## 1. Whisky Edition API Data
* **New Product Candidates** (`26_new_product_candidates_triage.csv`):
  * Mapped to -> `staging_new_products`
  * Action: Await manual approval. If approved, row is promoted to `whiskies` table.
* **Tasting Notes** (`24_tasting_notes_candidate_quality_audit.csv`):
  * Mapped to -> `staging_tasting_notes`
  * Action: Will point to `staging_new_products.staging_id`. Will be promoted to `tasting_notes` when the parent product is approved.

## 2. Malt List Data
* **Historical Menu Prices** (`06_reconciled_LOW_RISK_historical_menu_price_candidates.csv`):
  * Mapped to -> `staging_historical_menu_prices`
  * Action: Safe (LOW risk), but must go through staging. Since `whisky_id` is verified, they can be batch-approved easily without affecting `whiskies.current_price`.
* **Manual Review Prices** (`07_reconciled_manual_review_price_candidates.csv`):
  * Mapped to -> `staging_historical_menu_prices`
  * Action: Enters staging with `status = 'PENDING'` requiring human matching confirmation.

## 3. WhiskeyFYI Data
* **Regions** (`26_regions_knowledge_import_preview.csv`):
  * Mapped to -> `knowledge_regions`
  * Action: Safe reference data, can be inserted directly after staging review. Does not overwrite master entities.
* **Glossary** (`27_glossary_knowledge_import_preview.csv`):
  * Mapped to -> `knowledge_glossary_terms`
* **Guides** (`28_guides_reference_import_preview.csv`):
  * Mapped to -> `knowledge_guides`

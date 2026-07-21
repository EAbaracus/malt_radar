# Pipeline & Ingestion Blockers

This document catalogs the unresolved blockers preventing a new Malt Radar production release or further dataset promotion.

## 1. Database & Schema Blockers

### CRITICAL: Empty `knowledge.db` Mirror
- **Path:** `output/import/knowledge.db`
- **Details:** The mirror database is empty (0 bytes, 0 tables). Without tables like `canonical_vectors` and `citations`, direct promotion of staging assets into the knowledge layer is impossible.
- **Remediation:** Bootstrap this database with the `mr-kep/p102_bootstrap/schema.sql` schema.

### CRITICAL: ID-Space Mismatch
- **Details:** Production database (`production.db`) uses UUIDs (e.g. `21e7ffc0-...`), while the bootstrap `knowledge.db` uses legacy `W000001`-style W-ids. 
- **Impact:** Grains and single malts cannot be linked across databases without a crosswalk, breaking target-consensus joins.
- **Remediation:** Create a `uuid_to_wid_crosswalk` mapping table.

### HIGH: Citation Schema Gaps
- **Details:** The bootstrap schema for `citations` lacks columns for `source_key` and `source_citation_id`, and `canonical_vectors` is missing `smws_code` and `rich`.
- **Remediation:** Apply schema migrations to additive columns in `knowledge.db` bootstrap schema before promoting.

## 2. Review & Quality Backlogs

### HIGH: Unresolved Entity Backlog (Resolver Output)
- **Details:** 30,529 new-distillery/product leads from the 44-book extraction and 77 ambiguous SMWS codes sit in review queues.
- **Impact:** Gated from promotion; auto-promotion risks dirtying the production database.
- **Remediation:** Establish a partitioning script to auto-reject low-confidence candidates (e.g. confidence < 0.70) and present only high-value candidates to human reviews.

### MEDIUM: NULL Flavor Profiles
- **Details:** 653 of the 726 SMWS merge rows (89.9%) have no `flavour_profile` text in the staging files, which soft-blocks vector merge logic since there is no textual flavor ground truth to align against.

## 3. Pipeline Incompatibilities

### MEDIUM: Registry Staleness
- **Details:** `data/registries/book_registry.json` contains 13 out of 14 placeholder entries. Ingesting new books will trigger validation failures unless this registry is updated with actual metadata.

### LOW: GIS Assets Unprocessed
- **Details:** Geolocation shapefiles (`ScottishDistilleries.{dbf,shp,shx}`) are unparsed due to the absence of a shapefile parser.

# Promotion Priority Plan (V2)

Based on the quantitative gaps in `production.db`, this plan outlines the optimal order of dataset promotion and integration to maximize coverage gains while minimizing risk.

## Phase 1 — Database Bootstrapping & Prerequisite Schema (P131)
- **Target:** `output/import/knowledge.db`
- **Objective:** Deploy tables (`canonical_vectors`, `citations`, `official_source_references`) and columns (`smws_code`, `rich`, `source_key`, `source_citation_id`) to the mirror database. Create the `uuid_to_wid_crosswalk` mapping.
- **Why:** Immediate prerequisite. Without this, no staging vector can join the production UUID space.

## Phase 2 — Distillery Attribute Ingestion (Malt Whisky Yearbook 2019 - B1)
- **Target:** `distilleries`
- **Objective:** Promote the B1 yearbook facts (founded years, ownership, websites, coordinates) into `production.db`.
- **Why:** Closes the 99%-100% missing data gap on distillery attributes, which is the largest database deficiency.

## Phase 3 — Cask & Tasting Ingestion (SMWS USA Staging)
- **Target:** `whiskies`, `tasting_notes`, `flavor_evidence`
- **Objective:** Promote 726 MERGE vectors and 13,238 tasting note rows.
- **Why:** Addresses the 98.86% missing `cask_type` gap and significantly reduces the 63.55% missing `tasting_notes` gap.

## Phase 4 — Flavor Vector Calibration (B5 Flavor Methodology)
- **Target:** `flavor_profiles`
- **Objective:** Ingest Whisky Classified / Flavour of Whisky (David Wishart) datasets.
- **Why:** Establishes the 7-axis flavor profile model, enabling accurate consensus normalization for all subsequent book ingestion runs.

## Phase 5 — Regional & Country Enrichment (World Atlas - B2 / Jackson - B3)
- **Target:** `whiskies.region`, `whiskies.country`
- **Objective:** Promote Atlas/Jackson data to populate missing geographical attributes.
- **Why:** Reduces the 91.24% missing `region` and 97.16% missing `country` gaps.

## Phase 6 — Expression & Brand Expansion (B4b / Advocate / remaining reviews)
- **Target:** `whiskies`, `brands`
- **Objective:** Run resolver queues to approve/reject new expressions and brands.
- **Why:** Safely adds new entities without dirtying the production database.

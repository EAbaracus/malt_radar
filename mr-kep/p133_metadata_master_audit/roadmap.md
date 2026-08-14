# Roadmap — Metadata Enrichment Strategy

## Phase 1 — Database Bootstrapping (Immediate)
- **Action:** Execute DDL on `knowledge.db` to deploy missing vector and citation structures. Create the mapping crosswalk.

## Phase 2 — SMWS Dataset Promotion (High ROI)
- **Action:** Promote the 788 matched and 14 net-new SMWS expressions directly from the staging files into `production.db`.
- **Reason:** Requires zero entity-resolution effort (confirmed net-new by P132b) and closes significant tasting notes and cask type gaps.

## Phase 3 — Distillery Ingestion (Yearbook 2019)
- **Action:** Import Ingvar Ronde's distillery dataset to backfill owner, founded year, and regional attributes.

## Phase 4 — Core Range Parsing (World Atlas)
- **Action:** Deploy the segment text parser over Dave Broom's World Atlas to extract missing ABV and Age statements for the 1,931 orphan whiskies.

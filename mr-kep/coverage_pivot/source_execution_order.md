# Source Execution Order — Strategic Coverage Pivot

**Goal:** Maximize total whisky coverage (whisky_ids + distilleries + brands) before any further corroboration books.
**Read-only analysis.** No ingestion performed. Order is a recommendation for future sprints.

---

## Phase 1 — Tier A: Coverage gain (DO FIRST)

These directly enlarge the entity universe. All are local, already-staged CSVs → low processing cost, high confidence.

| Step | Source | Action | Est. new entities | Why this order |
|:-:|---|---|:-:|---|
| **1** | **S2 Distilleries** (`staging_distilleries.csv`, 351 rows) | Seed new distilleries (owner/region/founded/status) | **~215** | Distilleries are the parent entities; seeding them first lets expressions/brands resolve against them (higher match rate downstream) |
| **2** | **S1 Catalogue/expressions** (`staging_catalogue.csv`, 374 rows) | Seed new expressions linked to distillery/brand | **~313** | After distilleries exist, expression match rate rises; expressions are the primary "whisky_id" coverage unit |
| **3** | **S3 Brands** (`staging_brands.csv`, 263 rows) | Seed new brands (owner/distillery/country) | **~116** | Completes the producer graph; lowest marginal new but cheap |
| **4** | **S10 B8 EPUB** (`The Complete Whiskey Course`, Robin Robinson) | Enrichment sprint (reuse S08 loader) | **~13** | Only book with net-new; cheap; do it here so the book corpus is fully exhausted for coverage before we stop book work |

**Phase 1 subtotal new entities: ~657** (215 + 313 + 116 + 13).

> Note on "whisky_id" vs "entity": production.db `whiskies` = 3,557 expressions. S1's 313 are expression-level; many may resolve to existing distilleries as variants. Conservative realization (50%) still yields **~160–320 net-new whiskies** — far beyond all books combined.

---

## Phase 2 — Tier B: Evidence quality (DO SECOND)

Now that the universe is larger, enrich it. These add citations/flavor, not new ids.

| Step | Source | Action | Est. citations | Value |
|:-:|---|---|:-:|---|
| **5** | **S5 SMWS (803 cask notes)** | Load cask-scoped tasting → `canonical_vectors` flagged `single_cask=1` | ~803+ | Richest first-party flavor signal; raises 7-axis consensus quality on known expressions |
| **6** | **S4 HTFW brands** (276) | Cross-validate identity fields (region/owner/founded) | ~low | Strengthens Tier B identity consensus |
| **7** | **S7 Retailer ALKO** (50-row preview; needs full export) | Verify specs (abv/age/cask); price INTERNAL-only | ~low | Official-bottling verification per Field Authority Matrix |

---

## Phase 3 — Tier C: Corroboration only (DEFER)

Do last, if at all. These add ≈0 new coverage — the "Dave Broom Manual" pattern to avoid until coverage is maximized.

| Step | Source | Action | Note |
|:-:|---|---|---|
| **8** | **S9 Remaining books (B5/B4/B7)** | Enrichment (if approved) | ~0 new; pure corroboration. B5 Wishart valuable for 7-axis *methodology* quality, not count. |
| **9** | **S6 Whiskybase** | Requires full member export (only 5-row sample present) | Revisit when export available |
| **10** | **S8 Low-risk web** | Scraping workstream (not local) | Separate from offline pivot |

---

## Recommended next sprint

**Sprint 10 → Step 1 (S2 Distilleries)** is the highest-ROI first move: ~215 new distilleries, already staged, zero new extraction code (CSV load), and it unlocks higher match rates for Steps 2–3.

Stop processing corroboration books (S9 class) until Phase 1 + Phase 2 are complete.

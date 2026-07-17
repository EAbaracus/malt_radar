# Recommended Sprint Order — P103 Corpus Audit
_Generated 2026-07-15 18:01 UTC_

## Sprint 08 — Whisky Advocate / Magazine group (W3)
**Why:** Highest combined corroboration + steady net-new coverage; independent reviews cross-check existing facts; magazines are small/medium PDFs (low processing cost). 19 issues, several with 50–70 measured net-new whisky_ids (e.g. Fall 2025 = 58, Spring 2026 = 72). Best ROI for coverage gain.

## Sprint 09 — Remaining expert books (B8, B4, B5, B7)
**Why:** B8 Robin Robinson is already registered (pre-flight done, SHA256 known) → lowest friction. B4 Jim Murray (complete book), B5 Wishart/Whisky Classified, B7 MacLean/Offringa/etc fill descriptive and attribute gaps. Solid net-new coverage at low processing cost (small EPUBs/PDFs).

## Sprint 10 — SMWS USA Tasting Notes Archive (B6, 803 PDFs)
**Why:** HIGHEST corroboration value (803 independent single-cask ratings cross-check existing tasting facts), but measured net-new COVERAGE is minimal — the 41-file sample yielded only 2 distinct net-new whisky_id(s). SMWS overlaps heavily with already-covered bottles, so its ROI is driven by evidence-quality/corroboration, NOT coverage. Process as a corroboration pass after coverage sources are in. One-time pipeline cost is high but amortized over 803 files; batch-extract then batch-resolve. Recommend an intra-group SHA256 de-dup first (extreme internal overlap expected).

## Later / auxiliary
- CSVs in `data/input` & `data/manual_sources` (brands/catalogue/distilleries, whiskybase sample) are auxiliary cross-reference sources, not primary enrichment; fold in as validation, not separate sprints.
- `uploaded_whisky_tasting_notes.txt` is user-generated notes → manual-source tier, ing, not auto-ingest.

## Per-candidate ranked backing (top 12)

- **Маклин, Чарльз - Whiskypedia_ An Introduction to S** (B7) — ROI 8.15 (net-new 63, quality 3, corrob 3, cost 1)
- **Charles, MacLean _ John, MacPherson - Whiskypedia_** (B7) — ROI 7.2 (net-new 44, quality 3, corrob 3, cost 1)
- **The Complete Whiskey Course -- Robin Robinson --.e** (B8) — ROI 5.65 (net-new 13, quality 3, corrob 3, cost 1)
- **_OceanofPDF.com_Whisky_Advocate_-_Spring_2026_-_Wh** (W3) — ROI 5.6 (net-new 72, quality 2, corrob 4, cost 4)
- **A Field Guide to Whisky [eBook - Biblioboard]_ An ** (B7) — ROI 5.2 (net-new 4, quality 3, corrob 3, cost 1)
- **Japanese whisky _ the ultimate guide to the world'** (B7) — ROI 5.05 (net-new 1, quality 3, corrob 3, cost 1)
- **Whisky{Bruning, Ted}(2015, Bloomsbury Publishing){** (B7) — ROI 5.05 (net-new 1, quality 3, corrob 3, cost 1)
- **Dave Broom - Whisky_ The Manual (2014, Mitchell Be** (B7) — ROI 5.0 (net-new 0, quality 3, corrob 3, cost 1)
- **Lerner, Daniel - Single Malt and Scotch Whisky_ a ** (B7) — ROI 5.0 (net-new 0, quality 3, corrob 3, cost 1)
- **The Famous Grouse whisky companion _ heritage, his** (B7) — ROI 5.0 (net-new 0, quality 3, corrob 3, cost 1)
- **The flavour of whisky -- David Wishart(Fellow of t** (B5) — ROI 5.0 (net-new 0, quality 3, corrob 4, cost 2)
- **Whisky classified ; choosing single malts by flavo** (B5) — ROI 5.0 (net-new 0, quality 3, corrob 4, cost 2)
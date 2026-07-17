# P122 Phase 4 — Book Overlap Analysis

Overlap estimated from title-keyed grouping + known edition/translation relationships.

- **VERY HIGH** — Malt Whisky Yearbook 2019 vs annas-arch duplicate: Same SHA256 (056ab6524…) — byte-identical duplicate file, two filenames.
- **VERY HIGH** — Whisky Advocate Wol 32 No04 Winter 2023 (TruePDF vs OceanofPDF): Same SHA256 — identical issue from two sources.
- **HIGH** — Whiskypedia EN (Skyhorse) vs RU (Birlinn): Translation pair of same MacLean compendium — keep primary, dedupe.
- **MEDIUM** — Whisky Bible (B4) vs Complete Book of Whiskey (B4b): Both Jim Murray; Bible=per-expression scores, Complete Book=global distillery+encyclopedic — complementary, not duplicate.
- **MEDIUM** — World Atlas of Whisky (B2) vs World Guide to Whisky (B3): Both regional/distillery references; Atlas=visual/maps, Jackson=historical — complementary.
- **MEDIUM** — Whisky Classified (B5) vs Flavour of Whisky (B5): Both Wishart flavor-science; Classified=axis method, Flavour=statistics/chemistry — complementary.
- **MEDIUM** — Scotch Whisky Annuals (multiple) vs Malt Whisky Yearbook (B1): Overlapping annual stats/industry; yearbook is the structured directory.
- **LOW** — Whisky Opus vs World Atlas of Whisky: Both world-whisky visual references but different scope/photography.

## Books covering identical topics (reduce redundancy)
- Multiple Whisky Advocate issues (consumer reviews) — dedupe by issue.
- Multiple Scotch Whisky annuals — consolidate to B1 yearbook as canonical.
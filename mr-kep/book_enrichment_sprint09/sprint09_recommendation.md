# Sprint 09 — Highest ROI Source Recommendation

**Objective:** Determine the remaining source with the highest REAL expected value; recommend ONE for Sprint 09.
**Constraint recap:** Maximize (1) new whisky coverage, (2) evidence quality, (3) long-term consensus value. Avoid another "Dave Broom Manual" source (high corroboration, ~0 new coverage) unless no better alternative remains. Sources adding <20 new whisky_ids must be explicitly justified.
**Status:** Analysis only. **No source was processed.** No DB writes. Stop gate reached.

---

## Recommendation

> **Process B8 — Robin Robinson, *The Complete Whiskey Course* (EPUB) as source `RC_COURSE` in Sprint 09.**

It is the **only remaining book source that adds any net-new whisky coverage** (~13 new whisky_ids, verified by live probe) and it is the **lowest-complexity** remaining option (EPUB; the S08 `enrich_whisky_manual.py` loader is directly reusable — only the filename changes).

**But this recommendation carries a hard caveat the user must accept:** B8 is **T3_community (corroborate-only, cannot sole-certify)** per the acquisition plan (§B8, P95 books-tier audit C1/D1). Its net-new +13 expressions enter as *corroborated*, not certifying. And it otherwise behaves like the Dave Broom Manual pattern (corroboration-heavy, ~0 coverage beyond those 13). The full ranked rationale is in `remaining_roi_ranking.md`.

---

## Why not the alternatives

| Source | Why not chosen |
|--------|----------------|
| **B5 Wishart (Whisky classified)** | ~0 new whisky_ids. Highest *methodological* authority (7-axis basis) → raises consensus **quality**, not coverage. Strong secondary candidate if the goal shifts to axis-quality. Its companion "Flavour of Whisky" PDF in corpus is only 7 pages (preview) — incomplete. |
| **B4 Murray (Complete Book of Whiskey)** | ~0 new whisky_ids (0 of 96 resolved in probe). Pure corroboration; the textbook "Dave Broom Manual pattern" the brief says to avoid. |
| **B7 Supplementary (Opus / contemporary guide / etc.)** | ~0–5 new; matrix gate = CONDITIONAL (overlap audit first). High overlap/licensing risk vs already-processed T1 references. Low marginal ROI. |
| **B6 SMWS Archive (803)** | Different value class (cask-scoped, flag `single_cask=1`); Very High complexity; does not add canonical whisky_ids. Separate workstream, not a coverage play. |
| **W1–W5 (web)** | Not local files; require scraping/exports. Out of scope for local deterministic sprint. |

---

## Addressing the "<20 new whisky_ids" rule

B8 adds **~13 new whisky_ids** — below the 20 threshold. Per the brief, this must be explicitly explained. Two reasons it is still the correct pick:

1. **It is the ONLY remaining source with any net-new coverage.** Every other candidate (B5, B4, B7) is in the <20 bucket too — at **~0**. Choosing any of them satisfies the "avoid Dave Broom pattern" rule only by also sacrificing the single real coverage gain available. Among a field where the best achievable new-coverage is +13, +13 is the maximum.
2. **The corpus is saturated for the 3,557-expression universe.** Post-S08 coverage is 1,737/3,557 (48.83%). The remaining ~1,820 uncovered expressions are overwhelmingly *not present in any book in `data/books/`* — they are niche/modern releases that only web/retailer sources (W4) or member exports (W5) would surface. No remaining book can move the dial past +13.

**Therefore:** if the user's priority is strictly "maximize new whisky_ids," the honest answer is **stop book ingestion** and move to web/retailer acquisition (W1/W4/W5). If the priority is "extract the last feasible net-new from the book corpus with minimal effort," **B8 is the pick** — and it is recommended here on that basis, with the T3 caveat.

---

## Expected Sprint 09 outcomes (if B8 approved)

| Metric | Estimate |
|--------|---------|
| New whisky_ids | **+13** (real net-new, verified) |
| New citations | ~260 |
| New evidence_nodes / extracted_facts | ~260 |
| New consensus_nodes / canonical_vectors | ~249 (236 corroborations + 13 new) |
| Coverage after S09 | 1,750 / 3,557 ≈ **49.2%** |
| Processing complexity | Low (EPUB; reuse S08 loader) |
| Risk | Low (local, deterministic, no schema change) |
| Authority posture | T3 corroborate-only for the +13 net-new |

---

## Decision needed from user

- **Option A (recommended here):** Run Sprint 09 on **B8 Robin Robinson** (`RC_COURSE`) for the +13 net-new + corroboration. T3-caveat acknowledged.
- **Option B:** Skip book ingestion; pivot Sprint 09 to **web/retailer acquisition (W1/W4)** or **Whiskybase export (W5)** for materially higher new-coverage (requires scraping/export tooling, not local-file).
- **Option C:** Process **B5 Wishart** instead, prioritizing **7-axis consensus quality** over coverage (accepts ~0 new ids).

No action taken. Awaiting direction.

---

*Appendix — reproducibility: all estimates derived from a live, read-only extraction probe of each remaining physical source against the post-S08 covered set (1,737 whisky_ids). Source: `mr-kep/book_enrichment_sprint09/remaining_roi_ranking.md`. The four named audit reports cited in the brief were not present in the repo and were not fabricated; this analysis uses the real substitute artifacts listed there.*

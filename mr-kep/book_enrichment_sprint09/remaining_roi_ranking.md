# Remaining Sources — ROI Ranking (Sprint 09 Analysis)

**Prepared for:** Sprint 09 — Highest ROI Source Selection
**Baseline:** Post-S08 knowledge.db (24 books, 13,133 citations, 3,077 consensus nodes, **1,737 distinct whisky_ids covered = 48.83% of 3,557 universe**)
**Method:** Deterministic, evidence-grounded. Live extraction probe (`extract_entities` from frozen S01 pipeline) run against each remaining physical source with `production.db` lexicon, comparing resolved `whisky_id`s against the **post-S08 covered set**. No DB writes.

---

## ⚠️ Transparency note on source audit reports

The four audit reports named in the Sprint 09 brief —
`remaining_sources_inventory.md`, `enrichment_priority_matrix.md`, `roi_quantification.md`, `coverage_projection.md` —
**do not exist in the repository** (verified by `find . -iname` across the whole tree). Per the project's anti-fabrication rule (AGENTS.md Escalation Rule + standing memory), they were **not invented**.

This ranking is instead built from **real, available artifacts**:
- `mr-kep/source_inventory/source_priority.md` (tier + authority rules)
- `mr-kep/source_inventory/coverage_matrix.md`, `field_authority_matrix.md`
- `data/books/acquisition_plan/source_priority_matrix.md`, `book_ingestion_plan.md`, `GO_NO_GO_recommendation.md`
- Live `knowledge.db` state (post-S08)
- A **live extraction probe** of each remaining book (80–120 capped pages) measuring resolution rate + genuinely-NEW whisky_ids

Estimates marked **(est.)** are extrapolations from the capped sample (see "How estimates were derived").

---

## Key finding (the decisive signal)

**The book corpus is effectively SATURATED for the 3,557-expression production universe.**
A live probe shows that **every remaining book source resolves almost entirely to expressions already covered by S01–S08** — new-whisky_ids added is ≈0 for B5, B4, B7, and only **~13** for B8.

| Source | Sample resolved | NEW (capped) | NEW (extrapolated, est.) | Verdict on coverage |
|--------|:-:|:-:|:-:|---|
| B5 Wishart — Whisky classified | 58 | 0 | ~0 | Saturated |
| B4 Murray — Complete Book of Whiskey | 96 | 0 | ~0 | Saturated |
| B7 Whiskey Opus | 102 | 2 | ~5 | Saturated |
| B7 Malt whisky contemporary guide | 69 | 0 | ~0 | Saturated |
| **B8 Robin Robinson — Complete Whiskey Course** | 236 | 13 | **~13–14** | Only net-new source |

This directly answers the user's constraint: *"Avoid selecting another source expected to behave like Dave Broom Manual (high corroboration, almost zero new coverage) unless no better alternatives remain."* **B5, B4, B7 all behave exactly like Dave Broom Manual** (high corroboration, ~0 new coverage). **B8 also behaves like that pattern** (corroboration-heavy) but is the *only* one carrying any net-new (+13).

---

## Ranked shortlist — all remaining sources

Ranked by **maximizing (1) new whisky coverage, (2) evidence quality, (3) long-term consensus value**, per the brief.

| Rank | Source | Est. new whisky_ids | Corrob. gain | Est. new citations | Proc. complexity | Confidence | Authority tier | ROI |
|:-:|---|:-:|:-:|:-:|:-:|:-:|---|:-:|
| **1** | **B8 Robin Robinson — Complete Whiskey Course (EPUB)** | **~13** | Med | ~260 | Low (EPUB, reuse S08 loader) | High | T3_community (corroborate-only) | **Best net-new** |
| 2 | B5 Wishart — Whisky classified / Flavour of Whisky | ~0 | High (axis authority) | ~120 | Med (PDF) | High | T1 (methodological) | Quality, not coverage |
| 3 | B4 Murray — Complete Book of Whiskey (2nd vol) | ~0 | High | ~186 | Med (PDF) | High | T1 (reference) | Corroboration only |
| 4 | B7 Whiskey Opus | ~5 | Med | ~257 | Med (PDF) | Med | T3 (mixed) | Low net-new, overlap risk |
| 5 | B7 Malt whisky: a contemporary guide | ~0 | Med | ~115 | Med (PDF) | Med | T3 (mixed) | Overlap risk |
| 6 | B7 Whisky Tasting Guide (G. Moore) | ~0 | Low | n/a | Low | Low | T3 | Overlap; 83pg sample |
| 7 | B7 Ultimate Book of Whiskey | ~0 | Low | n/a | Med | Low | T3 | Overlap |
| 8 | B6 SMWS USA Archive (803 PDFs) | cask-scoped only | Med (cask) | Very high (~thousands) | **Very High** (803 files) | Med | T2 (cask-specific) | Different table; flag single_cask |
| — | W1–W5 (web) | unknown | varies | unknown | High (scraping/exports) | Low | mixed | Not local-file; needs scraping/export |

### Per-source detail

**1. B8 Robin Robinson — The Complete Whiskey Course (EPUB, 23.9 MB, 22 docs)**
- Est. new whisky_ids: **~13** (real net-new: Tincup, Willett Pot Still Reserve, Westland Sherry Wood, Teeling Single Grain, Kavalan Concertmaster, Dalmore King Alexander III, etc. — mostly American/world whiskey not yet in the Scotch-heavy corpus).
- Corroboration gain: Medium — high resolution rate (60.7%) fills sensory consensus on ~236 already-known expressions.
- Est. new citations: ~260.
- Proc. complexity: **Low** — EPUB, reuses the proven S08 `enrich_whisky_manual.py` loader (swap PDF→EPUB already done).
- Confidence: High (probe reproducible).
- Authority tier: **T3_community** — *corroborate-only, cannot sole-certify* (per acquisition plan §B8). So its net-new +13 would enter as corroborated, not certifying.
- Note: matches the "Dave Broom Manual pattern" (corroboration-heavy) but is the **only** remaining source with any net-new coverage, so it is the least-bad option on objective #1.

**2. B5 David Wishart — Whisky classified (248 pg) + Flavour of Whisky (7 pg sample only)**
- Est. new whisky_ids: ~0.
- Corroboration gain: **High — methodological**. Wishart is the *basis of the 7-axis flavor system*; his axis definitions are the canonical reference for canonical-vector normalization. This raises **long-term consensus quality**, not count.
- ⚠️ Caveat: the corpus copy of "The flavour of whisky" is only **7 pages** (likely a preview/sample, not the full book) — its axis-definition content may be incomplete. "Whisky classified" (248 pg) is the substantive volume.
- Est. new citations: ~120.
- Proc. complexity: Med (PDF). Confidence: High.
- Authority tier: **T1 (methodological)**. Highest authority for flavor-axis semantics.

**3. B4 Jim Murray — Complete Book of Whiskey (232 pg, 2nd volume)**
- Different book from S07's "Whisky Bible 2020 (Rest of the World)". Same author → flavor-signal methodology.
- Est. new whisky_ids: ~0 (probe: 0 new of 96 resolved). Corroboration gain: High. Est. citations ~186.
- Authority tier: T1 (reference). This is the purest "Dave Broom Manual pattern" — high corroboration, zero new coverage.

**4–7. B7 Supplementary (Whiskey Opus, contemporary guide, Tasting Guide, Ultimate Book of Whiskey)**
- Matrix gate: **CONDITIONAL** (overlap audit first; net-new only). Probe confirms ~0 net-new; resolution rates 37–43%.
- Whiskey Opus is the least-overlapping (≈5 new est.). Others ≈0. Overlap/licensing risk high.
- Authority tier: T3 (mixed). Low marginal ROI vs already-processed T1 references.

**8. B6 SMWS USA Archive (803 PDFs)**
- Genuinely large (803 single-cask notes) but **cask-scoped** (per matrix B6: flag `single_cask=1`, must NOT overwrite core expression profiles). Adds cask-level tasting, not new canonical whisky_ids.
- Proc. complexity: **Very High** — 803 files, batch parsing, separate staging lane.
- Authority: T2 (first-party SMWS, cask-specific). Different value class; not a substitute for coverage.

**Web W1–W5**
- Not present as local files. Require polite scraping / member exports (W3/W5 Cloudflare-blocked → manual path). Out of scope for a local deterministic sprint; excluded from ranking.

---

## How estimates were derived (reproducibility)

- Loaded frozen `extract_entities` + `production.db` lexicon (read-only).
- Extracted 80–120 capped pages per book (EPUB: all 20–22 docs for B8).
- Resolved entities → `whisky_id`; counted those NOT in post-S08 covered set (1,737 ids).
- New-whisky extrapolation = capped-new × (full_pages / capped_pages). B8 scaled 13→14 (near-full doc). Others scaled ~0.
- Citation estimates = resolved entities × (1 citation/entity, the S01–S08 pattern).
- Authority tiers & complexity from `source_priority.md` / `source_priority_matrix.md` / `book_ingestion_plan.md`.

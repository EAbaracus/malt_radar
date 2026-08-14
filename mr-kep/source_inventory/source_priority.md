# Source Priority — MR-KEP P62 Knowledge Source Inventory

> Deterministic, evidence-first classification of all MR-KEP candidate sources.
> No scraping, no downloads — assessment + tiering only. Assessments below are
> **reasoned judgments**, not measured metrics; where a value is an estimate it
> is explicitly labeled. No fabrication: absent data is marked `Kısmi`/`-`, never
> invented.

## Tier summary (priority order)

| Tier | Role | Sources |
|------|------|---------|
| **Tier 1 — Primary Authority** | Certifies identity + official specs + canonical reference | Official Distillery Websites, Scotch Whisky Association, World Atlas of Whisky, Michael Jackson Complete Guide, Dave Broom sources |
| **Tier 2 — Trusted Secondary** | Sensory, specs cross-validation, awards, structured DB | WhiskyFun, Whisky Advocate, Whiskybase, Master of Malt, The Whisky Exchange, Distiller magazines |
| **Tier 3 — Verification Only** | Verify specs / snapshot original sources | Whisky Auctioneer, Wayback Machine |
| **Tier 4 — Enrichment Only** | Non-certifying supporting context (none qualified yet) | — (reserved; e.g. community forums if ever added) |

## Priority rules (deterministic)

1. **Tier 1 wins** on `identity`, `official_bottling`, `regulatory` fields.
2. **Tier 2 wins** on `sensory_evaluation`, `scored_assessment`, structured specs (when ≥2 independent agree → consensus).
3. **Tier 3** is never a certifier; it only confirms/anchors T1/T2 claims.
4. **Tier 4** (future) supplies supporting evidence only; cannot be sole source.
5. Unknown/new source ⇒ fail-safe to **Tier 3 verification** (never overrides known tiers).

## Recommended usage per source

- **primary**: official_distillery, scotch_whisky_association, world_atlas_whisky, michael_jackson_guide, dave_broom
- **secondary**: whiskyfun, whisky_advocate, whiskybase, master_of_malt, the_whisky_exchange, distiller_mags
- **verification**: whisky_auctioneer, wayback_machine

## Notes on field trust

- `flavor_profile` / `tasting_notes` / `score`: T2 experts (WhiskyFun, Whisky Advocate) + T1 reference authors (Broom, Jackson) agree on the **7-axis canonical taxonomy** (smoky, peaty, fruity, sweet, spicy, maritime, sherry). Non-canonical legacy tags are rejected.
- `abv`: when sourced from text carrying `%`, normalize via **strip `%` then CAST REAL** (P53/P54 fix) — never `abv/100`.
- `price` (Master of Malt, TWE, Auctioneer): collected as verification signal only; **must never be exposed in UI/API** (Malt Radar product rule).
- `image`: T1 producer sites + T2 retailers carry bottle images; copyright-restricted, reference by URL only, never redistribute.

See `knowledge_sources.csv` for the full quantitative table and `coverage_matrix.md`
/ `field_authority_matrix.md` for the cross-cuts.

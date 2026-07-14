# P95-C — Canonical Flavor Conversion

- **Mode:** IMPLEMENTATION, but **staging-artifact-only**. `production.db` read via `mode=ro`. **Zero writes** to production.db / staging.db.
- **Date:** 2026-07-14 · **DB:** `output/import/production.db` (read-only)
- **Canonical axes (frozen, decisions.md #2):** smoky, peaty, fruity, sweet, spicy, maritime, sherry

## Scope
Convert eligible **T2 / core** flavor data into canonical 7-axis vectors. **Exclude** all book-derived, NotebookLM-derived, ML-derived, and community/T3 sources. Per user directive, book-tier data is ignored until D4 (16/20→7 reducer) is implemented.

## Input datasets
- `flavor_profiles` (production, read-only) — 2,676 rows total.
- `tasting_notes` — not required for vector conversion (flavor_profiles already carries the canonical vectors); noted for future corroboration.
- **Excluded:** `staging_book_flavor_profiles` (2,577), `staging_notebooklm_flavor_profiles` (17), all T3 sources.

## Eligibility
Eligible tier = `T2_core` + `T2` (Whisky Advocate, whiskeymapper, tasting_note_rule_based, production_data.csv, scotchgit, whiskyfun, whiskynotes, structured_whisky_source_01).
Excluded tiers (count, **not** converted): {'T3_notebooklm': 2, 'T3_other': 5, 'T3_upload': 153, 'T3_ml': 326, 'T3_book': 192}.
**Eligible rows = 1998.** Excluded = 678.

## Mapping methodology (deterministic, rule-based, no LLM)
1. **axis7** (already canonical, keys ⊆ 7 axes): pass-through; clamp values to 0–100; missing axes filled with 0.
2. **term_bag** (free-text descriptor dicts, e.g. `{sweet:4, oak:2, sherry:4, ...}`): a curated descriptor→axis lexicon (`LEX`) maps each descriptor to one of 7 axes. Per-row intensity = `round(100 * weight / row_max_weight)` (peak-normalized, 0–100). **Lossy** (P95-B term-bag rule): new canonical vectors only, never overwrite.
3. **PCA** (`component_*`): **REJECTED** — no deterministic inverse to 7 axes (P95-B REJECT).
4. **num_array** (any length, incl. len-7): **REJECTED/AMBIGUOUS** — no stored axis-order contract; positional mapping would be a guess (violates deterministic rule). Flagged for a future positional-axis-order contract (analogous to D4).
5. **unparseable/empty**: UNMAPPABLE.
- **Ambiguous descriptors** (e.g. `raisins` → fruity vs sherry) are recorded, never silently resolved.
- **Provenance preserved:** every output row keeps `whisky_id`, `whisky_name`, `source`, original `method`, `confidence`.

## Converted records
- **Total canonical vectors produced = 1611**
  - pass-through axis7: **1345**
  - term-bag lexicon conversion: **266**
- Output: `mr-kep/output/p95c/canonical_vectors.csv` (whisky_id, name, source, canonical_vector, method, confidence, ambiguity_count, ambiguous_terms).

## Unmapped descriptors
Descriptors with no lexicon entry (e.g. `rich, old, smooth, complex, balanced, heavy, light, mellow, mild, dry, earthy, herbal, tobacco, floral, malty, barley, tea, amber, brown, green, lingering, zest, bitter, sour`). Full vocabulary + counts: `unmapped_vocabulary.csv` (28 distinct). These are intensity/body/quality notes, not the 7 sensory axes → correctly excluded from canonical vectors. Rows with such descriptors still produce a vector if ≥1 mappable descriptor exists.

## Ambiguous mappings
Descriptor→axis conflicts recorded in `ambiguous_mappings.csv` (14 rows). Example: `raisins` (fruity↔sherry). These are flagged, not force-resolved.

## Validation
- Before (eligible) = 1998; After (converted 1611 + rejected 387) = 1998 → **balanced: True**.
- Every canonical vector contains **exactly the 7 frozen axes** (verified programmatically).
- **Zero excluded (book/NotebookLM/T3) rows entered conversion** (excluded count = 678, all non-T2).
- Deterministic: no timestamps in artifacts; re-run yields byte-identical outputs (integrity_hash.json).
- No duplicate profiles: output keyed by `whisky_id` (PK of flavor_profiles); one row per whisky. MERGE/KEEP_SEPARATE respected (no new product records created). P35/P37 protections honored (read-only; any future promotion must use gated backup+transaction path).

## Determinism check
- `integrity_hash.json` records per-file + concat sha256. Re-running `p95c_convert.py` on unchanged DB yields identical hashes. No RNG, no clock, no network.

## GO / NO-GO recommendation
**GO (conditional).** Canonical 7-axis conversion of eligible T2/core data is complete, deterministic, and DB-safe:
- 1611 canonical vectors produced (1345 pass-through + 266 lexicon-converted).
- 387 rows correctly held out as unmappable (PCA 225, num_array without axis-order 161, term-bag none-mappable 1, unparseable 0).
- No book/NotebookLM/T3 data included (excluded = 678).

**Conditions / not-yet-converted (do not promote until resolved):**
- Book/NotebookLM (T3) vectors remain excluded pending **D4** (16/20→7 reducer).
- `num_array` vectors (len≠7 and len=7) need an **axis-order contract** before conversion (currently unmappable/ambiguous).
- These staging artifacts are **not yet written to production** — a gated P35/P37-style promotion (backup + transaction + rollback + `promotion_audit_log`) is required before any production mutation, and is out of scope for this read-only conversion task.

**Success criteria met:** deterministic outputs ✓ · zero production DB mutation ✓ · no book/NotebookLM data ✓ · canonical vectors contain only the 7 frozen axes ✓.

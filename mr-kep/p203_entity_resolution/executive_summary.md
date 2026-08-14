# P203 — Executive Summary (READ-ONLY audit + design)

**Task:** Design the canonical entity resolution layer that becomes the single
matching system for every existing and future Malt Radar ingestion pipeline.
**Mode:** READ-ONLY. No SQL executed, no DB writes, no source changes, no commits/pushes.

## What already exists (reused, not reinvented)
- **Entity tables** in `production.db` (`schema/schema.sql`): `whiskies`,
  `distilleries`, `brands`, `bottlers`, `companies`, `entity_aliases`,
  `entity_external_links`, `external_entities`, `whisky_product_entities`,
  `distillery_company_links`, `bottler_product_links`, `official_source_references`.
- **A working name matcher** (`mr-kep/editorial/matching.py`): `normalize_text` +
  `SequenceMatcher` with thresholds 0.94 / 0.88 / 0.82, margins 0.03 / 0.04,
  age/brand downgrade rules, read-only on `production.db`. Statuses
  `exact | fuzzy | manual_review | unmatched`; returns `match_confidence`.
- **A knowledge.db identity model** (`mr-kep/p136_knowledge_bootstrap/migration/schema.sql`):
  `evidence.entity_key` (whisky/distillery/brand/bottler), `normalized_metadata`,
  `review_queue` (issue_type `conflict|identity|low_conf|historical`),
  `merge_history`, `promotion_queue` (field_class `IMMUTABLE|APPEND|REPLACEABLE|REVIEW`),
  `source_priority`, `processing_log` (stages `raw→normalize→canonicalize→merge→consensus→queue→review→export`).
- **OCR/alias-aware normalization** exists in the book pipeline
  (`mr-kep/book_ingestion/B4b/classify_unresolved.py`): deterministic OCR-junk and
  `*Distillery`/`*Distillenes` handling, auto-suppression of metadata/OCR/generic noise.
- **A crosswalk** (`mr-kep/p129_crosswalk/`): 475 weak UUID↔W matches + 315 no-match,
  currently **deferred (D5)** and **not loaded** into knowledge.db.

## What is missing (must be built in the implementation phase, not here)
1. **Matcher is alias-blind** — `matching.py` never reads `entity_aliases`; it matches
   only `whiskies.name`. Other entity types (distillery/brand/bottler) have no matcher at all.
2. **Whisky-level aliases unsupported** — `entity_aliases.entity_type` enum is
   `'brand','bottler','company','distillery'` only; **`whisky` is absent**, so whisky
   identity relies solely on fuzzy name similarity.
3. **No phonetic / token strategies** — grep across `mr-kep` finds no soundex/metaphone/
   token_set/jaro matcher; only `SequenceMatcher` on a normalized string.
4. **Crosswalk not activatable** — 475/475 matches are WEAK (0.50–0.60) and the 4
   "strong" are expression-level mismatches (SMWS single-cask vs core-range), a false-positive risk.
5. **Coverage gaps** (from `mr-kep/p143_release_readiness/remaining_gaps.md`):
   `distillery_id` 59.34%, `country` 2.84%, `region` 19.94%, `brand` 39.36%.

## Verdict
**WARN_GO.** The foundation is real and reusable — P203 can be *designed* against it
without reinventing anything, and all 13 deliverables are evidence-backed. But the
model cannot yet be THE single matcher until the alias-aware / multi-entity / phonetic
gaps and the crosswalk activation are closed in a gated implementation phase. These are
WARN conditions (design-complete, implementation-blocked), not NO-GO blockers.

*No production.db / knowledge.db writes, no commits, no pushes were performed.*

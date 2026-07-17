# P135 — Execution Batches (READ-ONLY Plan)

- doc_version: P135-1
- measurable batches. Each: inputs, outputs, est. row count, completion gain, rollback.

## Batch 1 — SMWS Technical Metadata  (PRIORITY 1, highest ROI)
- inputs: `staging_smws_tasting_notes.csv` (803) + `flavor_evidence` (791) → join via `whisky_id`
- fields: cask_type, age, abv, age_statement, nas, region, country
- outputs: enriched `whiskies` rows + `official_source_references` citations
- est. rows: 791 whisky_ids enriched (mostly UUID + some W)
- gain: cask_type +54pts, age +26pts, abv +24pts, region +26pts, age_statement +24pts
- automation: FULL (regex + deterministic join)
- rollback: backup + hash guard; batch is idempotent (source_hash key) → re-run reverts via backup

## Batch 2 — SMWS Tasting Notes
- inputs: `flavor_evidence.original_tasting_note` (791 verbatim)
- fields: nose_notes, finish_notes (palate already 99.9%)
- outputs: APPEND rows in `tasting_notes` (provenance source_doc=pdf name)
- est. rows: up to 791 new nose/finish appends
- gain: nose_notes +53pts, finish_notes +53pts
- automation: FULL (section regex)
- rollback: delete-by-source_hash

## Batch 3 — Book Metadata (structured)
- inputs: `staging_book_flavor_profiles` (2,575 pending; 1,803 joinable)
- fields: cask_or_maturation→cask_type, region, country, type, brand, meta_critic_score, notes
- outputs: enriched `whiskies` + `flavor_profiles` + citations
- est. rows: 1,803 joinable (774 → review queue)
- gain: region +~10pts, type +~8pts, brand +~6pts (incremental over SMWS)
- automation: SEMI (LLM fields → review on LOW conf)
- rollback: idempotent; review items never auto-applied

## Batch 4 — Flavor Vectors (consensus-gated)
- inputs: `staging_flavor_profile_candidates_full` (6,133) + NotebookLM (17) + SMWS vectors
- fields: 7-axis `canonical_vectors` via knowledge.db `consensus_nodes`
- outputs: consensus-derived vectors; `flavor_profiles.flavor_vector` updated
- est. rows: ~2,400 distinct whisky_ids with ≥1 vector source
- gain: maintain 100% vector coverage; improve consensus quality
- automation: GATED (requires D1 bootstrap of target knowledge.db + D2 crosswalk)
- rollback: vector table restored from backup; consensus re-runnable

## Batch 5 — Descriptions & Knowledge
- inputs: books (raw PDF/EPUB, 849) via NotebookLM/LLM
- fields: `brands.description`, `knowledge_glossary_terms`, `knowledge_guides`, `knowledge_regions.description`
- outputs: APPEND-ONLY knowledge + citations
- est. rows: variable (description per brand ~471; terms/guides from 24 books)
- gain: knowledge surface expansion
- automation: SEMI (LLM + review)
- rollback: idempotent by source_hash

## Batch 6 — Final Normalization & Recompute
- inputs: all post-batch `whiskies`/`flavor_profiles`
- fields: `completed_fields` (recompute count), `data_confidence` (max), `flavor_data_confidence`
- outputs: fully recomputed metadata
- est. rows: 4,749 whiskies + 3,467 flavor_profiles
- gain: completed_fields 0→100%, data_confidence +24pts
- automation: FULL (deterministic)
- rollback: recompute is pure function of inputs → re-run safe

## Sequencing & dependencies
```
B1 (SMWS tech) ─┐
B2 (SMWS notes) ├─→ B3 (books) ─→ B4 (vectors, needs D1+D2) ─→ B5 (knowledge) ─→ B6 (recompute)
B6 can run after any batch (idempotent recompute)
```
- B1/B2 require NO prerequisites (SMWS joins deterministic). START HERE.
- B4 blocked until D1 (target knowledge.db) + D2 (uuid↔W crosswalk) clear (see P128/P129).
- B3 can start in parallel with B1 but lower priority.

## Rollback strategy (all batches)
- Pre-batch: `cp production.db production.db.pre-p135-bN.bak` + record sha256.
- Gate: all writes via `get_write_connection`.
- Post-batch: `integrity_check` + `foreign_key_check` + citation==change count.
- Rollback = restore `.bak` (idempotent keys make partial revert unnecessary, but full restore is the safe path).

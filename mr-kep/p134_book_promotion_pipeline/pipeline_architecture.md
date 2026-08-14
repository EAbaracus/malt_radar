# P134 — Pipeline Architecture (READ-ONLY Design)

- doc_version: P134-1
- deterministic, repeatable book→production promotion pipeline. DESIGN ONLY; no writes.

## Stage graph
```
┌─────────────┐
│ Book corpus  │  PDF/EPUB (data/books/, SMWS archive)  [849 files]
└──────┬──────┘
       │  file_hash → book_versions (dedupe #11/#42)
       ▼
┌─────────────┐
│ 1. OCR       │  scanned → text, page-aligned; parser_confidence
└──────┬──────┘
       ▼
┌─────────────┐
│ 2. Chunk     │  by section/expression; preserve book+page provenance
└──────┬──────┘
       ▼
┌─────────────┐
│ 3. Extract   │  P135 Extraction Engine: regex+LLM+lookup → typed fields
└──────┬──────┘
       ▼
┌─────────────┐
│ 4. Normalize │  P136: numeric/text/flavor/axis → canonical (normalization_rules.md)
└──────┬──────┘
       ▼
┌─────────────┐
│ 5. Validate  │  field-class check (field_merge_matrix); schema/type/null checks
└──────┬──────┘
       ▼
┌─────────────┐
│ 6. Consensus │  P137: field-level precedence + knowledge.db vector consensus
└──────┬──────┘
       ▼
┌─────────────┐
│ 7. Confidence│  per-field + record; assign band (confidence_engine.md)
└──────┬──────┘
       ▼
┌─────────────┐
│ 8. Stage     │  → staging_* tables; one row per (entity,field,source_hash)
└──────┬──────┘
       ▼
   ┌───┴───────────┐
   │ DECISION      │  band + field class
   └───┬───────────┴───┐
       │                │
   HIGH+APPEND/         │ REVIEW-REQUIRED /
   REPLACEABLE          │ LOW / conflict / AMBIGUOUS
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────────────────┐
│ 9a. Promote  │  │ 9b. staging_manual_      │
│ (via gate)   │  │     review_queue         │
└──────┬──────┘  └───────────┬─────────────┘
       │                      │ human decision
       ▼                      ▼
┌─────────────┐  ┌─────────────────────────┐
│ Production   │  │ review_actions →         │
│ (P121 gate)  │  │ approved_for_promotion   │
└──────────────┘  └───────────┬─────────────┘
                              │
                              ▼
                     ┌──────────────┐
                     │ Promotion     │  (P121 gate, same path)
                     └──────────────┘
```

## Decision points (explicit)
1. **After Validate**: IMMUTABLE field in incoming → DISCARD (cite only).
2. **After Consensus**: conflict detected → log `review_conflict_log`, divert field to queue (C4).
3. **After Confidence**: band assignment decides auto vs review vs reject.
4. **Price field anywhere**: hard-stop firewall (C7) — never enters staging.
5. **Flavor vector**: only consensus-derived rows may write `canonical_vectors`; raw book vectors rejected from direct write (§5/promotion_contract §5).
6. **Citation missing**: promotion rejected (C1) — no citation, no promotion.

## Gate integration
- All writes (stages 9a/b) go through `db_write_guard.get_write_connection(authorized_context=...)`.
- Pre-write: backup (AGENTS.md) + hash guard.
- Post-write: `PRAGMA integrity_check` + `foreign_key_check` (gate-enforced) + citation-count == change-count verification.

## Idempotency
- Every staged/promoted change keyed by (entity_type, entity_id, field_name, source_hash) → re-run is no-op (C2).

## Repeatability
- Deterministic given (book file_hash, extraction prompt version, normalization rules version). Version stamp `enrichment_version` on `flavor_profiles`; `run_hash` on `promotion_runs`.

# P136 — Runtime Architecture

- doc_version: P136-1
- components under runtime/: migrate.py, ingest.py.

## migrate.py
- Applies migration/schema.sql then migration/migration.sql.
- Records each application in schema_version (version, description, baseline_sig).
- Idempotent: every DDL is `IF NOT EXISTS` / guarded; replay bumps version but re-applies no conflicting DDL.
- NEVER opens production.db.

## ingest.py — 7-stage pipeline
```
raw ─► normalize ─► canonicalize ─► evidence_merge ─► consensus ─► promotion_queue ─► manual_review
                                                                              │
                                                                              └─► (production export, dry-run plan only)
```
| stage | reads | writes | notes |
|---|---|---|---|
| raw | staging CSV / production.flavor_evidence (RO) | citations, sources | one citation per source fact; hash dedupe |
| normalize | citations | (in-place prep) | regex/LLM normalizers (age/abv/cask/region/axis) |
| canonicalize | staging CSV + flavor_evidence (RO) | normalized_metadata | entity resolution via whisky_id (UUID canonical) |
| evidence_merge | normalized_metadata | evidence | field-level claims (APPEND-ONLY) |
| consensus | flavor_evidence (RO) | canonical_flavor_vectors | 7-axis normalized 0-100; single-source SMWS for now |
| promotion_queue | normalized_metadata | promotion_queue | field_class→action (APPLY/APPEND/REVIEW); dedupe_key UNIQUE |
| manual_review | promotion_queue | review_queue | REVIEW-action items → review_queue |

## Merge rules implemented (P135)
- **source priority**: source_priority table seeded (smws>reference>general>notebooklm>periodical>community>web).
- **confidence propagation**: 4-signal weighted (extraction/parser/signal/source) — wired in evidence + confidence tables.
- **duplicate detection**: dedupe_key UNIQUE on promotion_queue + merge_history; note_hash on canonical_tasting_notes.
- **canonical flavor axis enforcement**: only the 7 canonical axes stored; `rich` mapped to sweet-side, `maritime` carried separately (per P134/P135 axis finding).
- **citation preservation**: every evidence/queue row carries citation_id → citations → sources (provenance chain).
- **review generation**: REVIEW-class fields → review_queue with suggested_action.

## Gate integration (future P138)
- promotion_queue rows are the ONLY input to production promotion. P138 reads them via get_write_connection, honoring field_class + C1 citation + dedupe_key.
- This runtime writes ONLY knowledge.db; production.db is read-only (ingest.rd).

## Determinism / idempotency
- Every mutation keyed by stable hash (dedupe_key, note_hash, source_hash, file_hash) → re-run is a no-op (verified by test_05).

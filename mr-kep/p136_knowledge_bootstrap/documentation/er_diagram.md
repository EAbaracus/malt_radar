# P136 — knowledge.db Schema (ER Diagram, text)

- doc_version: P136-1
- generated from migration/schema.sql (authoritative). UUID PKs, timestamps, confidence, source, provenance on every table.

## Entity tables
```
sources(1) ───< books(1) ───< book_pages(*)
   │
   ├──< citations(*)
            │
            ├──< evidence(*)
                     │
                     ├──< promotion_queue(*)
                     └──< merge_history(*)

normalized_metadata(1) ──< canonical_flavor_vectors(*)
                        ├──< canonical_tasting_notes(*)
                        └──< confidence(*)

review_queue(*)   source_priority(*)   processing_log(*)
```

## Table → purpose
| table | role |
|---|---|
| schema_version | migration ledger (version, baseline_sig) |
| sources | every upstream origin (book/notebooklm/smws/community/web) + authority_tier |
| books | one row per ingested book (file_hash dedupe) |
| book_pages | OCR/chunk, page-aligned provenance |
| citations | fact anchor (book+page / smws pdf / notebooklm run) |
| evidence | field-level extracted claim (normalization output) |
| canonical_flavor_vectors | consensus 7-axis (smoky,peaty,fruity,sweet,spicy,maritime,sherry) |
| canonical_tasting_notes | append-only notes (note_hash dedupe) |
| normalized_metadata | resolved entity attributes (post-consensus) |
| confidence | per-field confidence ledger |
| promotion_queue | rows ready for production promotion (gated) |
| review_queue | REVIEW/conflict/ambiguous items |
| source_priority | configured precedence (P135 conflict_policy) |
| merge_history | every applied merge (dedupe_key UNIQUE → idempotency) |
| processing_log | stage-level run log |

## Foreign keys (enforced: PRAGMA foreign_keys=ON)
sources←books, sources←citations, books←citations, books←book_pages,
citations←evidence, citations←promotion_queue, citations←merge_history.

## Indexes (perf + dedupe)
idx_books_hash, idx_evidence_entity, idx_evidence_cit, idx_cit_hash,
idx_vec_entity, idx_note_entity, idx_note_hash, idx_meta_entity,
idx_pq_dedupe (UNIQUE), idx_pq_status, idx_mh_dedupe (UNIQUE), idx_conf_entity, idx_src_type.

## Scale observed (initial SMWS sample)
normalized_metadata=724 (staging-overlap subset of 791), canonical_flavor_vectors=791
(all flavor_evidence), citations=791+, evidence=724, promotion_queue=2664, review_queue=1431.

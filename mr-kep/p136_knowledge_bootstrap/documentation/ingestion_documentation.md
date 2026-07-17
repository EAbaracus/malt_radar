# P136 — Ingestion Documentation

- doc_version: P136-1

## What this runtime does
Bootstraps and populates the production `knowledge.db` from read-only sources
(staging CSVs, production.db `flavor_evidence` for SMWS). It implements the 7-stage
pipeline and all P135 merge rules. It NEVER writes production.db.

## Prerequisites
- Python 3.11 (sqlite3 stdlib).
- Read-only access to: `mr-kep/p119_6/staging_smws_tasting_notes.csv`, `output/import/production.db`.
- Write access to target `knowledge.db` (default `output/import/knowledge.db`).

## Commands
```bash
# 1. Bootstrap schema (idempotent; replay-safe)
python runtime/migrate.py --kb output/import/knowledge.db

# 2. Run SMWS ingestion (7 stages)
python runtime/ingest.py --kb output/import/knowledge.db --source smws --run-id P136_INITIAL

# 3. Validate (standalone test harness builds its own TEMP db)
python tests/test_bootstrap.py
```

## Source support (roadmap)
| source | status | notes |
|---|---|---|
| SMWS | IMPLEMENTED | staging CSV + flavor_evidence; 791 vectors, 724 normalized |
| books | scaffolded | book_pages + citations wired; full OCR/LLM extraction is P136-ext (reuse P134 extractors) |
| NotebookLM | schema-ready | staging_notebooklm_flavor_profiles maps to evidence/canonical_flavor_vectors |
| community | schema-ready | source_type='community' in source_priority |
| web | schema-ready | migration.sql has web_snapshots template |

## Initial SMWS run results (real knowledge.db)
```
raw=803  normalize=798  canonicalize=724  evidence_merge=724
consensus=791  promotion_queue=2664  manual_review=1431
```
- normalized_metadata=724 (staging-overlap subset of 791 flavor_evidence whisky_ids)
- canonical_flavor_vectors=791 (all flavor_evidence rows; 7-axis, 0-100 normalized)
- promotion_queue=2664 → 1431 REVIEW-action rows routed to review_queue
- production.db hash unchanged (verified)

## Re-running
- Safe. dedupe_key (UNIQUE) + OR IGNORE make re-runs no-ops (test_05 asserts counts stable).

## Promotion handoff (P138)
- promotion_queue is the contract: each row = one field change with field_class + action + citation_id.
- P138 reads promotion_queue via the P121 write-gate, applies APPEND/APPLY, diverts REVIEW to human.

## Known limitations (honest)
- Consensus is single-source (SMWS) for the initial load; multi-source weighted consensus (P134 §4) is wired via source_count/confidence but activates when books/NotebookLM are ingested.
- Axis scale confirmed non-0-100 in canonical_vectors (smoky 0-945…); this runtime normalizes inputs to 0-100 and stores axis_scale='0-100' for traceability.

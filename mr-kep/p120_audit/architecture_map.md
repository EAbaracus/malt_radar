# KEP Architecture Map — P120 Audit

## Canonical vs Actual Architecture

### DESIGNED Architecture (from Sprint 1 specs)

```
Source (whiskyfun, SMWS, books, retailers)
  │
  ▼
[Qualification Engine] — P71
  │  Decision: in_scope / out_of_scope / deferred
  ▼
[Evidence Engine] — P73
  │  Emits: discovered evidence candidates (null field_value)
  ▼
[Execution Engine] — P68
  │  State machine: Queued → Qualified → Waiting → Extracting →
  │  Evidence Recording → Validation → Certification Ready → Completed/Rejected
  ▼
[Certification Engine] — P63
  │  Paths A-F per field, aggregate CERTIFIED/HOLD/REJECTED
  ▼
[Canonical Output] — P65
  │  schema-validated, 7-part artifact
  ▼
[Promotion Gate] — future (not implemented in Sprint 2)
  │  writes to knowledge.db or production.db after explicit approval
  ▼
Production / KnowledgeDB
```

### ACTUAL Runtime (what files and functions exist)

```
┌────────────────────────────────────────────────────────────────────┐
│ CANONICAL KEP PIPELINE (pipeline/run.py)                          │
│                                                                    │
│ run_pipeline(fixture_path, run_id)                                 │
│   ├─ run_qualification()     → QE.run_batch()          → output/qualification.json
│   ├─ run_evidence_engine()   → EE.run()                 → output/evidence.jsonl
│   ├─ run_execution()         → EXEC_ENGINE.ExecutionEngine()
│   │                            .run_to_completion()     → output/execution.json
│   ├─ produce_extracted_evidence()  → bridges discover→extract
│   ├─ run_certification()    → CE.certify()             → output/certification.json
│   ├─ build_canonical_output()                           → output/canonical_output.json
│   └─ write_manifest()                                   → output/run_manifest.json
│                                                                    │
│ run_batch_csv(csv_path) — parallel batch for CSV candidates       │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ BOOK ENRICHMENT SPRINTS (standalone, not through KEP pipeline)     │
│                                                                    │
│ enrich_mw_yearbook_2019.py  → extract_entities → build_consensus   │
│ enrich_sprint02.py          → ID scheme → knowledge.db → WAL write │
│ enrich_michael_jackson.py   → extract + consensus → knowledge.db   │
│ enrich_whisky_advocate.py   → global page counter → knowledge.db   │
│ enrich_jim_murray_2020.py   → extract + consensus → knowledge.db   │
│ enrich_whisky_manual.py     → EPUB extract + consensus → know.db   │
│                                                                    │
│ Target: mr-kep/p102_bootstrap/knowledge.db                         │
│ Schema: 12 tables (citations, evidence_nodes, extracted_facts,     │
│          consensus_nodes, canonical_vectors, etc.)                 │
│ Current state: 13,133 facts, 3,077 consensus, 3,077 vectors       │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ STRUCTURED SOURCE INTAKE (standalone retail pipeline)              │
│                                                                    │
│ Vinmonopolet / Alko / HTFW / WhiskyNotes                          │
│   → structured CSV → entity resolution → promotion                 │
│   → knowledge.db (39 entities promoted)                            │
│                                                                    │
│ This pipeline has its OWN resolution logic, NOT KEP's              │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ P119 SMWS EXTRACTION (standalone, ORPHANED)                       │
│                                                                    │
│ 803 SMWS PDFs                                                      │
│   → raw_extractions.csv (structured fields)                        │
│   → flavor_evidence.csv (flavor prose)                             │
│   → canonical_vectors_staging.csv (7-axis scores)                  │
│   → resolved_entities.csv (1 entity resolved out of 792)           │
│   → unresolved_entities.csv (791 unresolved)                       │
│   → coverage_report.md, quality_report.md                          │
│                                                                    │
│ P120 SMWS PROMOTION: output files only — NEVER reached any DB      │
│   → promotion_ready.csv                                            │
│   → promotion_report.md ("successfully promoted" — FALSE)          │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ ACQUISITION PIPELINE (P92-P95, SIMULATED)                         │
│                                                                    │
│ acquisition/run_pipeline.py                                         │
│   → Hardcoded telemetry (3 mock URLs, 400 tokens "saved")          │
│   → No real HTTP acquisition                                       │
│   → No real cache persistence                                      │
│   → Dry-run only                                                   │
│                                                                    │
│ Files: http_fetcher.py, content_cache.py, crawler_queue.py         │
│   → Modules exist with real interfaces but never called            │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ P96 PIPELINE (standalone, DUPLICATED)                              │
│                                                                    │
│ p96_pipeline/pipeline_orchestrator.py                              │
│   → llm_extractor.py (its own extractor)                           │
│   → entity_resolver.py (its own resolver)                          │
│   → consensus_engine.py (its own consensus)                        │
│   → evidence_graph.py (its own evidence)                           │
│   → chunking_engine.py (its own chunker)                           │
│   → cache_manager.py (its own cache)                               │
│                                                                    │
│ This is a COMPLETE parallel implementation of what the main        │
│ KEP pipeline already provides — with a different interface.        │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ D4 REDUCER (7-axis flavor mapper, standalone)                      │
│                                                                    │
│ d4_reducer/d4_orchestrator.py                                      │
│   → axis_reducer.py — maps legacy flavors → 7 canonical axes       │
│   → flavor_mapper.py — keyword→axis mapping                        │
│   → ambiguity_handler.py — resolves ambiguous descriptors          │
│                                                                    │
│ Output: canonical_mapping.json, canonical_vectors.json             │
│ Run modes: staging, live_staging, certification                    │
└────────────────────────────────────────────────────────────────────┘

## Data Flow Dead Ends

1. **P119 SMWS → nothing**: 792 extracted expressions, 792 flavor vectors — zero reach any database
2. **Acquisition pipeline → nowhere**: Simulated crawls produce reports but no actual data extraction
3. **P96 pipeline → output files only**: Its staging output was never wired to knowledge.db ingestion
4. **KEP pipeline → output files only**: The canonical pipeline produces certification.json and canonical_output.json but these are NEVER promoted to knowledge.db or production.db

## The Only ACTIVE write path to knowledge.db

```
Books (PDF/EPUB) → Book Enrichment Sprint loaders → knowledge.db
Retail CSVs     → Structured Source Intake loaders    → knowledge.db
```

These bypass the KEP pipeline entirely.

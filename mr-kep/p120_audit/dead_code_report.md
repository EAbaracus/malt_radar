# KEP Stage Classification — P120 Audit

## Sprint 2 Pipeline Stages (mr-kep/pipeline/run.py)

| Stage | File | Function | Classification | Evidence |
|---|---|---|---|---|
| 1. Qualification | `qualification_engine/engine.py` | `QE.run_batch()` | **ACTIVE** | Called by `run_pipeline()` line 75 and `run_batch_csv()` line 605 |
| 2. Evidence Engine | `evidence_engine/engine.py` | `EE.run()` | **ACTIVE** | Called by `run_pipeline()` line 98 |
| 3. Execution Engine | `extraction_execution/engine.py` | `ExecutionEngine.run_to_completion()` | **ACTIVE** | Called by `run_pipeline()` line 156 and `run_batch_csv()` line 633 |
| 4. Extract Evidence (bridge) | `pipeline/run.py` | `produce_extracted_evidence()` | **ACTIVE** | Called by `run_pipeline()` line 511 |
| 5. Certification | `certification_engine/__init__.py` | `CE.certify()` | **ACTIVE** | Called by `run_pipeline()` line 302 |
| 6. Canonical Output | `pipeline/run.py` | `build_canonical_output()` | **ACTIVE** | Called by `run_pipeline()` line 521 |
| 7. Run Manifest | `pipeline/run.py` | `write_manifest()` | **ACTIVE** | Called by `run_pipeline()` line 555 |

### Stage Status Details

Each stage has working code but **the pipeline as a whole processes only test fixtures** (`fixtures/sample_whisky.json`) and has never processed real source data end-to-end. The certification engine applies correct rules but receives evidence only from extracted fixtures or CSV candidates, not from a live acquisition feed.

---

## Acquisition Pipeline Stages (mr-kep/acquisition/)

| Stage | File | Classification | Evidence |
|---|---|---|---|
| Source Registry | `source_registry.py` | **DEAD CODE** | Module exists with real interface but never called from any active pipeline |
| Crawler Queue | `crawler_queue.py` | **DEAD CODE** | run_pipeline.py creates mock queue with hardcoded entries |
| Scheduler | `scheduler.py` | **DEAD CODE** | Never called with real sources |
| Change Detector | `change_detector.py` | **DEAD CODE** | Only called with mock content strings in run_pipeline.py |
| Rate Limiter | `rate_limiter.py` | **DEAD CODE** | Never exercised with real crawl |
| Http Fetcher | `http_fetcher.py` | **DEAD CODE** | Interface exists; real HTTP never used |
| Content Cache | `content_cache.py` | **DEAD CODE** | Never persisted; reset every run |
| Telemetry | `telemetry.py` | **DEAD CODE** | Hardcoded telemetry values in run_pipeline.py |
| Adapters | `adapters/*.py` | **DEAD CODE** | MasterofMalt, Whiskybase, WhiskyNotes — interfaces exist but never wired |

**Verdict:** The entire acquisition directory is a **simulation artifact**. Modules have real interfaces but the orchestrator (`run_pipeline.py`) hardcodes every metric. Never connected to the outside world.

---

## Book Enrichment Sprint Stages (mr-kep/book_enrichment_sprint*/)

| Stage | File | Classification | Evidence |
|---|---|---|---|
| PDF Text Extraction | Various `enrich_*.py` | **ACTIVE** | Processes real PDFs |
| Entity Extraction | `extract_entities()` (frozen module) | **ACTIVE** | Called by every sprint |
| Entity Resolution | Inline in each loader | **ACTIVE** | Cross-references production.db |
| Consensus Building | `build_descriptor_consensus()` | **ACTIVE** | Writes to consensus_nodes |
| Vector Generation | Vector builder in each loader | **ACTIVE** | Writes to canonical_vectors |
| DB Loader | `save_to_knowledge_db()` (frozen) | **ACTIVE** | Writes ALL data to knowledge.db |

Note: Book enrichment has its OWN implementation of entity resolution, consensus, and vector generation — DUPLICATED from the KEP pipeline.

---

## P96 Pipeline Stages (mr-kep/p96_pipeline/)

| Stage | File | Classification | Evidence |
|---|---|---|---|
| Pipeline Orchestrator | `pipeline_orchestrator.py` | **SUPERSEDED** | Book enrichment sprints replaced this |
| LLM Extractor | `llm_extractor.py` | **SUPERSEDED** | Rule-based extraction replaced LLM approach |
| Chunking Engine | `chunking_engine.py` | **SUPERSEDED** | Not used in current sprints |
| Entity Resolver | `entity_resolver.py` | **SUPERSEDED** | Has its OWN resolution logic → duplicated |
| Consensus Engine | `consensus_engine.py` | **SUPERSEDED** | Has its OWN consensus → duplicated |
| Evidence Graph | `evidence_graph.py` | **SUPERSEDED** | Has its OWN evidence model → duplicated |
| Cache Manager | `cache_manager.py` | **SUPERSEDED** | Not used in current sprints |

---

## D4 Reducer Stages (mr-kep/d4_reducer/)

| Stage | File | Classification | Evidence |
|---|---|---|---|
| Orchestrator | `d4_orchestrator.py` | **PARTIALLY USED** | Canonical flavor mapper |
| Axis Reducer | `axis_reducer.py` | **ACTIVE** | 20-axis/16-axis → 7-axis canonical |
| Flavor Mapper | `flavor_mapper.py` | **ACTIVE** | Keyword→axis lookup |
| Ambiguity Handler | `ambiguity_handler.py` | **ACTIVE** | Ambiguous descriptor resolution |

---

## P119 SMWS Pipeline (mr-kep/p119_smws_extraction/)

| Stage | File | Classification | Evidence |
|---|---|---|---|
| PDF Extraction | Not committed (external scripts) | **ORPHANED** | Output files exist but no source scripts committed |
| Entity Resolution | Not committed | **ORPHANED** | 1/792 resolved |
| Flavor Vectorization | Not committed | **ORPHANED** | 792 vectors generated |
| Promotion (P120) | Not committed | **ORPHANED** | Output files claim success; data reached NO database |

---

## Structured Source Intake Stages (mr-kep/structured_source_intake/)

| Stage | Classification | Evidence |
|---|---|---|
| CSV Intake | **COMPLETED** | Vinmonopolet (39 entities), Alko, HTFW, WhiskyNotes all processed |
| Entity Resolution | **COMPLETED** | Resolved against existing IDs |
| Promotion | **COMPLETED** | Data reached knowledge.db |

---

## Stage Summary

| Stage Group | Classification |
|---|---|
| Sprint 2 KEP Pipeline (canonical) | ACTIVE — but processes test fixtures only |
| Book Enrichment Sprints | ACTIVE — real data flows to knowledge.db |
| D4 Reducer (7-axis map) | PARTIALLY USED |
| Structured Source Intake | COMPLETED |
| Acquisition Pipeline (P92-P95) | DEAD CODE (simulation only) |
| P96 Pipeline | SUPERSEDED (replaced by book enrichment) |
| P46 SMWS Review Queue | DEAD CODE (P119 redid from scratch differently) |
| P119 SMWS Extraction | ORPHANED (outputs exist; no committed scripts) |
| P120 SMWS Promotion | ORPHANED (data never entered any database) |
| P53 Flavor Verification | SUPERSEDED (superseded by P95 canonical) |
| P60 Whiskybase Staging | DEAD CODE |
| P97/P98 Promotion | SUPERSEDED (book sprints have their own promotion) |
| Ground Truth | UNREACHABLE (100 source_records never processed through pipeline) |
| Candidate Selection | DEAD CODE (markdown only) |
| Workstream C | DEAD CODE (documentation only) |

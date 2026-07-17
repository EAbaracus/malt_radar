# KEP Runtime Execution Graph — P120 Audit

## LEGEND

```
[Stage]          = Processing step
[Stage]─┬─(...)  = Multiple parallel paths
[File]           = Concrete file implementing the stage
Function()       = Concrete function called
→ Output         = Artifact produced
```

---

## 1. CANONICAL KEP PIPELINE (Sprint 2)

```
[Fixture JSON]
 │  fixtures/sample_whisky.json
 ▼
run_pipeline() — mr-kep/pipeline/run.py (lines 474–565)
 │
 ├── Stage 1: Qualification
 │   ├── File: mr-kep/qualification_engine/engine.py
 │   ├── Function: QE.run_batch(source_key, input_units)
 │   ├── Also uses: classifier.py, scorer.py, gates.py, config.py, strategy.py, emit.py
 │   └── → output/qualification.json
 │
 ├── Stage 2: Evidence Engine (discovery)
 │   ├── File: mr-kep/evidence_engine/engine.py
 │   ├── Function: EE.run(qualification_records)
 │   ├── Also uses: authority/confidence.yaml, source_priority.yaml,
 │   │             resolution/source_resolution_model.yaml
 │   ├── Emits: discovered candidates (provenance_state='discovered', field_value=null)
 │   └── → output/evidence.jsonl (appended to)
 │
 ├── Stage 3: Execution Engine (P68 state machine)
 │   ├── File: mr-kep/extraction_execution/engine.py
 │   ├── Function: ExecutionEngine(run_id).run_to_completion()
 │   ├── States: QUEUED→QUALIFIED→WAITING→EXTRACTING→
 │   │           EVIDENCE_RECORDING→VALIDATION→CERTIFICATION_READY→COMPLETED
 │   ├── Also uses: checkpoints.py (checkpoint persistence)
 │   │             evidence.py (evidence bundle building)
 │   └── → output/execution.json
 │
 ├── Stage 3b: Bridge Extraction → Evidence
 │   ├── Function: produce_extracted_evidence() (lines 177–293 in run.py)
 │   ├── Reads fixture extracted_fields → creates P64-compatible evidence entries
 │   ├── Sets provenance_state='extracted', confidence=0.90
 │   ├── Merges discovered + extracted, deduplicates by evidence_id
 │   └── → output/evidence.jsonl (final combined)
 │
 ├── Stage 4: Certification
 │   ├── File: mr-kep/certification_engine/__init__.py
 │   ├── Function: CE.certify(entity_key, entity_type, qual_record, evidence_ledger)
 │   ├── Paths A–F per field (resolution/certification_paths.md)
 │   ├── Aggregate: CERTIFIED / HOLD / REJECTED
 │   ├── Hard rules: certify_min=0.70, FIELD_CEILING (authority_matrix.yaml)
 │   └── → output/certification.json
 │
 ├── Stage 5: Canonical Output
 │   ├── Function: build_canonical_output()
 │   ├── Schema: extraction/canonical_output.schema.json
 │   ├── 7 parts: entity, metadata, evidence, provenance, confidence,
 │   │            certification, merge_candidates
 │   └── → output/canonical_output.json
 │
 └── Stage 6: Run Manifest
      ├── Function: write_manifest()
      ├── SHA-256 for every artifact
      └── → output/run_manifest.json
```

---

## 2. BATCH PIPELINE PARALLEL PATH

```
run_batch_csv(csv_path) — mr-kep/pipeline/run.py (lines 568–696)
 │
 │ Reads gold_dataset_manifest.csv → iterates candidates
 │
 ├── For EACH candidate:
 │   ├── 1. Qualification (QE.run_batch)
 │   ├── 2. Extraction (extractor.run_extraction from extraction_engine/)
 │   ├── 3. Execution (ExecutionEngine)
 │   ├── 4. Certification (CE.certify)
 │   └── → Accumulates results
 │
 ├── → output/extraction_results.jsonl
 ├── → output/evidence_bundle.jsonl
 ├── → output/extraction_manifest.json
 └── → output/extraction_statistics.md
```

---

## 3. BOOK ENRICHMENT SPRINT PIPELINE

```
[PDF / EPUB]
 │
 ├── extract_pdf_text(pdf_path) — pypdf (frozen)
 │   └── → List of {page_num, text, text_len}
 │
 ├── load_production_lexicon(conn) — reads production.db whiskies
 │
 ├── extract_entities(pages, lexicon)
 │   ├── Regex-based entity extraction
 │   ├── Cross-references against production.db names
 │   └── → List of {entity_id, whisky_id, page, name, citations, descriptors}
 │
 ├── build_descriptor_consensus(entities)
 │   └── → Dict of {whisky_id: {axe: score, ...}}
 │
 ├── build_p103_candidates(entities, consensus, book_key)
 │   └── → citations, evidence_nodes, extracted_facts, consensus_nodes,
 │          canonical_vectors, promotion_candidates
 │
 └── save_to_knowledge_db(conn, candidates)
      └── → INSERT into knowledge.db
```

**Executed for:** MW Yearbook, World Atlas, Michael Jackson, Whisky Advocate, Jim Murray, DB Manual (EPUB)

---

## 4. STRUCTURED SOURCE INTAKE PIPELINE

```
[CSV — Vinmonopolet / Alko / HTFW / WhiskyNotes]
 │
 ├── Parse CSV rows
 ├── Entity resolution against production.db name/original_name
 │   ├── Matched → existing_entities.csv
 │   └── Unmatched → ambiguous_entities.csv (manual review)
 │
 ├── Promotion candidates → promotion_ready.csv
 ├── Promotion to knowledge.db (via custom loader)
 └── Reports → sprint_report.md, statistics.json
```

---

## 5. P119 SMWS EXTRACTION (ORPHANED — no committed scripts, only outputs)

```
[SMWS PDFs — 803 files]
 │
 ├── Processing: 0.78s, 98.63% success
 │
 ├── → raw_extractions.csv (structured fields per expression)
 │     Columns: file_name, smws_code, distillery_code, expression_name,
 │              age, vintage, bottling_year, abv, cask_type, region, outturn, price
 │
 ├── → flavor_evidence.csv (flavor prose extracted)
 │
 ├── → canonical_vectors_staging.csv (7-axis scores per SMWS code)
 │     Axes: smoky, peaty, sherry, fruity, spicy, sweet, rich
 │
 ├── → resolved_entities.csv (1 entity resolved: 127.9 → W001645)
 │
 ├── → unresolved_entities.csv (791 unresolved)
 │
 ├── → provenance.csv (provenance chain per extraction)
 │
 └── Statistics: 792 expressions, 792 vectors, average confidence 0.0013
```

---

## 6. ACQUISITION PIPELINE (SIMULATED — dead code)

```
run_pipeline() — mr-kep/acquisition/run_pipeline.py
 │
 ├── SourceRegistry(registry.json)
 ├── CrawlerQueue(crawl_queue.jsonl) — 3 mock URLs enqueued
 ├── RateLimiter — instantiated but never governs
 ├── Scheduler — instantiated but never schedules
 ├── ChangeDetector — called with mock "CONTENT A" strings
 │
 ├── Metrics — hardcoded:
 │   ├── discovered_pages = 3 (hardcoded)
 │   ├── changed_pages = 2 (hardcoded)
 │   ├── extracted_evidence = 5 (hardcoded)
 │   ├── token_savings = 400 (hardcoded)
 │   └── crawl_duration = 1.25 (hardcoded)
 │
 └── Reports → crawler_metrics.json, token_savings.json,
               p92_report.md, p92_validation_report.md
```

---

## 7. D4 REDUCER PIPELINE

```
[Input data — flavor descriptors from any source]
 │
 ├── flavor_mapper.py — keyword→canonical_axis mapping
 ├── axis_reducer.py — 20/16 axes → 7 canonical axes reduction
 ├── ambiguity_handler.py — ambiguous descriptor resolution
 │
 ├── d4_orchestrator.py — coordinates:
 │   ├── Run modes: staging, live_staging, certification
 │   └── → canonical_mapping.json, canonical_vectors.json,
 │          mapping_statistics.json, review_queue.json,
 │          unmapped_descriptors.json, validation_report.md
```

---

## 8. P96 PIPELINE (SUPERSEDED — parallel implementation)

```
[PDF documents]
 │
 ├── chunking_engine.py → text chunks
 ├── llm_extractor.py → entity extraction
 ├── entity_resolver.py → entity resolution (ITS OWN)
 ├── consensus_engine.py → descriptor consensus (ITS OWN)
 ├── evidence_graph.py → evidence relationships (ITS OWN)
 └── pipeline_orchestrator.py → coordinates all
      └── → output/p96_staging/
```

---

## DATA FLOW GAPS

```
Source                     → Pipeline Used              → Target DB      → Status
────────────────────────────────────────────────────────────────────────────────────
WhiskyFun (fixtures)       → KEP Sprint 2 Pipeline      → output files    → TEST ONLY
Books (PDF/EPUB)           → Book Enrichment Sprints    → knowledge.db    → ✅ REAL
Retail CSVs                → Structured Source Intake   → knowledge.db    → ✅ REAL
SMWS PDFs (P119)           → Unknown external scripts   → NO DATABASE     → ❌ ORPHANED
Web sources (hypothetical) → Acquisition Pipeline       → NO PIPELINE     → ❌ SIMULATED
P96 books                  → P96 Pipeline               → staging files   → ❌ SUPERSEDED
KEP certified output       → (no promotion gate)        → NO DATABASE     → ❌ BROKEN PATH
```

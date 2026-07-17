# Git Architecture History — P120 KEP Audit

## Project Timeline (chronological, oldest → newest)

### Phase 0: Foundation (Initial — P44)
| Commit Range | Purpose | Status |
|---|---|---|
| `c245059` — `30795dd` | Initial repo, CSV dataset, basic pipelines, P44 clustering | ARCHIVED |
| Various `test(audit)` | Pre-P45 flavor audits, manual review packs, staging dry-runs | ARCHIVED |

### P45–P52: First Pipeline Layer
**Commit:** `2d4321e feat: add P45-P52 pipeline scripts and verification tooling`
- **Purpose:** First structured source extraction pipeline (SMWS inventory + audit, parsing, flavor extraction, matching)
- **Still Exists:** `scripts/p45_*.py`, `scripts/p46_smws_review_queue.py`, `output/p45/` directory
- **Obsolete:** Much of the early P45 flavor logic was pre-standardization (before 7-axis canonical model)
- **Current:** These scripts exist but are not wired into any modern pipeline; they are legacy artifacts

### P46: SMWS Human Review Queue
**Commit:** `c979c8a P46: SMWS human review queue generator (staging-only, no prod write)`
- **Purpose:** First SMWS processing attempt — generated a human-review queue for SMWS expressions
- **Still Exists:** `scripts/p46_smws_review_queue.py`
- **Obsolete:** Entirely — P119 re-did SMWS extraction from scratch with a different methodology
- **Current:** NOT ACTIVE

### P53: Flavor Verification Pipeline
**Commit:** `4b4a1df feat: add P53 flavor verification pipeline`
- **Purpose:** Added deterministic flavor verification using snapshot comparisons
- **Still Exists:** Git history shows the pipeline existed; `ef6f537 fix(p53): harden verification snapshot integrity`
- **Obsolete:** Pre-7-axis-canonical flavor logic
- **Current:** NOT ACTIVE — superseded by P95 canonical flavor certification

### P54–P56: Schema Modernization
**Commit:** `199c3ab feat: add P54-P56 schema modernization and import gate`
`e36627f schema: regenerate canonical DDL (P56)`
- **Purpose:** Modernized database schema (DDL regeneration, import gates)
- **Still Exists:** Schema files in `schema/`, DDL artifacts
- **Obsolete:** The schema has been revised multiple times since
- **Current:** FUNCTIONS AS BASE SCHEMA for `production.db`

### P60–P61: Whiskybase Staging + Auto-Link
**Commit:** `bd1ddad feat: add P60 whiskybase staging and P61 auto-link tooling`
- **Purpose:** External source staging (whiskybase) and auto-linking tooling
- **Still Exists:** `output/p61a_migration/` directory
- **Obsolete:** Whiskybase pipeline was frozen (archive branch)
- **Current:** NOT ACTIVE

### P62–P69: KEP Foundation (Spec-Only)
**Commit(s):** Various early sprints, culminating in Sprint 1 architecture freeze
- **Purpose:** Define schemas, authority model, evidence ledger, extraction contracts, document qualification (spec-only)
- **Still Exists:** ALL — `authority/`, `schemas/`, `evidence/`, `extraction/`, `document_qualification/`, `resolution/`
- **Obsolete:** NONE — these are the frozen contracts that define the KEP architecture
- **Current:** ACTIVE as the architectural foundation

### P71–P73: KEP Implementation (Sprint 2)
**Commit(s):** Part of the Sprint 2 vertical slice
- **Purpose:** Implemented Qualification Engine (P71), Evidence Engine (P73), P68 state machine, certification engine
- **Still Exists:** `qualification_engine/`, `evidence_engine/`, `extraction_execution/`, `certification_engine/`, `pipeline/run.py`, `fixtures/`
- **Obsolete:** NONE — this is the canonical pipeline implementation
- **Current:** ACTIVE — the canonical KEP pipeline

### P91–P95: Production Hardening + Canonical Flavor
**Commit:** `ea13260 feat(kep): add P95 release readiness and P96 knowledge engineering architecture`
`497e6d1 feat(p95): add canonical flavor processing pipeline`
`b2930de feat(frontend): integrate canonical flavor pipeline`
`89fb4f4 feat(api): update DB API for canonical flavor support`
- **Purpose:** Production hardening (HttpFetcher, ContentCache), canonical 7-axis flavor certification (P95-A/B/C), P95 release readiness audit
- **Still Exists:** `acquisition/` (but with simulated components), `output/p95/`, `output/p95a/`, `output/p95b/`, `output/p95c/`
- **Obsolete:** The acquisition pipeline was **never de-simulated** — hardcoded telemetry values remain
- **Current:** PARTIALLY USED — canonical flavor standard is active in frontend/backend; acquisition pipeline is a simulation artifact

### P96–P98: Knowledge Engineering Pipeline
**Commit:** `597e48d feat(kep): add P96-P98 knowledge engineering pipeline`
- **Purpose:** Book PDF knowledge extraction, P97 promotion, P98 release
- **Still Exists:** `p96_pipeline/` (standalone extractor + resolver + consensus), `p97_promotion/`, `p98_promotion/`, `output/p96/`, `output/p97_promotion/`, `output/p98_release/`
- **Obsolete:** P96 has its OWN entity resolver, consensus engine, evidence graph — DUPLICATE of the main KEP pipeline's capabilities
- **Current:** SUPERSEDED by book enrichment sprint pattern; P96 code is standalone/parallel

### P102–P103: Immutable Knowledge Database
**Commit:** `1417f0b feat(p102): bootstrap immutable knowledge database`
`d7b2ab7 feat(p103): implement immutable knowledge database ingestion`
- **Purpose:** Created `knowledge.db` (SQLite schema), bootstrapped with book enrichment data, implemented ingestion
- **Still Exists:** `p102_bootstrap/` (schema, knowledge.db, certifier), `p103_corpus_audit/`, `p103_ingestion/`
- **Obsolete:** NONE — knowledge.db IS the active data store for enrichment results
- **Current:** ACTIVE — all book enrichment sprints target knowledge.db

### P117: Vinmonopolet Structured Source Intake
**Commit:** Not a single commit; output exists in `structured_source_intake/`
- **Purpose:** Retail CSV intake (Vinmonopolet, Alko, HTFW, WhiskyNotes) → entity resolution → promotion to knowledge.db
- **Still Exists:** `structured_source_intake/` directory with CSV outputs
- **Obsolete:** Standalone pipeline parallel to KEP
- **Current:** COMPLETED — data was promoted (39 new entities)

### P118–P120: SMWS Archive Processing
**Commit:** Not committed as single phases; outputs exist in phase directories
- **Purpose:** P118 = SMWS audit; P119 = SMWS deterministic extraction; P120 = SMWS promotion
- **Still Exists:** `p118_smws_audit/`, `p119_smws_extraction/`, `p119_5_validation/`, `p120_smws_promotion/`
- **Obsolete:** P119 extraction was a STANDALONE pipeline (not through KEP pipeline)
- **Current:** ORPHANED — P119 outputs exist as files only; P120 "promotion" never reached any database

---

## Key Architecture Milestones by Concept

| Concept | Introduced In | Current Location | Active? |
|---|---|---|---|
| **KnowledgeDB** | P102 (1417f0b) | `p102_bootstrap/knowledge.db` | ACTIVE |
| **KEP Pipeline** | P62–P69 spec + Sprint 2 | `pipeline/run.py` | ACTIVE |
| **Evidence** | P64 spec + P73 engine | `evidence/`, `evidence_engine/` | ACTIVE |
| **Consensus** | P96 pipeline | `p96_pipeline/consensus_engine.py` + book sprints | DUPLICATED |
| **Provenance** | P64 spec | `evidence/provenance_model.md` | ACTIVE |
| **Flavor Profiles** | P53 → P95 canonical | Frontend/backend canonical pipeline | ACTIVE |
| **7-Axis Mapping** | P95 canonical | D4 reducer, frontend/backend | ACTIVE |
| **Promotion** | P97→P98 | `p97_promotion/`, `p98_promotion/`, book sprints | DUPLICATED |
| **Staging** | P45–P52 era | Legacy archive | NOT ACTIVE |

# CHANGELOG — MR-KEP

All notable changes to MR-KEP are documented here. Format: keep-a-changelog
(Added / Changed / Removed / Fixed). Versioning follows the pipeline's
schema_version (`MAJOR.MINOR.PATCH`).

---

## [2.1.0] — 2026-07-22 — P500-P/Q Repository & Documentation Canonicalization

**Status: CLOSED**

### Changed
- `README.md` — full rewrite to reflect canonical architecture, PromotionGate, governance, and post-P500-O baseline
- `ROADMAP.md` — P500-N/O descriptions corrected; P500-P/Q description updated; stale labels fixed; footer updated
- `AGENTS.md` — expanded to include all 15 canonical governance rules
- `CHANGELOG.md` (root) — created; P500-A through P500-O entries added; P500-P/Q closure added
- `mr-kep/archive/ARCHIVE_MANIFEST.md` — extended with P500-A..O phase archive entries; P500-P/Q marked CLOSED
- `docs/ARCHITECTURE.md` — canonical repository structure + pipeline responsibility documentation
- `docs/pipeline/PIPELINE_OVERVIEW.md` — RETIRED banner added

### Closed
- Pipeline v1 → RETIRED
- MR-KEP → CANONICAL

---

## [2.0.0] — 2026-07-21 — P500 Canonical Pipeline Series

### P500-O — Production Promotion via PromotionGate (CLOSED)

**Production DB baseline shift:**
- Pre-apply SHA: `e9ef4702...` (2,881 flavor_evidence)
- Post-apply SHA: `40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0` (3,180 flavor_evidence)

#### Added
- 299 `flavor_evidence` rows promoted to production (source: `pipeline`)
- 661 total `staging_tasting_notes` now in promoted state

#### Held / Skipped
- 60 QR HOLD (quality rejected)
- 8 unresolved (entity resolution pending)
- 4 duplicate/overlap skips

---

### P500-N — QA Pre-Promotion Audit (CLOSED)

#### Added
- Full invariant check pass on staging_tasting_notes queue
- R4 violations: 0 (confirmed)
- Dedup check: passed
- evidence_id determinism: verified

---

### P500-M — EVIDENCE Pipeline (CLOSED)

#### Added
- `mr-kep/evidence/__init__.py`
- `mr-kep/evidence/evidence_mapper.py` — map normalized axes to evidence record
- `mr-kep/evidence/evidence_planner.py` — plan evidence insertions from staging
- `mr-kep/evidence/tests/` — evidence module tests
- Deterministic `evidence_id` generation: `sha256(whisky_id + source + axes_hash)`

---

### P500-L — CANONICALIZE Pipeline (CLOSED)

#### Added
- `mr-kep/canonicalize/` — canonicalization stage
- knowledge.db revival

---

### P500-K — NORMALIZE Pipeline (CLOSED)

#### Added
- `mr-kep/normalize/` — normalization stage
- Coverage expanded through canonical `flavor_mapper` in `d4_reducer/`

---

### P500-J — P42 Pending Row Resolution (CLOSED)

#### Changed
- P42 pending rows (371 PENDING) — resolved via P500-O promotion
- Classic P42 pipeline remains RETIRED

---

### P500-I — Real EXTRACT Implementation (CLOSED)

#### Added
- `mr-kep/extraction_engine/__init__.py`
- `mr-kep/extraction_engine/extractor.py` — real extraction logic
- `mr-kep/extraction_engine/extractors.py` — source-specific extractors
- `mr-kep/extraction_engine/extraction_record.py` — extraction record dataclass
- `mr-kep/extraction_engine/tests/`

#### Changed
- `extractor.py` — replaced fixture-only stub with real extraction logic

---

### P500-H — Real INGEST Implementation (CLOSED)

#### Added
- `mr-kep/acquisition/__init__.py`
- `mr-kep/acquisition/artifact_store.py`
- `mr-kep/acquisition/source_types.py`
- `mr-kep/acquisition/tests/`

#### Changed
- `mr-kep/acquisition/run_pipeline.py` — replaced hardcoded mocks with real ingest sources

---

### P500-G — Feature Branch → Main Merge (CLOSED)

#### Changed
- `feature/editorial-crawl-phase` merged into `main`
- Merge conflicts resolved

---

### P500-F — Canonical Invariant Registry (CLOSED)

#### Added
- `mr-kep/common/invariant_registry.yaml` — canonical QA invariant registry

---

### P500-E — Canonical PromotionGate (CLOSED)

#### Changed
- `kep_review_runtime/runtime/promotion_engine.py` — PromotionGate is now the ONLY authorized path to write `production.db`
- All bypass patterns from pre-canonical promotions are retired

---

### P500-D — KEP Runtime ↔ MR-KEP Integration (CLOSED)

#### Added / Changed
- KEP Runtime `promotion_engine.py` wired to `mr-kep/editorial/promotion/editorial_promotion_writer.py`
- Boundary rule: MR-KEP domain writers callable by KEP Runtime; domain writers never invoke runtime directly

---

### P500-C — Canonical Roadmap (CLOSED)

#### Added
- `ROADMAP.md` (root) — canonical single-source-of-truth roadmap

---

### P500-A / P500-B — Architecture Decision + Lifecycle Model (CLOSED)

#### Changed
- MR-KEP + KEP Runtime declared canonical architecture
- Classic P32-P42 declared RETIRED
- Canonical lifecycle model defined (DISCOVERY → ... → CLOSURE → ARCHIVE)

---

## [1.0.0] — Sprint 1 (FOUNDATION)

**Status:** Released (standards + skeleton only).

### Added
- Repository skeleton: `authority/`, `schemas/`, `manifests/`, `templates/`,
  `pipelines/`, `sources/`, `examples/`, `docs/`.
- Top-level docs: `README.md`, `AGENTS.md`, `HERMES.md`, `MERGE_STRATEGIES.md`,
  `CHANGELOG.md`, `ROADMAP.md`.
- Authority layer (5 files): `authority_matrix.yaml`, `source_priority.yaml`,
  `field_rules.yaml`, `confidence.yaml`, `merge_policies.yaml`.
- JSON Schemas (6 files): `manifest`, `qualification`, `extraction`,
  `normalization`, `certification`, `evidence`.
- Templates (4 files): `manifest.yaml`, `source_profile.yaml`,
  `merge_strategy.yaml`, `certification.yaml`.
- Docs (5 files): `architecture.md`, `lifecycle.md`, `authority_model.md`,
  `merge_strategy.md`, `glossary.md`.
- First source profile: `sources/whiskyfun/source_profile.yaml`.
- Six agent roles defined in `AGENTS.md` (Qualification, Extraction, Validation,
  Merge, Certification, Audit).

### Changed
- Nothing (initial foundation).

### Removed
- Nothing.

### Fixed
- Nothing.

---
*No scraper, parser, or extraction code was written in Sprint 1, by design.*

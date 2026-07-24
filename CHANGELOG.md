# CHANGELOG — Malt Radar

Production-level change history. Each entry corresponds to a completed,
verified production mutation with a closure report.

Format: [keep-a-changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Active
- (none — P500-P/Q completed)

### Remaining production queue
- 60 staging_tasting_notes QR HOLD — held for quality review
- 8 staging_tasting_notes unresolved — pending entity resolution or human decision
- 4 staging_tasting_notes duplicate/overlap skips — no action required
- Total: 72 rows remaining in staging queue

---

## [P500-P/Q] — 2026-07-22 — Pipeline v1 Retirement + Documentation Canonicalization

**Status: CLOSED**

### Closed
- Pipeline v1 → RETIRED. MR-KEP → CANONICAL.
- P500-P: Non-execution phase directories archived.
- P500-Q: ROADMAP, CHANGELOGs, ARCHIVE_MANIFEST, PIPELINE_OVERVIEW updated.
- All P500 series phases now CLOSED.

---

## [P500-O] — 2026-07-21 — Production Promotion (PromotionGate)

**Status: CLOSED**

### Production DB baseline shift
- **Pre-apply SHA:** `e9ef4702...` (2,881 flavor_evidence)
- **Post-apply SHA:** `40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0`

### Added
- 299 `flavor_evidence` rows promoted via canonical KEP Runtime PromotionGate
- Source: `pipeline` (MR-KEP canonical pipeline output)

### Held / Skipped
- 60 QR HOLD (quality rejected — held in staging for human review)
- 8 unresolved (entity resolution pending)
- 4 duplicate/overlap skips (deterministic dedup — no action needed)

### Verified production state post-apply
| Table | Count |
|-------|-------|
| whiskies | 4,749 |
| flavor_evidence | **3,180** (delta: +299) |
| flavor_profiles | 3,468 |
| tasting_notes | 1,852 |
| staging_tasting_notes | 733 (661 promoted, 72 remaining) |
| Tables total | 37 |

---

## [P500-N] — 2026-07-21 — QA (Pre-Promotion Audit)

**Status: CLOSED**

### Changed
- Full QA pass on staging_tasting_notes queue
- All canonical invariants verified (R4, dedup, evidence_id determinism)
- Promotion-readiness audit completed on 299 promotable rows

---

## [P500-M] — 2026-07-21 — EVIDENCE Pipeline

**Status: CLOSED**

### Added
- `mr-kep/evidence/` — Evidence record assembly module
- Deterministic `evidence_id` generation from (whisky_id, source, axes hash)
- Evidence planner + mapper wired into canonical pipeline

---

## [P500-L] — 2026-07-21 — CANONICALIZE Pipeline

**Status: CLOSED**

### Added
- `mr-kep/canonicalize/` — Canonical evidence_id generation stage
- Deterministic canonicalization from normalized axis values
- knowledge.db revival (P500-L scope)

---

## [P500-K] — 2026-07-21 — NORMALIZE Pipeline

**Status: CLOSED**

### Added
- `mr-kep/normalize/` — Field normalization stage
- Canonical flavor scale 0.0-1.0 enforcement
- Coverage expanded through canonical `flavor_mapper`

---

## [P500-J] — 2026-07-21 — P42 Pending Row Resolution

**Status: CLOSED**

### Changed
- P42 pending rows (371 PENDING + 362 approved) decision formalized
- Resolution: promote eligible rows via KEP Runtime PromotionGate in P500-O
- Classic P42 pipeline remains RETIRED; rows handled under canonical pipeline

---

## [P500-I] — 2026-07-21 — Real EXTRACT Implementation

**Status: CLOSED**

### Added
- `mr-kep/extraction_engine/extractor.py` — Real extraction logic (replacing test-only fixture)
- `mr-kep/extraction_engine/extractors.py` — Source-specific extractors
- `mr-kep/extraction_engine/extraction_record.py` — Extraction record schema
- `mr-kep/extraction_execution/` — EXTRACT orchestration layer

---

## [P500-H] — 2026-07-21 — Real INGEST Implementation

**Status: CLOSED**

### Added
- `mr-kep/acquisition/run_pipeline.py` — Real ingest sources (replacing hardcoded mocks)
- `mr-kep/acquisition/artifact_store.py` — Artifact persistence
- `mr-kep/acquisition/source_types.py` — Source type definitions
- `mr-kep/acquisition/tests/` — Acquisition test suite

---

## [P500-G] — 2026-07-21 — Feature Branch → Main Merge

**Status: CLOSED**

### Changed
- `feature/editorial-crawl-phase` merged into `main`
- Merge conflicts resolved
- Post-merge tests verified

---

## [P500-F] — 2026-07-21 — Canonical Invariant Registry

**Status: CLOSED**

### Added
- `mr-kep/common/invariant_registry.yaml` — Canonical QA invariant registry
- All QA checks reference the registry; no more per-phase ad-hoc invariant re-discovery

---

## [P500-E] — 2026-07-21 — Canonical PromotionGate

**Status: CLOSED**

### Added / Changed
- `kep_review_runtime/runtime/promotion_engine.py` — Made the ONLY authorized path to write `production.db`
- PromotionGate enforces: backup → SHA256 before → dry-run → human GO → apply → SHA256 after → verify
- All bypass patterns from historical promotions (P95B, P403/P404, P417) are now non-canonical

---

## [P500-D] — 2026-07-21 — KEP Runtime ↔ MR-KEP Integration

**Status: CLOSED**

### Added / Changed
- KEP Runtime `promotion_engine.py` wired to call `mr-kep/editorial/promotion/editorial_promotion_writer.py`
- Domain adapter: KEP Runtime invokes MR-KEP domain writers; domain writers never invoke runtime
- Boundary rule enforced: MR-KEP never writes production.db; KEP Runtime never contains domain logic

---

## [P500-C] — 2026-07-21 — Canonical Roadmap

**Status: CLOSED**

### Added
- `ROADMAP.md` (root) — canonical single-source-of-truth roadmap created
- Supersedes `mr-kep/ROADMAP.md`
- Reconciled all known phases, blockers, and decisions

---

## [P500-B] — 2026-07-21 — Canonical Lifecycle Model

**Status: CLOSED**

### Added
- Canonical lifecycle model: DISCOVERY → PLANNING → IMPLEMENTATION → STAGING → QA → GO/NO-GO → PROMOTION → VERIFICATION → CLOSURE → ARCHIVE
- Status definitions (CLOSED, ARCHIVED, BLOCKED, FAILED, SUPERSEDED, OBSOLETE, RETIRED)
- Transition rules (forward/backward, no skipping)

---

## [P500-A] — 2026-07-21 — Architecture Decision: MR-KEP + KEP Runtime Canonical

**Status: CLOSED**

### Changed
- MR-KEP + KEP Runtime declared canonical architecture
- Classic P32-P42 pipeline declared RETIRED
- Decision is CLOSED/DO-NOT-REOPEN (reopen threshold: Classic becomes runnable OR MR-KEP fatally flawed)

---

## Historical — Pre-P500 Production Mutations

> These promotions predate the canonical PromotionGate. They are historical
> exceptions, NOT canonical patterns. All future promotions must use PromotionGate.

### [P417] — 2026-07-20 — OCR Pipeline Promotion

- 1,831 `flavor_evidence` rows promoted (source: `ocr`)
- Pre-P417 baseline SHA: (see P417 closure report)
- Post-P417 baseline: 2,881 `flavor_evidence`

### [P403/P404] — 2026-07-20 — Books Promotion

- 64 `flavor_evidence` rows promoted (source: `book`)

### [P252] — 2026 — Entity Binding Apply

- 1,222 production writes (distillery_id binds + D1091→D0010 repoints)

### [P243] — 2026 — Single Editorial Apply

- 7 `flavor_evidence` rows promoted (source: `editorial`)

### [P239] — 2026 — R4 Normalization Fix

- 64 `flavor_evidence` rows corrected (axis values > 1.0 → normalized)
- 345 total axis fixes
- R4 violations after: 0

### [P95B Phase 12] — 2026-07-18 — Canonical Flavor Schema Migration

- 196 `flavor_evidence` rows promoted (source: `tasting_note`)
- 1 schema ALTER (canonical flavor schema)

### [P136-P149 SMWS] — 2026 — SMWS Pipeline Promotion

- 791 `flavor_evidence` rows promoted (source: `SMWS`)
- Knowledge bootstrap + SMWS metadata

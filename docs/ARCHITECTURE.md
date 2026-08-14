# Malt Radar — Canonical Architecture Reference

**Last updated:** P500-Q (2026-07-21)
**Status:** Canonical. Supersedes any older architecture descriptions.

---

## Overview

Malt Radar is a whisky discovery platform. Its data pipeline is built on two
canonical systems:

- **MR-KEP** — domain pipeline (data transformation, no production writes)
- **KEP Runtime** — execution + safety layer (orchestration, gating, production writes)

All future production promotion must go through **KEP Runtime PromotionGate**.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  KEP RUNTIME (execution layer)                │
│                                                              │
│  kep_review_runtime/runtime/                                 │
│  ├── scheduler.py       — queue scan, phase orchestration    │
│  ├── executor.py        — DryRunExecutor + RealExecutor      │
│  ├── promotion_engine.py— PromotionGate (ONLY write path)    │
│  ├── actions.py         — ActionPlan + action wrappers       │
│  ├── queue_manager.py   — computed review queues             │
│  ├── audit_writer.py    — audit logging to runtime.db        │
│  ├── dry_run.py         — dry-run runner + report            │
│  └── db_write_guard.py  — OS lock + write gating            │
│                                                              │
│  RESPONSIBILITY: orchestration, safety, gating, audit        │
│  NEVER: domain logic, LLM inference, PDF parsing            │
└─────────────────────────┬────────────────────────────────────┘
                          │ calls / invokes domain writers
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  MR-KEP (domain pipeline layer)               │
│                                                              │
│  mr-kep/                                                     │
│  ├── acquisition/         — INGEST stage                     │
│  ├── extraction_engine/   — EXTRACT stage (engine)           │
│  ├── extraction_execution/— EXTRACT stage (orchestration)    │
│  ├── normalize/           — NORMALIZE stage                  │
│  ├── d4_reducer/          — NORMALIZE + CANONICALIZE (axes)  │
│  ├── canonicalize/        — CANONICALIZE (evidence_id)       │
│  ├── evidence/            — EVIDENCE assembly                │
│  ├── qa/                  — QA + pre-promotion audit         │
│  ├── common/              — shared utils + invariant registry│
│  └── archive/             — historical non-execution phases  │
│                                                              │
│  RESPONSIBILITY: domain data transformation logic            │
│  NEVER: write production.db directly                        │
└─────────────────────────┬────────────────────────────────────┘
                          │ writes to (via PromotionGate only)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  STORAGE LAYER                                │
│                                                              │
│  output/import/production.db   canonical source of truth    │
│  staging_* tables              in production.db             │
│  backups/                      pre-apply snapshots          │
│  kep_review_runtime/runtime.db KEP Runtime audit log        │
└──────────────────────────────────────────────────────────────┘
```

---

## Canonical Pipeline Stages

### INGEST — `mr-kep/acquisition/`

**Responsibility:** Detect and fetch changes from external sources.

| File | Role |
|------|------|
| `run_pipeline.py` | Pipeline entry point — orchestrates fetch |
| `artifact_store.py` | Persist fetched artifacts |
| `source_types.py` | Source type definitions |

**Output:** Raw fetched artifacts, change detection signals.

**Rules:**
- Never writes production.db.
- Uses change detection to avoid re-fetching unchanged sources.
- Artifacts stored to disk, not directly to DB.

---

### EXTRACT — `mr-kep/extraction_engine/` + `extraction_execution/`

**Responsibility:** Parse raw source artifacts and extract structured field values
with verbatim quotes.

| File | Role |
|------|------|
| `extractor.py` | Core extraction logic |
| `extractors.py` | Source-specific extractors |
| `extraction_record.py` | Extraction record dataclass |

**Output:** Extraction records — raw field values with provenance.

**Rules:**
- Every extracted field must carry a verbatim `quote` from the source.
- If a field is not present in the source, emit `null`. Never invent.
- No normalization at this stage.

---

### NORMALIZE — `mr-kep/normalize/` + `d4_reducer/`

**Responsibility:** Normalize raw field values to canonical scale and format.

| File | Role |
|------|------|
| `normalize/` | Field normalization stage |
| `d4_reducer/flavor_mapper.py` | Flavor category → axis mapping |
| `d4_reducer/axis_reducer.py` | Reduce to canonical 7-axis model |
| `common/flavor_scale_utils.py` | Scale normalization utilities |

**Output:** Normalized records — all axis values in `[0.0, 1.0]`.

**Rules:**
- All flavor axis values must be in range `[0.0, 1.0]` (R4 contract).
- Canonical axes: fruity, sweet, spicy, smoky, oak, malty, floral.
- No axis value may exceed 1.0 or be below 0.0.

---

### CANONICALIZE — `mr-kep/canonicalize/` + `d4_reducer/`

**Responsibility:** Generate deterministic `evidence_id` from normalized evidence.

**Output:** Canonicalized evidence record with deterministic ID.

**Rules:**
- `evidence_id` = `sha256(whisky_id + source + axes_hash)`.
- Same input always produces the same `evidence_id`.
- If `evidence_id` already exists in production — INSERT is a no-op (idempotent).

---

### EVIDENCE — `mr-kep/evidence/`

**Responsibility:** Assemble final evidence records for promotion.

| File | Role |
|------|------|
| `evidence_planner.py` | Plan which evidence rows to insert |
| `evidence_mapper.py` | Map normalized axes to evidence record schema |

**Output:** Evidence batch ready for QA.

**Rules:**
- Evidence is INSERT-only. Never UPDATE or DELETE existing rows.
- Each record has a deterministic `evidence_id`.

---

### QA — `mr-kep/qa/` + `kep_review_runtime/runtime/dry_run.py`

**Responsibility:** Verify evidence batch against canonical invariants before
promotion is proposed.

**Invariants (from `mr-kep/common/invariant_registry.yaml`):**

| Invariant | Check |
|-----------|-------|
| R4 | All axis values in `[0.0, 1.0]` |
| R5 | No duplicate `(whisky_id, source)` in flavor_evidence |
| R6 | `evidence_id` determinism — same input → same ID |
| R7 | No orphaned evidence — whisky_id must exist in whiskies |
| R8 | staging_tasting_notes status transitions are one-way |

**Output:** QA report — GO / NO-GO / HOLD per evidence row.

**Rules:**
- QA must run before any promotion is proposed to the human.
- Any R4 violation → entire batch is NO-GO.
- Dry-run must match QA output exactly.

---

### HUMAN GO/NO-GO

**Responsibility:** Human authorization for production promotion.

**Rules:**
- Dry-run output + QA report must be presented to human.
- Human must explicitly respond GO.
- No autonomous apply without GO.
- GO is valid for one session only. A new session requires a new GO.

---

### PromotionGate — `kep_review_runtime/runtime/promotion_engine.py`

**Responsibility:** The ONLY authorized path to write `production.db`.

**Protocol:**

```
1. Receive human GO token
2. Create backup of production.db
3. Record SHA256 BEFORE apply
4. Apply evidence batch (INSERT-only, SAVEPOINT safety)
5. Record SHA256 AFTER apply
6. Verify row counts match dry-run predictions
7. Verify R4 invariants on newly inserted rows
8. If verification fails → ROLLBACK to backup
9. Write audit log entry to runtime.db
```

**Rules:**
- No bypass. PromotionGate is the ONLY write path.
- SAVEPOINT safety — partial failures roll back atomically.
- SHA256 before/after is mandatory.
- Backup is mandatory.

---

### VERIFY

**Responsibility:** Post-apply verification.

Checks:
- Row count delta matches prediction.
- SHA256 after matches expectation.
- R4 violations: 0.
- No duplicate `(whisky_id, source)`.
- Audit log entry written.

If any check fails → rollback → closure report records failure.

---

### CLOSURE

**Responsibility:** Document the completed promotion.

Closure artifact must contain:
- Phase ID
- Pre-apply SHA256
- Post-apply SHA256
- Promoted count
- Held / skipped counts
- Verification status
- Human GO record (session, date)

---

## Repository Structure

```
malt radar CLEAN/
│
├── README.md                      Project overview + current status
├── ROADMAP.md                     Canonical single-source-of-truth roadmap
├── AGENTS.md                      Agent governance rules (15 rules)
├── CHANGELOG.md                   Production-level change history
│
├── mr-kep/                        Canonical domain pipeline
│   ├── acquisition/               INGEST — source fetch + change detection
│   ├── extraction_engine/         EXTRACT — parsing + field extraction
│   ├── extraction_execution/      EXTRACT — orchestration
│   ├── normalize/                 NORMALIZE — field normalization
│   ├── d4_reducer/                NORMALIZE + CANONICALIZE — axis reduction
│   ├── canonicalize/              CANONICALIZE — evidence_id generation
│   ├── evidence/                  EVIDENCE — record assembly
│   ├── qa/                        QA — invariant checks
│   ├── common/                    Shared utils + invariant_registry.yaml
│   ├── archive/                   Historical closed non-execution phases
│   │   └── ARCHIVE_MANIFEST.md    Phase archive index
│   ├── CHANGELOG.md               MR-KEP change history
│   ├── AGENTS.md                  MR-KEP agent role definitions
│   └── CANONICAL_SCHEMA.md        Canonical DB schema reference
│
├── kep_review_runtime/            KEP Runtime — execution + safety layer
│   ├── runtime/                   Core runtime modules
│   │   ├── promotion_engine.py    PromotionGate (ONLY production write path)
│   │   ├── executor.py            DryRunExecutor + RealExecutor
│   │   ├── scheduler.py           Queue scan + orchestration
│   │   ├── actions.py             ActionPlan + wrappers
│   │   ├── queue_manager.py       Review queue computation
│   │   ├── audit_writer.py        Audit logging
│   │   ├── dry_run.py             Dry-run runner
│   │   ├── db_write_guard.py      OS lock + write gating
│   │   └── run.py                 Main orchestrator entry point
│   └── tests/                     Runtime test suite
│
├── output/
│   └── import/
│       └── production.db          Production SQLite DB (canonical source of truth)
│
├── frontend/                      Flutter app (Riverpod + Drift)
├── backend/                       FastAPI backend
├── data/                          Datasets and working data
├── schema/                        Database schema definitions
├── docs/                          Project documentation
│   ├── ARCHITECTURE.md            This file
│   ├── PIPELINE.md                Pipeline documentation
│   └── PROJECT_MAP.md             Project map
├── reports/                       Audit and validation reports
├── tests/                         Backend and pipeline tests
├── rules/                         Operating rules
├── workflows/                     Workflow definitions
└── memory/                        Project memory (architecture, decisions, etc.)
```

---

## Boundary Rules (absolute)

| Rule | Description |
|------|-------------|
| MR-KEP NEVER writes production.db | All production mutations go through KEP Runtime PromotionGate |
| KEP Runtime NEVER contains domain logic | No flavor mapping, no entity resolution in runtime/ |
| All future promotion MUST use PromotionGate | Pre-P500 direct writes are historical exceptions, NOT canonical |
| Evidence INSERT-only | Never UPDATE or DELETE existing flavor_evidence rows |
| Human GO required | No autonomous production apply |

---

## Current Production Baseline (post-P500-O)

| Metric | Value |
|--------|-------|
| SHA256 | `40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0` |
| Tables | 37 |
| Whiskies | 4,749 |
| flavor_evidence | 3,180 |
| Remaining staging queue | 72 (60 QR HOLD + 8 unresolved + 4 duplicate/overlap) |

---

## Historical / Retired

### Classic Pipeline P32-P42 — RETIRED

Not runnable. Entry scripts never committed. No revival planned.

P500-A decision (CLOSED/DO-NOT-REOPEN): Classic pipeline retired.
All future investment goes to MR-KEP + KEP Runtime.

See `ROADMAP.md` Section 11 for the full retired appendix.

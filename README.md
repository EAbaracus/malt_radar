# Malt Radar

Whisky discovery platform combining flavor intelligence with a structured
whisky database. Browse distilleries, search the catalog, inspect detailed
whisky profiles, and visualize each expression on a Flavor Radar with
similar-whisky recommendations.

---

## Features

- **Whisky discovery** — browse and surface whiskies from a structured catalog.
- **Distillery exploration** — inspect distilleries and their expressions.
- **Search** — find whiskies by name, distillery, or attribute.
- **Whisky profiles** — detailed per-expression data and metadata.
- **Flavor Radar** — visualize a whisky's flavor signature across seven axes.
- **Similar whisky recommendations** — find expressions that taste alike.

### Flavor Radar axes

| Axis | Description |
|------|-------------|
| Fruity | Stone fruit, tropical, orchard |
| Sweet | Honey, vanilla, toffee |
| Spicy | Pepper, ginger, spice |
| Smoky / Peaty | Peat, smoke, medicinal |
| Oak / Cask | Wood, tannin, cask influence |
| Malty / Cereal | Grain, biscuit, malt |
| Floral / Herbal | Floral, grassy, herbal |

---

## Architecture

| Layer | Technology |
|-------|------------|
| Frontend | Flutter (Riverpod + Drift/SQLite) |
| Backend API | FastAPI (Python) |
| Data pipeline | MR-KEP + KEP Runtime |
| Production DB | SQLite (`output/import/production.db`) |

---

## Canonical Data Pipeline — MR-KEP + KEP Runtime

**MR-KEP** (domain pipeline) and **KEP Runtime** (execution / safety layer)
are the canonical production data path. Classic P32-P42 is **RETIRED** (see
Historical / Retired section).

### Pipeline stages

```
INGEST          mr-kep/acquisition/
    ↓
EXTRACT         mr-kep/extraction_engine/ + extraction_execution/
    ↓
NORMALIZE       mr-kep/normalize/ + d4_reducer/
    ↓
CANONICALIZE    mr-kep/canonicalize/ + d4_reducer/axis_reducer.py
    ↓
EVIDENCE        mr-kep/evidence/
    ↓
QA              mr-kep/qa/ + kep_review_runtime/runtime/dry_run.py
    ↓
HUMAN GO/NO-GO  — explicit human authorization required —
    ↓
PromotionGate   kep_review_runtime/runtime/promotion_engine.py
    ↓
VERIFY          SHA before/after + row count check
    ↓
CLOSURE         closure report written, phase marked CLOSED
```

### Responsibilities

| Module | Stage | Writes production? |
|--------|-------|--------------------|
| `mr-kep/acquisition/` | INGEST — fetch/detect source changes | ❌ Never |
| `mr-kep/extraction_engine/` | EXTRACT — parse raw fields + verbatim quotes | ❌ Never |
| `mr-kep/extraction_execution/` | EXTRACT orchestration | ❌ Never |
| `mr-kep/normalize/` | NORMALIZE — field normalization, scale 0.0-1.0 | ❌ Never |
| `mr-kep/d4_reducer/` | NORMALIZE + CANONICALIZE — axis reduction | ❌ Never |
| `mr-kep/canonicalize/` | CANONICALIZE — deterministic evidence_id generation | ❌ Never |
| `mr-kep/evidence/` | EVIDENCE — evidence record assembly | ❌ Never |
| `mr-kep/qa/` | QA — invariant checks, pre-promotion audit | ❌ Never |
| `mr-kep/common/` | Shared utilities, invariant registry | ❌ Never |
| `kep_review_runtime/runtime/promotion_engine.py` | PromotionGate — **ONLY** production write path | ✅ Authorized only |

---

## Production DB Governance

### Evidence INSERT-only policy

- Existing `flavor_evidence` rows are **never** UPDATE'd or DELETE'd.
- New evidence is INSERT'd with a deterministic `evidence_id`.
- Production mutations happen **only** via authorized `PromotionGate` flow.
- Every production write requires: backup + SHA256 before → dry-run → human GO → apply → SHA256 after → verify → closure report.

### Production DB protection rules

1. No direct SQL writes to `production.db`.
2. No experimental or ad-hoc mutations.
3. Every mutation needs a new authorized phase with its own closure record.
4. Backup is mandatory before every apply.
5. SHA256 must be captured before AND after apply.
6. Failed verification triggers rollback.

---

## QA / Invariant Model

Invariants are defined in `mr-kep/common/invariant_registry.yaml`.

Key invariants:

- All flavor axis values in range `[0.0, 1.0]` (R4 contract).
- No duplicate `(whisky_id, source)` in `flavor_evidence`.
- `evidence_id` is deterministic — same input always produces same ID.
- No orphaned `flavor_evidence` (whisky_id must exist in `whiskies`).
- `staging_tasting_notes` status transitions are one-way.

---

## Current Project Status

| Metric | Value |
|--------|-------|
| Production DB SHA | `40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0` |
| Tables | 37 |
| Whiskies | 4,749 |
| flavor_evidence rows | 3,180 |
| Evidence coverage | 2,924 / 4,749 whiskies (61.6%) |
| staging_tasting_notes total | 733 |
| staging_tasting_notes promoted | 661 |
| Remaining active queue | **72** (60 QR HOLD + 8 unresolved + 4 duplicate/overlap skips) |
| NULL distillery_id | 724 / 4,749 (15.2%) |

### P500-O — CLOSED

Last production promotion:

| Item | Count |
|------|-------|
| Promoted to production | 299 |
| QR HOLD (quality rejected) | 60 |
| Unresolved | 8 |
| Duplicate / overlap skips | 4 |
| **Remaining staging queue** | **72** |

Pre-P500-O baseline: 2,881 `flavor_evidence`, SHA `e9ef4702...`
Post-P500-O baseline: 3,180 `flavor_evidence`, SHA `40b7f71e...`

---

## Development

### Flutter (frontend)

```bash
flutter pub get
flutter test
flutter build apk --release
```

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Backend serves on port `8080` by default (override with `PORT` env var).

### MR-KEP / KEP Runtime (data pipeline)

```bash
# Run KEP Runtime dry-run (read-only, no production writes)
cd kep_review_runtime
python run.py --dry-run

# Run MR-KEP tests
cd mr-kep
python -m pytest tests/ -v

# Run KEP Runtime tests
cd kep_review_runtime
python -m pytest tests/ -v
```

---

## Repository Structure

```
malt radar CLEAN/
├── frontend/            Flutter app (Riverpod + Drift)
├── backend/             FastAPI backend
├── mr-kep/              Canonical domain pipeline (MR-KEP)
│   ├── acquisition/       INGEST — source detection/fetching
│   ├── extraction_engine/ EXTRACT — parsing + field extraction
│   ├── extraction_execution/ EXTRACT orchestration
│   ├── normalize/         NORMALIZE — field normalization
│   ├── d4_reducer/        NORMALIZE + CANONICALIZE — axis reduction
│   ├── canonicalize/      CANONICALIZE — deterministic evidence_id
│   ├── evidence/          EVIDENCE — evidence record assembly
│   ├── qa/                QA — invariant checks, pre-promotion audit
│   ├── common/            Shared utilities + invariant_registry.yaml
│   └── archive/           Historical closed phases (non-canonical)
├── kep_review_runtime/  KEP Runtime — execution + safety layer
│   ├── runtime/           promotion_engine, executor, audit_writer, dry_run
│   └── tests/             Runtime test suite
├── output/
│   └── import/
│       └── production.db  Production SQLite DB (canonical source of truth)
├── data/                Datasets and working data
├── schema/              Database schema definitions
├── docs/                Pipeline and project documentation
├── reports/             Audit and validation reports
├── tests/               Backend and pipeline tests
├── rules/               Operating rules
├── workflows/           Workflow definitions
└── memory/              Project memory
```

---

## Canonical Architecture

```
┌──────────────────────────────────────────────────────────┐
│              KEP RUNTIME (execution layer)                │
│  scheduler → executor → actions → db_write_guard         │
│  promotion_engine → dry_run → queue_manager              │
│  audit_writer → runtime.db                               │
│  RESPONSIBILITY: orchestration, safety, gating, audit    │
│  NEVER: domain logic, LLM inference, PDF parsing         │
└─────────────────────┬────────────────────────────────────┘
                      │ calls / invokes
                      ▼
┌──────────────────────────────────────────────────────────┐
│              MR-KEP (domain pipeline layer)               │
│  INGEST → EXTRACT → NORMALIZE → CANONICALIZE             │
│  → EVIDENCE → QA                                         │
│  RESPONSIBILITY: domain data transformation logic        │
│  NEVER: write production.db directly                     │
└─────────────────────┬────────────────────────────────────┘
                      │ writes to (via PromotionGate only)
                      ▼
┌──────────────────────────────────────────────────────────┐
│              STORAGE LAYER                                │
│  output/import/production.db  (canonical source of truth)│
│  staging_* tables             (in production.db)         │
│  backups/                     (pre-apply snapshots)      │
└──────────────────────────────────────────────────────────┘
```

---

## Governance Rules

1. **MR-KEP is never** allowed to write `production.db` directly.
2. **All production promotion MUST use** `kep_review_runtime/runtime/promotion_engine.py`.
3. **Evidence INSERT-only** — no UPDATE or DELETE on existing `flavor_evidence`.
4. **Human GO/NO-GO required** before every `PromotionGate.apply()`.
5. **Backup + SHA256 verification** required before and after every apply.
6. **Dry-run before apply** — mandatory.
7. **Failed verification triggers rollback** — no silent failures.
8. **Closure artifact required** — every phase must produce a closure report.
9. **Staging-first** — all experimental work lands in staging, never directly in production.
10. **Commit/push only with explicit human authorization**.

---

## Next Work

| Priority | Work | Status |
|----------|------|--------|
| Active | P500-P/Q — Repository & documentation canonicalization | **IN PROGRESS** |
| Open | Remaining 72-row staging queue (60 QR HOLD + 8 unresolved + 4 skips) | Held for human review |
| Open | 724 NULL distillery_id resolution | Deliberate exclusions + 13 manual-review collisions |
| Blocked | Real INGEST/EXTRACT adapters (acquisition/ uses hardcoded mocks) | Implementation needed |

---

## Release Pipeline

CI runs on push to `main` and on version tags (`v*`):

```
push main / tag v*
    ↓
flutter pub get
    ↓
flutter test
    ↓
flutter build apk --release
    ↓
GitHub Artifact
    ↓
GitHub Release (tag)
    ↓
Google Drive upload (when GOOGLE_DRIVE_CREDENTIALS + GOOGLE_DRIVE_FOLDER_ID set)
```

See `.github/workflows/android-release.yml`.

---

## Historical / Retired

### Classic Pipeline P32-P42 — RETIRED

The classic pipeline (P32-P42) is **retired and not runnable**:

- P36-P42 entry point scripts were **never committed** to the repository.
- Data formats (CSV-based staging, manual review CSVs) superseded by MR-KEP evidence model.
- **No revival planned.** All future investment goes to MR-KEP + KEP Runtime.
- Outputs retained as historical evidence only (`output/p36/` through `output/p42/`).

The 733 `staging_tasting_notes` rows in production.db are a legacy of P39 (classic pipeline).
661 are promoted; 72 remain as the active review queue (see Current Status above).
The classic pipeline cannot promote these — promotion must go through KEP Runtime PromotionGate.

### Pre-P500 Promotion History (non-canonical patterns)

| Phase | Rows | Note |
|-------|------|------|
| P136-P149 SMWS | 791 flavor_evidence | Historical — direct write, pre-canonical |
| P95B Phase 12 | 196 flavor_evidence | Historical — direct write, pre-canonical |
| P403/P404 Books | 64 flavor_evidence | Historical — direct write, pre-canonical |
| P417 OCR | 1,831 flavor_evidence | Historical — direct write, pre-canonical |
| P243 Editorial | 7 flavor_evidence | Historical — direct write, pre-canonical |
| P252 Entity Binding | 1,222 distillery writes | Historical — direct write, pre-canonical |
| P239 R4 Normalization | 64 rows fixed | Historical — direct write, pre-canonical |

These are **historical exceptions, NOT canonical patterns**. All future promotions must use KEP Runtime PromotionGate.

---

## Documentation

- `ROADMAP.md` — canonical roadmap (single source of truth)
- `AGENTS.md` — agent operating instructions and governance rules
- `CHANGELOG.md` — production-level change history
- `mr-kep/CHANGELOG.md` — MR-KEP pipeline change history
- `docs/PIPELINE.md` — pipeline documentation
- `docs/PROJECT_MAP.md` — project map
- `docs/ARCHITECTURE.md` — canonical architecture reference
- `mr-kep/archive/ARCHIVE_MANIFEST.md` — archived historical phases
- `mr-kep/common/invariant_registry.yaml` — canonical QA invariants

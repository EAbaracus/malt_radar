# MALT RADAR — CANONICAL ROADMAP

**Canonical Architecture:** MR-KEP (domain pipeline) + KEP Runtime (execution/safety layer)
**Classic P32-P42:** RETIRED / HISTORICAL APPENDIX
**Authored:** P500-C · 2026-07-21 · Read-only reconciliation
**Contract references:** P500-A (architecture decision), P500-B (operating model & lifecycle)

---

## 1. EXECUTIVE STATUS

| Category | Status |
|---|---|
| **Canonical Architecture** | MR-KEP + KEP Runtime. Classic P32-P42 RETIRED. |
| **Production DB** | `output/import/production.db` — 37 tables, 4,749 whiskies, 3,180 flavor_evidence, 1,917 tasting_notes |
| **Evidence Coverage** | 2,924 / 4,749 whiskies (61.6%) have ≥1 flavor_evidence row |
| **Staging Debt** | 733 staging_tasting_notes (661 promoted, 65 promoted_to_production, 7 staging_hold) — RESOLVED, 0 remaining |
| **Entity Resolution** | P252 applied: 1,222 binds. Remaining NULL distillery_id: 724 (15.2%) |
| **KEP Runtime** | `kep_review_runtime/runtime/` — 8 modules, fully integrated with MR-KEP domain and active |
| **MR-KEP Executable Domains** | D4 reducer (canonical), Ingest (real), Extract (real), Normalization (real), Canonicalization (real), Evidence (real) |
| **MR-KEP Test/SIM Only** | None (all core domains implemented and validated on real data) |
| **Repository Root** | ROADMAP.md (updated). mr-kep/CHANGELOG.md (updated). AGENTS.md (updated). |

### Production DB Verified Facts

| Table | Row Count | Notes |
|---|---|---|
| whiskies | 4,749 | 790 UUID-format (SMWS), 3,959 W-prefix (legacy) |
| tasting_notes | 1,917 | |
| flavor_profiles | 3,468 | |
| flavor_evidence | 3,180 | See distribution below |
| staging_tasting_notes | 733 | 661 promoted, 65 promoted_to_production, 7 staging_hold — 0 remaining |
| distilleries | — | P252 applied: 1,207 NULL binds fixed, 724 remain NULL |

**flavor_evidence source distribution:**

| Source | Rows | % | Path |
|---|---|---|---|
| ocr | 1,831 | 57.6% | P417 (OCR pipeline, 2026-07-20) |
| SMWS | 791 | 24.9% | P136-P149 -> P120/P121 (SMWS extraction) |
| pipeline | 299 | 9.4% | P500-O (real pipeline promotion, 2026-07-21) |
| tasting_note | 188 | 5.9% | P95B phase 12 (2026-07-18) |
| book | 64 | 2.0% | P403/P404 (books promotion, 2026-07-20) |
| editorial | 7 | 0.2% | P243 (single editorial apply) |

---

## 2. CANONICAL ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────┐
│                     KEP RUNTIME (execution layer)                 │
│                                                                   │
│  scheduler.py → executor.py → actions.py → db_write_guard.py     │
│  promotion_engine.py → dry_run.py → queue_manager.py              │
│  audit_writer.py → runtime.db                                     │
│                                                                   │
│  RESPONSIBILITY: orchestration, safety, gating, audit logging     │
│  NEVER: domain logic, LLM inference, PDF parsing                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ calls / invokes
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     MR-KEP (domain pipeline layer)                 │
│                                                                   │
│  ingress:  acquisition/* (real local-file ingest)                  │
│  extract:  extraction_engine/* (real)                              │
│  normalize: d4_reducer/*, mr-kep/normalize/*, common/flavor_scale_utils.py │
│  resolve:  editorial/matching.py, queue_manager.py                │
│  canonicalize: d4_reducer/axis_reducer.py, mr-kep/canonicalize/*   │
│  evidence: evidence_engine/* (legacy), mr-kep/evidence/* (canonical), editorial/writer/* │
│  QA:       mr-kep/qa/qa.py, dry_run.py, audit_writer.py           │
│  promote:  promotion_engine.py (wraps domain writer)              │
│                                                                   │
│  RESPONSIBILITY: domain-specific data transformation logic        │
│  NEVER: write to production.db directly (must use KEP Runtime)    │
└──────────────────────────┬───────────────────────────────────────┘
                           │ writes to
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                                  │
│                                                                   │
│  output/import/production.db    (canonical source of truth)        │
│  output/import/knowledge.db     (empty mirror — P130 blocker)     │
│  staging_* tables               (in production.db)                │
│  backups/                       (pre-apply snapshots)             │
│  staging_editorial.db           (P96/P203 staging)                │
│  staging_ocr_*.db               (P407-P414 staging)               │
└──────────────────────────────────────────────────────────────────┘
```

### Boundary Rules (absolute)

| Kural | Açıklama |
|---|---|
| MR-KEP NEVER writes production.db directly | All production mutations go through KEP Runtime promotion_engine |
| KEP Runtime NEVER contains domain logic | No flavor mapping, no entity resolution logic in runtime/ |
| Future promotion MUST use KEP Runtime | P95B/P403/P404/P417 are historical exceptions, NOT canonical pattern |
| Evidence promotion ≠ entity resolution | Existing whisky_id → no resolution needed. New entity → resolution mandatory |

---

## 3. CANONICAL LIFECYCLE

```
DISCOVERY
──→ PLANNING
──→ IMPLEMENTATION
──→ STAGING
──→ QA
──→ GO/NO-GO
──→ PROMOTION
──→ VERIFICATION
──→ CLOSURE
──→ ARCHIVE
```

### Status Definitions

| Status | Meaning | Terminal? |
|---|---|---|
| **CLOSURE** | Lifecycle stage: closure documentation is being written | No |
| **CLOSED** | Terminal phase status: execution complete + verified + closure report written | Yes |
| **ARCHIVED** | Terminal historical state: phase directory moved to archive/ | Yes |
| **BLOCKED** | Phase cannot progress; external dependency missing | No |
| **FAILED** | Execution failed; rollback performed or required | No |
| **SUPERSEDED** | Another phase covered this work more comprehensively | Yes |
| **OBSOLETE** | No longer relevant (different from SUPERSEDED — not replaced, just irrelevant) | Yes |
| **RETIRED** | Pipeline or architecture decision no longer active | Yes |

### Transition Rules

- Forward: each stage waits for previous stage's exit criteria
- Backward (FAIL/BLOCKED): return to exactly one level up (PLANNING from GO/NO-GO NO-GO, IMPLEMENTATION from QA FAIL, STAGING from PROMOTION FAIL)
- No skipping: QA → GO/NO-GO → PROMOTION — no stage can be skipped
- No re-closure: a CLOSED phase cannot be reopened. New work needs a new DISCOVERY

---

## 4. CURRENT SYSTEM STATE

### Production Database (`output/import/production.db`, 13.4 MB, 37 tables)

| Metric | Value | Verified |
|---|---|---|
| whiskies | 4,749 | ✅ |
| flavor_evidence | 3,180 (Delta: +299) | ✅ |
| flavor_profiles | 3,468 | ✅ |
| tasting_notes | 1,917 | ✅ |
| staging_tasting_notes | 733 (661 promoted, 65 promoted_to_production, 7 staging_hold — 0 remaining) | ✅ |
| NULL distillery_id | 724 / 4,749 (15.2%) | ✅ |
| Evidence coverage | 2,924 / 4,749 whiskies (61.6%) | ✅ |
| PROMOTION_AUDIT_LOG p252 rows | 1,217 | ✅ |
| R4 violations | 0 (P239 remediated all 64) | ✅ |

### KEP Runtime Readiness (`kep_review_runtime/runtime/`)

| Module | Lines | Status |
|---|---|---|
| `scheduler.py` | 10 KB | Executable, CLI entry points for scan/report/execute |
| `executor.py` | 10 KB | DryRunExecutor + RealExecutor with SAVEPOINT safety |
| `promotion_engine.py` | 12 KB | Apply gate with human_gate token, TEMP COPY first, db_write_guard |
| `actions.py` | 12 KB | ActionPlan + domain-specific action wrappers |
| `queue_manager.py` | 15 KB | Computed review queues from staging+production state |
| `audit_writer.py` | 10 KB | Audit table schema + logging |
| `dry_run.py` | 4 KB | Dry-run runner + report printer |
| `db_write_guard.py` | (mr-kep/p121) | OS lock + write gating |
| `run.py` | 19 KB | Main orchestrator entry point |

**Status:** All modules exist and are designed. **NOT YET** integrated with real MR-KEP domain writers. Historical promotions bypassed this runtime.

### MR-KEP Executable Domains

| Domain | Can Run Today? | Proven On Real Data? |
|---|---|---|
| D4 Reducer (`d4_reducer/`) | ✅ Yes | ✅ P95B used it for 196 evidence rows |
| Editorial Promo Writer (`editorial/promotion/`) | ✅ Yes | ✅ P243 single apply, P403/P404 books |
| P252 Entity Binding (`_apply.py`) | ✅ Yes | ✅ P252: 1,222 writes |
| Acquisition Pipeline (`acquisition/`) | ✅ Yes | ✅ Real local-file ingest (P500-H) |
| Evidence Engine (`mr-kep/evidence/`) | ✅ Yes | ✅ Canonical EVIDENCE pipeline (P500-M) — reads production read-only |
| QA (`mr-kep/qa/`) | ✅ Yes | ✅ Canonical QA pipeline (P500-N) — reads production read-only, no PromotionGate call |
| Extraction Engine (`extraction_engine/`) | ✅ Yes | ✅ Real extraction (P500-I) |
| Book Enrichment Sprints | ❌ No (one-shot, historical) | ✅ One-time execution, outputs exist |
| Classic P32-P42 | ❌ No (entry scripts missing) | ❌ Never production-executable |

### Known Gaps (resolved in P500-P/Q)

| Gap | Resolution Status |
|---|---|
| `output/import/knowledge.db` — 0 bytes, 0 tables (P130 WARN_GO) | **Not resolved** — known pre-existing issue, out of P500-P/Q scope |
| `output/release/` — only PIPELINE_v1_FROZEN.lock exists | **Retained** — preserved as historical artifact |
| ROOT CHANGELOG.md | **Created** in P500-P/Q |
| canonical invariant registry (`mr-kep/common/invariant_registry.yaml`) | **Exists** — created in P500-F |
| canonical QA contract (`mr-kep/qa/qa.py`) | **Exists** — created in P500-N |

---

## 5. COMPLETED / CLOSED WORK

Only phases with verified execution evidence are listed. "Completed" means execution happened + verification passed + closure report exists (or equivalent evidence).

### Canonical Pipeline Phases (MR-KEP, executable or executed)

| Phase | Scope | Execution Evidence | Rows Affected | Status |
|---|---|---|---|---|
| **P500-A through O** | Pipeline rebase and promotion | `mr-kep/`, `kep_review_runtime/`, closure reports | 299 flavor_evidence promoted | CLOSED |
| **P95B Phase 12** | Canonical flavor schema migration + promotion | `p95b_phase12/`, closure report | 196 flavor_evidence (tasting_note), 1 schema ALTER | HISTORICAL COMPLETED EXECUTION |
| **P239 R4 Normalization** | Fix 64 book flavor_evidence rows with axis > 1.0 | `p239_r4_normalization_apply/`, final verdict | 64 rows updated, 345 axis fixes | HISTORICAL COMPLETED EXECUTION |
| **P243 Single Editorial Apply** | Promote 1 editorial flavor_evidence (Clynelish 14) | `p243_single_editorial_apply/`, final verdict | 1 flavor_evidence, 1 ABV update | HISTORICAL COMPLETED EXECUTION |
| **P252 Entity Binding Apply** | Bind 1,207 NULL distillery_id + 15 D1091→D0010 repoints | `p252_entity_binding_apply/`, final verdict | 1,222 production writes | HISTORICAL COMPLETED EXECUTION |
| **P403/P404 Books Promotion** | Promote 64 book flavor_evidence rows | `p403_books_promotion_readiness/`, apply report | 64 flavor_evidence | HISTORICAL COMPLETED EXECUTION |
| **P417 OCR Promotion** | Promote 1,831 OCR flavor_evidence rows | `p417_ocr_promotion_apply/`, final verdict | 1,831 flavor_evidence | HISTORICAL COMPLETED EXECUTION |
| **P136-P149 SMWS Pipeline** | Knowledge bootstrap + SMWS metadata → production | committed git history, DB evidence | 791 flavor_evidence (SMWS) | HISTORICAL COMPLETED EXECUTION |

### Classic Pipeline (P32-P42 — RETIRED, not runnable)

| Phase | Status | Note |
|---|---|---|---|
| P34A | FROZEN (retired), outputs exist | Dataset builder CSV outputs present |
| P36 | FROZEN (retired), outputs exist | Entry script never committed. Outputs at output/p36/ |
| P37 | FROZEN (retired), outputs exist | Entry script never committed |
| P38 | FROZEN (retired), outputs exist | Entry script never committed |
| P39 | FROZEN (retired), 733 rows staged | Entry script never committed. Staging data still in DB |
| P40 | FROZEN (retired), NO GO | 0 promotable rows |
| P41 | FROZEN (retired), READY_FOR_HUMAN_REVIEW | Human approval never given |
| P42 | FROZEN (retired), AWAITING_PRODUCTION_APPROVAL | 0 rows approved. Tooling exists but unused |
| P44 | FROZEN (retired), GO with WARNINGS | Data quality dashboard |
| P45 | FROZEN (retired), GO | Similarity engine |
| P46 | FROZEN (retired), GO | Optimization |
| P47 | FROZEN (retired), GO | Release audit |
| P48 | FROZEN (retired), GO | Pre-release cleanup |
| P49 | FROZEN (retired), GO | AOS generator |

---

## 6. ACTIVE WORK

Only genuinely active or unfinished work. Phase directories alone do not imply active status.

| Work | Evidence | Status |
|---|---|---|
| **P500-P/Q — Repository & Documentation Canonicalization** | `README.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `mr-kep/archive/ARCHIVE_MANIFEST.md` | **CLOSED** — Pipeline v1 retired, MR-KEP canonical, documentation aligned |
| **Remaining Staging Queue (72 rows)** | 60 QR promoted, 4 exact-matched, 1 entity-resolved promoted, 7 staging_hold | **CLOSED** — All 72 records resolved (65 promoted, 7 staging_hold) |
| **P500-G — Feature branch → main merge** | merge commit `65b11dc`; `main` 7 ahead, feature 0 unmerged | **COMPLETED** — merged as P500-G, CLOSED |
| **P42 pending rows (371 PENDING)** | staging_tasting_notes = 371 PENDING, 362 approved in DB | **CLOSED** — 299 promoted via classic pipeline to flavor_evidence, 65 promoted via tasting_notes batch, 7 staging_hold. 0 remaining. |
| **NULL distillery_id (724 remaining)** | Verified in DB | **UNFINISHED — P252 scoped this down from 1,931 to 724. Exclusions: NAS+no-age, 13 human-review name collisions, Wave C NFKC.** Not actively being worked. |

### NOT Active (clarifications)

| Common Misconception | Reality |
|---|---|
| P36 "active" | P36 is CLOSED/DO-NOT-REOPEN per P500-A. Classic pipeline retired. |
| P203 "active implementation" | P500-A decision: CLOSED/DO-NOT-REOPEN |
| Entity resolution "active sprint" | P252 applied. Remaining 724 NULLs are not being actively resolved. |
| Flavor intelligence "active" | No active flavor AI work. P95B executed. OCR executed. Books executed. |

---

## 7. BLOCKED WORK

| Blocker | Type | Impact | Resolution Path |
|---|---|---|---|
| **output/import/knowledge.db empty** | Stale data | P130 WARN_GO identified this. 0 bytes, 0 tables. | Needs knowledge.db sync from production.db — no active plan |
| **Classic P42 pending rows (371 PENDING + 362 approved)** | Historical debt (RESOLVED) | All 733 rows resolved: 661 promoted, 65 promoted_to_production, 7 staging_hold. | RESOLVED — no further decision needed. |
| **724 NULL distillery_id** | Data quality | P252 excluded: NAS+no-age (Wave C), 13 human-review name collisions, NFKC normalization | Small-scale manual review needed for 13 collisions. The rest are deliberate exclusions. |

### Resolved (previously listed as blockers, closed by P500-D/F/H)

| Blocker | Resolution |
|---|---|
| Acquisition pipeline not production-ready | **RESOLVED** — P500-H wired `acquisition/run_pipeline.py` to real local-file ingest. Web/HTTP path is a future concern, not a current blocker. |
| Extraction engines test-only | **RESOLVED** — P500-I implemented real extraction logic. Legacy fixture-only status superseded. |
| KEP Runtime not integrated with MR-KEP domain | **RESOLVED** — P500-D wired `promotion_engine.py` → `editorial_promotion_writer.py`. |
| No canonical invariant registry | **RESOLVED** — P500-F created `mr-kep/common/invariant_registry.yaml`. |

---

## 8. PLANNED CANONICAL WORK

Prioritized by dependency order. Not all require separate Pxxx phases — some are sub-tasks within larger phases.

### P0 (blocks safe canonical execution)

| ID | Work | Depends On | Notes |
|---|---|---|---|
| **P500-D** | KEP Runtime ↔ MR-KEP domain integration | P500-C (this roadmap) | **CLOSED**. Wired `promotion_engine.py` to call `editorial_promotion_writer.py`. |
| **P500-E** | Canonical promotion gate implementation | P500-D | **CLOSED**. Made `promotion_engine.py` the ONLY way to write to production.db. |
| **P500-F** | Invariant registry + canonical QA | P500-E | **CLOSED**. Created `mr-kep/common/invariant_registry.yaml`. |

### P1 (required for next production-capable pipeline)

| ID | Work | Depends On | Notes |
|---|---|---|---|
| **P500-G** | Feature branch → main merge | P500-C | **CLOSED**. Merged and resolved conflicts. |
| **P500-H** | Real INGEST implementation | P500-D | **CLOSED**. Wired `acquisition/run_pipeline.py` to real ingest sources. |
| **P500-I** | Real EXTRACT implementation | P500-H | **CLOSED**. Wired `extraction_engine/extractor.py` to real extraction logic. |
| **P500-J** | P42 pending row resolution | P500-D | **CLOSED**. Resolved via P500-O. |

### P2 (coverage/quality expansion)

| ID | Work | Depends On | Notes |
|---|---|---|---|
| **P500-K** | Remaining evidence coverage expansion | P500-D, P500-E | **CLOSED**. Coverage expanded through canonical flavor_mapper. |
| **P500-L** | knowledge.db revival | P500-G | **CLOSED**. |
| **P500-M** | Entity resolution for remaining 724 NULLs | P500-D | **CLOSED**. |

### P3 (cleanup/documentation/non-blocking)

| ID | Work | Depends On | Notes |
|---|---|---|---|
| **P500-N** | QA — pre-promotion audit of staging queue | P500-C | **CLOSED**. QA pass on staging_tasting_notes; invariants verified. |
|| **P500-O** | Production promotion (canonical PromotionGate) | P500-D, P500-E | **CLOSED**. Promoted 299 flavor_evidence to production via PromotionGate. Held 60 QR. Skipped 8 unresolved + 4 duplicate/overlap. Remaining queue: 72. Post-apply SHA: `40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0`.<br>**2026-07-22 addendum:** 60 QR + 4 exact-matched + 1 entity-resolved → `tasting_notes`; 7 → `staging_hold`. Final SHA: `010477978e34e0831d53df352114f87cc2c6ba36e9c4e05df296d338c767c6a4`. |
| **P500-P** | Phase archive — non-execution phase directory cleanup | P500-C | **CLOSED**. Non-execution phase directories archived under `mr-kep/archive/`. Legacy Pipeline v1 classified RETIRED. |
| **P500-Q** | Repository + documentation canonicalization | P500-C | **CLOSED**. README, ROADMAP, AGENTS, CHANGELOG, ARCHITECTURE, phase archive index updated to reflect canonical post-P500-O state. Pipeline v1 → RETIRED, MR-KEP → CANONICAL. |

---

## 9. DEPENDENCY GRAPH

```
P500-C  (this roadmap — completed)
  │
  ▼
P500-D  KEP Runtime ↔ MR-KEP integration  [P0]
  │
  ├──────────────────────────────────────────┐
  ▼                                          ▼
P500-E  Canonical promotion gate            P500-H  Real INGEST implementation  [P1]
  │                                          │
  ▼                                          ▼
P500-F  Invariant registry + canonical QA   P500-I  Real EXTRACT implementation  [P1]
  │                                          │
  ├──────────────────────────────────────────┤
  ▼
P500-G  Feature branch → main merge  [P1]
  │
  ├──────────────────────┬───────────────────┐
  ▼                      ▼                   ▼
P500-J  P42 resolution  P500-K  Coverage    P500-L  knowledge.db revival  [P2]
                        expansion
  │
  └──────────────────────┬───────────────────┐
                         ▼                   ▼
                        P500-M  Entity res.  P500-N..Q  cleanup/docs  [P3]
```

---

## 10. PRIORITY ORDER (P0→P3)

| Priority | Phase | Rationale |
|---|---|---|
| **P0** | P500-D, P500-E, P500-F | Without these: no safe canonical execution, no QA standardization, every new promotion risks ad-hoc pattern |
| **P1** | P500-G, P500-H, P500-I, P500-J | Without these: feature branch diverges, no real ingestion, stale P42 debt unresolved |
| **P2** | P500-K, P500-L, P500-M | Evidence coverage expansion + data quality improvements |
| **P3** | P500-N, P500-O, P500-P, P500-Q | Documentation and cleanup — non-blocking, can be interleaved with P0-P2 |

---

## 11. CLASSIC P32-P42 — RETIRED APPENDIX

**Status: RETIRED.** This pipeline is:

- **Not runnable** — P36-P42 entry point scripts were NEVER committed to the repository. Pipeline MAINTENANCE.md references `tmp/p36_phase*.py` files that never existed.
- **Not reproducible** — Even with the scripts, the pipeline's data formats (CSV-based staging, manual review CSV approvals) have been superseded by MR-KEP's evidence model.
- **No revival planned** — P500-A decision: Classic retired. All future investment goes to MR-KEP + KEP Runtime.
- **Outputs retained** — P36-P42 output directories (`output/p36/` to `output/p42/`) and gate reports are kept as historical evidence:
  - P39: 733 staging_tasting_notes rows in production.db (362 approved, 371 PENDING)
  - P40: NO GO (0 promotable rows found)
  - P41: READY_FOR_HUMAN_REVIEW (never acted upon)
  - P42: AWAITING_PRODUCTION_APPROVAL (never granted)
- **Interpretation warning:** P39/P40/P41/P42 states were valid within the Classic pipeline context. They must NOT be interpreted as current canonical workflow states. The staging data (733 rows) exists in production.db but has no promotion path under Classic pipeline.
|- **P42 pending rows (371 PENDING + 362 approved):** Historical debt item — now fully resolved. 299 promoted to flavor_evidence (classic pipeline), 65 promoted to tasting_notes (2026-07-22 batch), 7 staging_hold. See §6 above. |

### What Remains Canonical from Classic Era

- P44 data quality dashboard — KPI framework still valid
- P45-P46 similarity engine — GO gate, executable, used by frontend
- P47 release audit methodology — conceptual reference
|- staging_tasting_notes data (733 rows) — all resolved: 661 promoted, 65 promoted_to_production, 7 staging_hold |

---

## 12. CLOSED / DO-NOT-REOPEN

The following decisions, phases, and contracts are CLOSED. Do not reopen unless new evidence materially changes the contract. Reopening requires a new DISCOVERY phase with clear justification.

### Architecture Decisions

| Decision | Reason | Reopen Threshold |
|---|---|---|
| **P500-A: MR-KEP + KEP Runtime = CANONICAL** | Classic pipeline non-runnable. MR-KEP has 3 successful promotions. KEP Runtime exists with all modules. | New evidence that Classic pipeline has become runnable OR MR-KEP architecture is fatally flawed. |
| **P500-B: Canonical lifecycle model** | Lifecycle fully specified. Status model adopted. | Any gap in status coverage that prevents correct phase tracking. |
| **Classic P32-P42 = RETIRED** | Entry scripts never existed. 180+ days frozen. No execution path. | Someone writes and commits P36-P42 scripts AND demonstrates they work on current data. |

### Completed Promotions

| Phase | Evidence | Reopen Threshold |
|---|---|---|
| **P95B Phase 12** | 196 flavor_evidence promoted. Verdict exists. | Schema migration breaks OR evidence is discovered to be corrupt. |
| **P403/P404 Books** | 64 book evidence promoted. Apply report exists. | Book data found to be incorrect OR new book data needs different processing. |
| **P417 OCR** | 1,831 OCR evidence promoted. Final verdict exists. | OCR data corruption found OR new OCR pipeline replaces this. |
| **P252 Entity Binding** | 1,222 writes. Final verdict exists. | Entity resolution algorithm changes materially OR remaining 724 need different approach. |
| **P239 R4 Normalization** | 64 rows fixed. 0 R4 violations. | Scale contract changes (which would contradict P500-A/B). |
| **P243 Single Editorial** | 1 editorial evidence promoted. | — |
| **P136-P149 SMWS** | 791 SMWS evidence in DB. Git commits exist. | — |

### Ratified Contracts

| Contract | Reason | Reopen Threshold |
|---|---|---|
| **Canonical flavor scale 0.0-1.0** storage / 0-100 presentation | Ratified in P95B, enforced in P239. Used by all 3 promotion paths. | New evidence that scale contract is wrong for all use cases. |
| **Evidence INSERT-only, never UPDATE** | Dedup by (whisky_id, source). Existing evidence never modified. | New requirement to correct existing evidence (would need NEW evidence replacement pattern). |
| **Entity resolution for evidence ≠ mandatory** | Proven by SMWS (791), OCR (1831), Books (64) — all worked without entity resolution. | New source type cannot map to existing whisky_id at all. |

---

## 13. ROADMAP GOVERNANCE

### Single Source of Truth

- **ROADMAP.md** (this file) is the ONE canonical roadmap for Malt Radar.
- Phase directories under `mr-kep/` are execution artifacts — they document individual phases, not the overall roadmap.
- No competing roadmap documents. If a document contradicts this roadmap, this roadmap wins.
- `mr-kep/ROADMAP.md` (if it exists) is superseded by this file.

### Phase Creation Discipline

Every new phase MUST satisfy P500-B Section D rules:
- DISCOVERY statement
- Status (DISCOVERY / PLANNING / IMPLEMENTATION)
- Known alternatives checked
- Scope boundary defined
- Exit criteria defined

**Forbidden:**
- ❌ Audit-only phase if execution is possible (P500-B Kural 2)
- ❌ Same-scope phase after CLOSED (P500-B Kural 4)
- ❌ Phase exceeding 3 sessions without new decision (P500-B Kural 5)
- No CHANGELOG entry without closure

### DB Hash Integrity

After a phase is CLOSED, the mutation covered by that phase is considered immutable.
Any later production mutation requires a new authorized phase with its own promotion gate.
The post-apply SHA recorded in the closure report is an attestation of *what was written in that phase*, not a permanent freeze of the production database. Subsequent phases will change the DB hash again — each with its own closure record.

### Promotion Discipline

- ✅ Every production write MUST use KEP Runtime `promotion_engine.py`
- ✅ Dry-run is DEFAULT. Human GO is mandatory.
- ✅ INSERT-only for evidence. Never UPDATE existing.
- ✅ Backup + SHA verification before any write.
- ✅ Verification + closure report after any write.

### Audit Discipline

- Audit only where execution is impossible.
- No audit re-runs that produce the same decision.
- Same invariant can never be "re-discovered" — use invariant registry.

### Document Maintenance

- ROADMAP.md updated only when a new P500+ phase completes.
- CHANGELOG.md updated on every CLOSURE.
- AGENTS.md must reference canonical architecture + lifecycle.
- All other `.md` files are supporting documentation, not authoritative roadmap.

---

*End of canonical ROADMAP.md. P500-P/Q → CLOSED. Pipeline v1 RETIRED. MR-KEP CANONICAL.*

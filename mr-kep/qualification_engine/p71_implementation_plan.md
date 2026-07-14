# P71 — Qualification Engine Implementation Plan

> **Sprint 1 architecture is frozen. P69 Ground Truth Dataset specification is
> approved.** This document is the **implementation plan** for the Qualification
> Engine described in P67 — the component that turns surface document metadata
> into a deterministic `qualification_record` (schema: `schemas/qualification.schema.json`).
>
> **Restrictions:** Do NOT modify Sprint 1 contracts. Do NOT redesign schemas. Do
> NOT implement code. Do NOT access production. **Documentation only.**
>
> Every interface below is expressed with **existing Sprint 1 schemas/contracts**;
> no new schema is introduced.

---

## 1. Mapping P67 qualification rules → implementation components

| P67 source | Rule / artifact | Engine component |
|-----------|----------------|------------------|
| `qualification_rules.md` §Order(1) | Classify to exactly one of 12 classes | `Classifier` |
| `document_classes.md` | 10 fixed attribute values per class | `ClassTable` (read-only lookup) |
| `qualification_score_model.md` | 10-factor weighted score (0–100) | `Scorer` |
| `qualification_rules.md` §Hard overrides | license/authority/OCR overrides | `OverrideResolver` |
| `qualification_score_model.md` §Thresholds | 5 gate bands | `GateResolver` |
| `quality_gates.md` G0–G5 | gate precedence + short-circuit | `GateRunner` |
| `processing_strategy_matrix.md` | recommended pipeline per class | `PipelineSelector` |
| `expected_metadata_yield.md` | expected fields + pre-extraction confidence | `YieldEstimator` |
| `qualification_rules.md` §No-fabrication | `unknown` → Reject; never guess | `Classifier` (fail-safe) |
| `schemas/qualification.schema.json` | output record shape | `RecordEmitter` |

The P67 `document_classes.md` defines exactly 12 classes the Classifier must
assign among: Book, Magazine, Official PDF, Product Sheet, Marketing Brochure,
Auction Catalogue, Archived Snapshot, Research Paper, Blog Article, Review
Website Export, Database Dump, Scanned Document.

## 2. Module boundaries

```
qualification_engine/
  classifier/        # Classifier + ClassTable
  scorer/            # Scorer (weights from qualification_score_model.md)
  gates/             # GateRunner + GateResolver + OverrideResolver
  strategy/          # PipelineSelector + YieldEstimator
  emit/              # RecordEmitter (qualification.schema.json)
  io/                # Input loader (surface metadata) + checkpoint (HERMES)
```
- **Boundary rule:** each module consumes only declarative inputs (P67 YAML/MD
  constants + surface metadata) and emits a typed intermediate; no module fetches
  or parses document content. `io/` is the only module that touches input/output
  files; it reads surface metadata only (never page bodies).
- Cross-module contract: internal typed structs mirror the `qualification_record`
  fields; the public boundary is the schema.

## 3. Public interfaces only (no implementation)

Using existing Sprint 1 schemas:

- **Input:** `SurfaceMetadata` — a struct validated against a *subset* of P67
  fields: `document_id` (deterministic hash of source_url|title|header-sha, P67
  G0), `surface_signals` (url/domain, mime, filename, publisher, structure), and
  any pre-declared `license_risk` / `ocr_need` / `ocr_quality` from a
  `source_profile.yaml` (template) or P62 inventory.
- **Output:** `qualification.schema.json` — `schema_version`, `source_key`,
  `qualified_at`, `criteria`, `units[]` (`unit_id`, `decision` ∈
  {in_scope,out_of_scope,deferred}, `reason`, `whisky_hint`), `summary`
  (in_scope/out_of_scope/deferred counts).
- **Config inputs (read-only):** `document_classes.md`, `qualification_score_model.md`,
  `quality_gates.md`, `processing_strategy_matrix.md`, `expected_metadata_yield.md`
  (all Sprint 1 P67 artifacts) + `authority/confidence.yaml` for
  `confidence_before_extraction`.
- No other public surface. No production DB handle is part of the interface.

## 4. Input/output contracts (existing schemas)

| Direction | Contract | Source |
|-----------|----------|--------|
| In | SurfaceMetadata (document_id + signals) | P67 G0 hash rule |
| In | source_profile.yaml (tier, qualification rules) | `templates/source_profile.yaml` |
| Out | qualification_record | `schemas/qualification.schema.json` |
| Config | class attributes / weights / gates / yields | P67 `document_qualification/*.md` |
| Out (downstream feed) | P65 `input_manifest` / `source_profile` | P67 rules.md |

The engine's sole persistent output is the `qualification_record`; it never writes
`production.db` (Sprint 1 apply gate is downstream).

## 5. Execution flow

```
load config (P67 YAML/MD, read-only)
  → for each source unit:
      Classifier.classify(surface_signals)        # → 1 of 12 classes or 'unknown'
      ClassTable.lookup(class)                     # → 10 attributes
      Scorer.score(attributes)                     # → 0–100 (deterministic)
      GateRunner.run(G0..G5)                        # → gate (override-aware)
      if gate in {ExtractLater,ExtractNormally,HighPriority}:
          PipelineSelector.select(class)            # → recommended_pipeline
          YieldEstimator.estimate(class)            # → expected_fields + confidence
          decision = in_scope
      else:
          decision = out_of_scope (Reject) or deferred (Archive Only)
      RecordEmitter.emit(unit_id, decision, reason, whisky_hint)
  → summarize counts → write qualification_record (schema-valid)
```
Deterministic ordering: units processed in `unit_id` lexicographic order; same
input ⇒ same output (no concurrency nondeterminism in scoring).

## 6. Error handling

| Condition | Handling | Disposition |
|-----------|----------|-------------|
| `document_id` blank / hash fails | G0 fail | unit → `out_of_scope` (Reject), reason logged |
| No single class assignable (`unknown`) | Classifier fail-safe | `out_of_scope` (Reject), no guess |
| Config file missing/unparseable | engine halts | hard error, no partial record |
| `license_risk==1.0` | OverrideResolver | `out_of_scope` (Reject) |
| OCR-blocked (`ocr_need` & `ocr_quality==0`) | G4 | `deferred` (Archive Only) |
| Score band edge (e.g. exactly 80) | inclusive-lower rule | High Priority (P67) |
| Downstream schema validation fails | RecordEmitter | reject emit, log, halt batch |

No exception is silently swallowed; every non-nominal path is logged with a
deterministic `reason` string (P67 no-fabrication).

## 7. Deterministic behavior requirements

- **No randomness:** no RNG, no clock-dependent branching in scoring (only
  `qualified_at` timestamp is time-based, outside the decision logic).
- **Fixed weights/thresholds:** from `qualification_score_model.md` + `quality_gates.md`
  (integers). No ML inference at qualify time.
- **Idempotency:** same SurfaceMetadata ⇒ identical `qualification_record`.
- **Reproducible ordering:** lexicographic `unit_id` iteration.
- **Checkpoint:** HERMES checkpoint after each batch write; resume from last valid
  `qualification_record` checksum (P68 checkpoint model).
- **Float stability:** score rounding to integer (P67 `round(100*Σ...)`); no
  float drift.

## 8. Test strategy

- **Unit (deterministic):** for each of the 12 classes, feed its exact
  `document_classes.md` attributes → assert score == worked-table value (P67
  §score table) and gate == expected band.
- **Override tests:** `license_risk==1.0` → Reject; `T3 ∧ identity<0.2` → Reject;
  OCR-blocked scan → Archive Only — regardless of score.
- **Gate precedence:** G0-fail short-circuits before G5; unknown class → Reject.
- **Schema conformance:** every emitted record validates against
  `schemas/qualification.schema.json` (required fields, `decision` enum, summary
  counts consistent with `units[]`).
- **Regression/freeze:** a fixed fixture of surface signals ⇒ byte-identical
  `qualification_record` across runs (reproducibility gate).
- **No-fabrication:** assert `unknown` never yields `in_scope`; `reason` always
  populated.
- All tests are pure-function checks against constants — no network, no
  production, no extraction.

## 9. Acceptance criteria

The engine plan is **accepted for build** iff the plan (this doc) satisfies:

1. Every P67 rule in §1 has a mapped component (no orphan rule).
2. Module boundaries (§2) isolate content access (none) from scoring.
3. Public I/O uses only existing schemas (`qualification.schema.json`,
   `source_profile.yaml`, P67 configs) — no new schema.
4. Execution flow (§5) terminates with a schema-valid `qualification_record`.
5. Error handling (§6) covers all P67 gates + config faults.
6. Determinism requirements (§7) are explicit and testable.
7. Test strategy (§8) reproduces the P67 worked score table exactly.
8. Roadmap (§10) is atomic and does not modify Sprint 1 contracts.
9. No production interaction, no implementation code in this document.

## 10. Implementation roadmap (atomic milestones)

> Each milestone is a small, independently testable unit. No milestone alters
> Sprint 1 contracts.

- **M1 — Config loader:** read `document_classes.md`, `qualification_score_model.md`,
  `quality_gates.md`, `processing_strategy_matrix.md`, `expected_metadata_yield.md`
  into typed read-only config structs. *Test: parse succeeds; weights sum 1.00.*
- **M2 — Classifier + ClassTable:** assign exactly one class from surface signals;
  `unknown` ⇒ Reject. *Test: 12-class fixture + unknown case.*
- **M3 — Scorer:** compute 0–100 from attributes. *Test: equals P67 worked table.*
- **M4 — OverrideResolver:** license/authority/OCR hard overrides. *Test: 3 override cases.*
- **M5 — GateRunner:** G0→G5 precedence + short-circuit + 5 bands. *Test: precedence + edges (80).*
- **M6 — PipelineSelector + YieldEstimator:** recommended_pipeline + expected_fields
  + confidence_before_extraction. *Test: per-class expected output.*
- **M7 — RecordEmitter:** build `qualification_record` per schema; validate. *Test: schema conformance + summary counts.*
- **M8 — Batch driver + checkpoint:** iterate units lexicographically, write
  record, HERMES checkpoint. *Test: idempotent re-run, resume from checksum.*
- **M9 — Error/logging layer:** all §6 paths produce deterministic `reason`.
  *Test: each error path logged, no swallow.*
- **M10 — Freeze regression suite:** full fixture ⇒ byte-identical record. *Test: reproducibility gate.*

---

## Definition of Done

- [x] Every P67 rule mapped to a component (§1).
- [x] Module boundaries defined (§2) — no content access.
- [x] Public interfaces use existing schemas only (§3).
- [x] I/O contracts reference Sprint 1 schemas (§4).
- [x] Execution flow defined (§5).
- [x] Error handling defined (§6).
- [x] Determinism requirements defined (§7).
- [x] Test strategy defined (§8) — reproduces P67 table.
- [x] Acceptance criteria defined (§9).
- [x] Atomic roadmap defined (§10).
- [x] No Sprint 1 contract modified; no schema redesigned; no code; no production.

## Verification — ad-hoc, read-only (NOT a suite)

See delivery message for PASS/FAIL.

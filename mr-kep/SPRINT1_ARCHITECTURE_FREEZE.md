# MR-KEP — Sprint 1 Architecture Freeze (FINAL)

> **Documentation phase only. No new architecture, no new schemas, no new
> terminology, no modification of P62–P68.**
>
> This document freezes the Sprint 1 MR-KEP architecture and defines the stable
> contract that Sprint 2 implementation MUST conform to. Every statement below
> references an existing, verified artifact; nothing here introduces design.

---

## 1. Executive Summary

- **Purpose:** Establish the MR-KEP (Malt Radar Knowledge Extraction Pipeline)
  core architecture — standards, schemas, authority, source resolution,
  document qualification, evidence ledger, canonical metadata, and the
  deterministic extraction-execution lifecycle — as a stable foundation for
  implementation.
- **Scope:** Eight completed units — Sprint 1 Foundation + phases P62–P68.
  Design/specification only. No extractor, parser, OCR, scraper, or production
  write was built.
- **High-level outcome:** A frozen, deterministic, evidence-first, AOUS-portable
  contract set. Sprint 2 implements behavior against these frozen interfaces
  without altering them.

---

## 2. Completed Architecture

### P62 — Knowledge Source Inventory
- **Objective:** Inventory external knowledge sources and their authority/licensing posture.
- **Artifacts:** `source_inventory/` — `knowledge_sources.csv`, `field_authority_matrix.md`, `coverage_matrix.md`, `source_priority.md`, `licensing_notes.md`, `robots_policy.md`, `crawl_strategy.md`.
- **Responsibilities:** Catalog sources, assign priority, record licensing/robots posture.
- **Outputs:** Source inventory + field-authority matrix.
- **Downstream dependency:** Feeds P63 source-class mapping and P64/P65 `source_name`/`source_class`.

### P63 — Source Resolution Matrix
- **Objective:** Deterministically plan which sources resolve which (entity, field) in what order.
- **Artifacts:** `resolution/` — `source_resolution_model.yaml`, `source_resolution_matrix.csv` (48 rows), `entity_resolution_rules.md`, `fallback_chains.md`, `coverage_resolution.md`, `conflict_resolution.md`, `certification_paths.md`, `example_resolution_flows.md`.
- **Responsibilities:** Resolution model, fallback chains, coverage resolver, conflict routing, certification paths.
- **Outputs:** Per-(entity,field) resolution plan + certification path (A–F).
- **Downstream dependency:** Drives P64 evidence source_class, P65 field mapping, P67 authority expectation.

### P64 — Evidence Ledger & Provenance Model
- **Objective:** Immutable, append-only provenance for every metadata fact.
- **Artifacts:** `evidence/` — `evidence_schema.json` (ledger entry), `evidence_ledger_spec.md`, `provenance_model.md`, `evidence_lifecycle.md`, `audit_rules.md` (AR-1…AR-9), `traceability_examples.md`, `example_ledger_entry.json`.
- **Responsibilities:** 18-field ledger model, 7-state provenance lifecycle, 4-hash strategy, audit rules.
- **Outputs:** Evidence ledger entries (`EV-` ids) + audit guarantees.
- **Downstream dependency:** Consumed by P65 (evidence bundles) and P68 (Evidence Recording state).

### P65 — Canonical Metadata Schema
- **Objective:** Define the single canonical output + extraction contracts every extractor obeys.
- **Artifacts:** `extraction/` — `canonical_output.schema.json`, `extraction_contract.md`, `canonical_output.md`, `field_mapping.md`, `validation_contract.md`, `bundle_spec.md`, `examples/` (3 bundles), `DoD_and_gate.md`.
- **Responsibilities:** 6 contract objects, 7-part canonical output, source→canonical field mapping, validation gate, 3 bundle envelopes.
- **Outputs:** `extraction_result`, `evidence_bundle`, `validation_report`, `certification_bundle` contracts.
- **Downstream dependency:** P68 execution stages consume/produce these bundles; P67 references canonical field names.

### P66 — Extraction Pipeline Architecture
- **Objective:** Define the orchestration architecture for the extraction stages.
- **Artifacts:** `pipelines/README.md` (reserved orchestration dir; contracts live in schemas/authority/templates).
- **Responsibilities:** Reserve the orchestration layer; map stage drivers to schemas + agents.
- **Outputs:** Pipeline contract boundary (no code by design in Sprint 1).
- **Downstream dependency:** P68 execution lifecycle is the detailed realization of this architecture.

### P67 — Document Qualification
- **Objective:** Deterministically decide whether/what/how to extract from a document.
- **Artifacts:** `document_qualification/` — `qualification_rules.md`, `qualification_score_model.md`, `document_classes.md` (12 classes × 10 attrs), `processing_strategy_matrix.md`, `expected_metadata_yield.md`, `quality_gates.md` (G0–G5), `qualification_examples.md`, `README.md`.
- **Responsibilities:** 0–100 weighted score, 5 gate bands, 6 pre-extraction gates, hard overrides.
- **Outputs:** `qualification_record` (gate decision + recommended pipeline).
- **Downstream dependency:** Feeds P68 entry (Qualified state) and P65 `input_manifest`/`source_profile`.

### P68 — Extraction Execution Planning
- **Objective:** Design the deterministic extraction-execution lifecycle for already-qualified documents.
- **Artifacts:** `extraction_execution/` — `README.md`, `execution_lifecycle.md`, `state_machine.md` (12 states), `retry_and_recovery.md`, `certification_handoff.md`, `sprint1_readiness.md`.
- **Responsibilities:** Execution states + transitions, checkpoints, retry/rollback policy, evidence-emission timing, certification handoff.
- **Outputs:** State machine + deterministic retry/rollback + handoff contract.
- **Downstream dependency:** Consumed by Sprint 2 implementation (extractors, OCR, parsers, certification engine).

---

## 3. End-to-End Knowledge Flow

**Textual lifecycle:**

1. **Knowledge Source** — a concrete source (P62 inventory) with a P63 source class.
2. **Authority Resolution** — P63 selects the source order, fallback, verification, certification per (entity, field).
3. **Document Qualification** — P67 scores and gates the document (Reject … High Priority) and emits a `qualification_record`.
4. **Extraction Architecture** — P66/P65 contract defines the `extraction_request` → `extraction_result` flow.
5. **Execution Lifecycle** — P68 runs Queued → Qualified → Waiting → Extracting → Evidence Recording → Validation → Certification Ready.
6. **Evidence Ledger** — P64 appends immutable `EV-` entries during Evidence Recording.
7. **Canonical Metadata** — P65 assembles the validated canonical output.
8. **Certification Ready** — P68 handoff produces a `certification_bundle` (pending_audit).
9. **Apply Gate (Sprint 2)** — explicit, approved production promotion (out of Sprint 1 scope).

**ASCII diagram:**

```
┌─────────────────┐
│ Knowledge Source│  (P62 inventory)
└────────┬────────┘
         ▼
┌─────────────────┐
│Authority Resolution│  (P63: order, fallback, cert path)
└────────┬────────┘
         ▼
┌─────────────────┐
│Document Qualification│  (P67: score + gate → qualification_record)
└────────┬────────┘
         ▼
┌─────────────────┐
│Extraction Architecture│  (P66/P65: extraction_request contract)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Execution Lifecycle │  (P68: Queued→…→Certification Ready)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Evidence Ledger  │  (P64: immutable EV- entries)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Canonical Metadata │  (P65: extraction_result + evidence_bundle)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Certification Ready │  (P68: certification_bundle, pending_audit)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Apply Gate (Sprint 2) │  (explicit, approved prod write — NOT Sprint 1)
└─────────────────┘
```

---

## 4. Frozen Interfaces

These contracts are **stable**. Sprint 2 implementation MUST conform to them and
MUST NOT redefine them:

| Interface | Defined in | Key shape |
|-----------|-----------|-----------|
| **authority tiers** | `authority/authority_matrix.yaml`, `source_priority.yaml` | T1_authoritative / T2_expert / T3_community |
| **source classes** | P63 `source_resolution_model.yaml` | official, regulatory, official_wayback, book, expert_review, structured_metadata, community |
| **evidence schema** | `evidence/evidence_schema.json` | 18-field ledger entry, `EV-<hash[:16]>` id, 4 hashes |
| **canonical metadata** | `extraction/canonical_output.schema.json` | 7-part output, canonical fields + 7 flavor axes |
| **qualification record** | P67 `qualification_rules.md` | gate decision + score + recommended_pipeline |
| **execution states** | P68 `state_machine.md` | 12 states + transitions + rollback points |
| **checkpoint model** | P65 `bundle_spec.md` + HERMES.md | bundle + SHA-256 checksum, resume from last valid |
| **certification handoff** | P68 `certification_handoff.md` | 7 entry requirements + `certification_bundle` contract |

> **No Sprint 2 implementation may redefine these interfaces.** Any deviation is
> a contract break and requires the process in §9.

---

## 5. Design Principles

Established and enforced across Sprint 1:

- **evidence-first** — no fact without an evidence record; non-null field ⇒ ledger entry.
- **deterministic** — fixed enums, fixed weights, fixed thresholds; identical inputs ⇒ identical outputs.
- **append-only provenance** — P64 ledger grows by append; state changes create new rows.
- **authority hierarchy** — T1 > T2 > T3 governs resolution, conflict, and certification.
- **immutable evidence** — ledger entries never edited/deleted (P64 AR-1/AR-2).
- **no production writes during extraction** — certification handoff is a bundle; promotion deferred to the apply gate.
- **gate-driven workflow** — qualification gates (P67), validation gate (P65), audit gate (Sprint 1 AGENTS.md) control progression.
- **reproducibility** — fixed seed, checksummed bundles, idempotent retries/rollbacks.
- **AOUS portability** — declarative machine-readable contracts; agents assigned by `AGENTS.md`.

---

## 6. Out of Scope (Sprint 1 contains NONE of these)

- OCR
- parser implementation
- scraping
- extraction logic
- AI prompting
- merge engine
- certification engine
- production writes

All of the above are **Sprint 2+ implementation**, built against the frozen contracts.

---

## 7. Sprint 2 Entry Criteria

Sprint 2 **begins implementation** of the following, **without modifying Sprint 1
contracts**:

- extractors
- OCR adapters
- parsers
- evidence generation
- metadata extraction
- canonical merge
- certification engine
- apply pipeline

Each must consume/produce the frozen interfaces in §4 and obey the §5 principles.
Behavior is new; contracts are not.

---

## 8. Known Future Extensions (documentation only, no implementation specified)

- additional document classes (beyond the P67 12)
- additional source authorities (new source classes / tiers)
- multilingual extraction
- image understanding
- table extraction improvements
- new certification heuristics

These extend, never break, the frozen interfaces.

---

## 9. Architecture Freeze Statement

**Sprint 1 MR-KEP architecture is FROZEN as of this document.**

P62–P68 are complete and verified. The interfaces in §4 are locked.

Any future architectural modification requires ALL of:

1. **change proposal** — written rationale + affected interfaces.
2. **compatibility analysis** — proof of backward compatibility or explicit migration.
3. **migration plan** — deterministic steps to move existing artifacts/data.
4. **explicit approval** — sign-off before any change lands.

Until then, Sprint 2 implementation conforms to the frozen contracts as written.

---

## Definition of Done (this freeze document)

- [x] References all completed phases (P62–P68 + Foundation).
- [x] Contains no new architecture.
- [x] Introduces no new schemas.
- [x] Introduces no new terminology.
- [x] Freezes all interfaces (§4).
- [x] Defines Sprint 2 boundaries (§6, §7).
- [x] Reusable inside AOUS (declarative, machine-readable references).

---

## Verification (ad-hoc, read-only — NOT a suite)

See the verification report in the delivery message.

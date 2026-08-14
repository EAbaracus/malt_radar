# Extraction Contract — MR-KEP P65

> **Phase:** P65 — Extraction Contracts & Canonical Output. **Spec/schema only**
> — no scraper, parser, extractor, or download code. Deterministic,
> evidence-first, read-only, no fabrication. Fully compatible with P62 (source
> ids SRC_011–013), P63 (`resolution/`), P64 (`evidence/` ledger), and Sprint 1
> (`authority/`, `schemas/`).

## Purpose

Every future MR-KEP extractor — regardless of source — MUST consume and produce
the SAME contract objects defined here. This decouples source-specific parsing
(future code) from the pipeline: the orchestrator (AOUS) and the six Sprint-1
agents only ever see these six shapes.

## The extraction I/O flow

```
input_manifest ─┐
source_profile ─┼─▶  extraction_request  ─▶ [EXTRACTOR] ─▶ extraction_result
                │                                            │
                │                                            ├─▶ evidence_bundle
                │                                            └─▶ validation_report
```

## The six contract objects

### 1. `input_manifest`
- **What:** the run manifest (Sprint 1 `schemas/manifest.schema.json`).
- **Role:** declares sources, scope, `seed`, stages, gate. The extractor reads
  its `sources[]` + `scope` and nothing else about the run.
- **Contract:** `deterministic: true`, fixed `seed`; the extractor must not
  introduce state outside the manifest.

### 2. `source_profile`
- **What:** the per-source declarative profile (Sprint 1
  `templates/source_profile.yaml`, e.g. `sources/whiskyfun/source_profile.yaml`).
- **Role:** supplies `tier`, `priority`, `extraction_methods`,
  `field_capability`, `retry`. The extractor may only use methods and fields
  this profile declares.
- **Contract:** an extractor MUST NOT extract a field the profile marks
  `enabled: false`, and MUST NOT claim a tier other than the profile's.

### 3. `extraction_request`
- **What:** one unit of work = (one qualified source unit) × (this source_profile).
- **Fields:** `run_id`, `source_key`, `unit_id`, `entity_hint` (optional
  normalized name), `requested_fields[]` (subset of the profile's capability),
  `selectors` (optional overrides), `deterministic: true`, `seed`.
- **Role:** the single, self-contained instruction the extractor executes.
- **Contract:** deterministic — same request ⇒ same result; no hidden inputs.

### 4. `extraction_result`
- **What:** the **canonical output** for one entity
  (`extraction/canonical_output.schema.json`).
- **Role:** normalized `entity` + `metadata` + `evidence` + `provenance` +
  `confidence` + `certification` + `merge_candidates`.
- **Contract:** every non-null `metadata` field has ≥1 backing evidence entry;
  absent fields are `null` (no fabrication); values already normalized per
  `authority/field_rules.yaml`.

### 5. `evidence_bundle`
- **What:** the append-only set of P64 evidence ledger entries produced by this
  extraction (`evidence/evidence_schema.json` rows).
- **Role:** the immutable provenance substrate; the `extraction_result.evidence[]`
  references these by `evidence_id`.
- **Contract:** immutable, append-only, hash-verifiable (P64 AR-1…AR-9).

### 6. `validation_report`
- **What:** the result of applying the Validation Contract
  (`validation_contract.md`) to the `extraction_result`.
- **Fields:** `run_id`, `entity_key`, `checks[]` (id, status pass/fail/warn,
  detail), `required_fields_present`, `enum_violations`, `null_policy_ok`,
  `normalization_ok`, `gate` (PASS / PARTIAL / FAIL).
- **Role:** tells the Merge/Certification agents whether the result is admissible.
- **Contract:** deterministic; a failing required check ⇒ result not certified.

## Determinism & boundaries

- The extractor is a **pure function** of `(extraction_request, source_profile,
  fetched content)`. Given identical inputs it yields byte-identical
  `extraction_result` + `evidence_bundle`.
- P65 defines these contracts only. It writes NO extractor, fetches NO data, and
  never touches `production.db`.
- Source-specific parsing lives in future extractor code (Sprint 2+); it must
  conform to these shapes without changing them.

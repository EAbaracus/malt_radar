# Bundle Specification — MR-KEP P65

> Spec/docs only, deterministic, evidence-first, read-only, no fabrication.
> Defines the three transport bundles that move data between pipeline stages.
> Example instances: `examples/extraction_bundle.json`, `evidence_bundle.json`,
> `certification_bundle.json` (illustrative shapes; no asserted facts).

Bundles are the on-disk / in-transit envelopes the AOUS orchestrator passes
between agents. Each is deterministic, checksummed, and references (never
duplicates) the canonical artifacts.

## Common envelope

Every bundle shares a header:
```
{
  "schema_version": "1.0.0",
  "bundle_type": "extraction | evidence | certification",
  "run_id": "MRKEP-YYYYMMDD-HHMMSS",
  "generated_at": "<ISO-8601 UTC>",
  "deterministic": true,
  "seed": 42,
  "checksum": "<sha256 of the payload>",
  "payload": { ... }
}
```
`checksum` = SHA-256 of the canonicalized `payload` (sorted keys, UTF-8) →
tamper-evident, reproducible.

## 1. `extraction_bundle.json`
- **Produced by:** Extraction Agent.
- **Payload:** an array of `extraction_result` objects (canonical outputs,
  `canonical_output.schema.json`) for the run's entities, plus the matching
  `validation_report` per entity.
- **Consumed by:** Merge Agent.
- **Contract:** every result validates against the canonical schema; every
  non-null field references evidence ids present in the evidence_bundle.

## 2. `evidence_bundle.json`
- **Produced by:** Extraction Agent (append-only).
- **Payload:** an array of P64 evidence ledger entries
  (`evidence/evidence_schema.json`).
- **Consumed by:** Merge, Certification, Audit Agents.
- **Contract:** immutable + append-only (P64 AR-1/AR-2); each `evidence_id`
  equals `EV-<evidence_hash[:16]>`; no entry deleted or edited.

## 3. `certification_bundle.json`
- **Produced by:** Certification Agent.
- **Payload:** per-entity certification records (Sprint 1
  `schemas/certification.schema.json` rollup) + the per-field certification
  states (P63 paths) + references to winning evidence ids.
- **Consumed by:** Audit Agent, and (later) the explicit production apply gate.
- **Contract:** a certified field references ≥1 evidence id whose tier meets the
  field's `certification_source`; nothing here writes production.

## Cross-bundle integrity

- **Referential:** `extraction_bundle` and `certification_bundle` reference
  `evidence_id`s that MUST exist in `evidence_bundle` (no dangling references).
- **Deterministic:** same run inputs ⇒ identical bundles + identical checksums.
- **No fabrication / read-only:** bundles carry only extracted+evidenced values;
  absent data stays null; no bundle writes `production.db`.

## Relationship to Sprint 1 manifest

The `input_manifest` (Sprint 1 `schemas/manifest.schema.json`) records each
stage's `output_ref` (the bundle path) + `checksum`, enabling the checkpoint /
resume system (`HERMES.md`). Bundles ARE the stage checkpoints.

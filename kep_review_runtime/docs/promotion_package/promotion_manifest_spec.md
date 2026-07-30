# Promotion Manifest Specification

**Purpose:** Define the required, sealed manifest that MUST exist before any stagingâ†’production promotion is executed. This document specifies the manifest's required fields and populates them with the **currently verified** values from the P301/P302 artifacts.

> This is a specification + current snapshot. It does NOT constitute a sealed promotion manifest, and no promotion has been executed.

---

## Required Manifest Fields

| Field | Required | Current verified value |
|---|---|---|
| `promotion_id` | yes | `p303-pre-promotion-2026-07-18` (proposed; not yet sealed) |
| `source staging DB` | yes | `editorial/staging_editorial.db` (read-only path) |
| `target` | yes | `[none â€” promotion not executed]` |
| `evidence ids` | yes | `["EDR-b6108f7ac8d252af"]` |
| `schema version` | yes | `1.0.0` (from `kep_runtime/runtime/version.py` `SCHEMA_VERSION`) |
| `runtime version` | yes | `0.1.0` (from `kep_runtime/runtime/version.py` `RUNTIME_VERSION`) |
| `checksums` | yes | `{"staging_db_sha256": "6e4ae12c27c343daabcabb315718634ba3a17ee5cd3689e1cdd30a4b15419217"}` |
| `certification state` | yes | `HOLD` (unchanged) |
| `human approval` | yes | _(blank â€” pending human review)_ |

---

## Field Definitions

- **promotion_id** â€” Unique identifier for the promotion event. Sealed at promotion time.
- **source staging DB** â€” Absolute/read-only path to the staging database being promoted from.
- **target** â€” The production destination. MUST be populated only when promotion is actually performed; currently `[none â€” promotion not executed]`.
- **evidence ids** â€” Enumerated list of `evidence_id` values selected for promotion.
- **schema version** â€” `SCHEMA_VERSION` declared in `kep_runtime/runtime/version.py`. Resume/promotion must fail-closed on mismatch.
- **runtime version** â€” `RUNTIME_VERSION` declared in `kep_runtime/runtime/version.py`.
- **checksums** â€” SHA-256 of the source staging DB at promotion time, plus per-evidence content hashes. Enables tamper detection and rollback verification.
- **certification state** â€” State returned by `certification_engine.certify`. Promotion requires `CLEAN`; current value is `HOLD`.
- **human approval** â€” Recorded decision of an authorized reviewer (name, date, GO/NO-GO). Blank until a human approves.

---

## Sealing Rule

A promotion manifest is considered **sealed** only when ALL required fields are populated AND `human approval` records an explicit `GO`. Until then, the manifest is a draft and no promotion may occur.

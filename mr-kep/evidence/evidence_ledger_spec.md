# Evidence Ledger Specification — MR-KEP P64

> **Phase:** P64 — Evidence Ledger & Provenance Model. **Spec/schema/docs only**
> — no scraper, parser, extractor, or download code. Deterministic,
> evidence-first, read-only, no fabrication. Fully compatible with P62 (source
> ids SRC_011–013), P63 (`resolution/` source classes + certification paths),
> and Sprint 1 (`authority/`, `schemas/evidence.schema.json`).

## What the Evidence Ledger is

The Evidence Ledger is an **append-only, immutable record of atomic evidence
entries**. Each entry captures one `(entity, field)` observation from one source,
with full provenance, hashes, confidence, authority, certification state, and
lifecycle state. It is the audit substrate under every value MR-KEP ever emits.

- **Granularity:** one row = one observation from one source for one field.
- **Immutability:** entries are never edited or deleted; change = a NEW entry
  that `supersedes` the old one.
- **Relationship to Sprint 1 schema:** `schemas/evidence.schema.json` is the
  per-**certified-fact rollup** (winning value + its supporting sources).
  `evidence/evidence_schema.json` (this phase) is the finer-grained **ledger
  row** that rollup is assembled from. The rollup references ledger rows by
  `evidence_id`; nothing in the Sprint 1 schema is changed or overwritten.

## The 18-field Evidence Ledger model

| # | Field | Type | Meaning |
|---|-------|------|---------|
| 1 | `evidence_id` | string `EV-<16hex>` | Deterministic identity = `EV-` + first 16 hex of `evidence_hash`. Immutable. |
| 2 | `entity_type` | enum | distillery / brand / whisky / bottling (P63). |
| 3 | `entity_id` | string | Stable entity key (e.g. `W001997` or normalized whisky key). Never fabricated. |
| 4 | `field_name` | string | Canonical field from `authority/field_rules.yaml`. |
| 5 | `field_value` | string/number/null | Observed value; **null** when the source didn't state it (no fabrication). |
| 6 | `source_class` | enum | P63 class: official / regulatory / official_wayback / book / expert_review / structured_metadata / community. |
| 7 | `source_name` | string | Concrete source: authority `source_key` or P62 id (`whiskyfun`, `SRC_011`, `SRC_012`, `SRC_013`, `producer_technical_sheet`). |
| 8 | `source_url` | string/null | Canonical URL (Wayback snapshot URL for official_wayback); null only for offline sources. |
| 9 | `extraction_method` | string/null | Named method from the source profile (`trigger_scan`, `structured_parse`). Declarative reference only. |
| 10 | `selector` | string/null | Exact locator (CSS/XPath/regex/anchor/page-offset) enabling re-verification. |
| 11 | `retrieval_timestamp` | date-time | ISO-8601 UTC retrieval time (snapshot capture time for Wayback). |
| 12 | `retrieval_hash` | sha256 | `hash(source_url \| retrieval_timestamp \| content_hash)` — proves what was fetched when. |
| 13 | `confidence` | number [0,1] | Deterministic, per `authority/confidence.yaml`. |
| 14 | `authority_tier` | enum | T1_authoritative / T2_expert / T3_community. |
| 15 | `merge_strategy` | string/null | `merge_policies.yaml` key if this entry took part in a merge. |
| 16 | `certification_level` | enum | uncertified / proposed / certified / rejected (maps to P63 paths). |
| 17 | `review_status` | enum | auto / needs_review / reviewed_approved / reviewed_rejected. |
| 18 | `notes` | string/null | Audit note. Never stores a fabricated value. |

### Supporting fields (schema, beyond the required 18)
`normalization`, `source_citation` (required when `source_url` is null),
`selector_hash`, `content_hash`, `snapshot_hash`, `evidence_hash`,
`certification_path`, `provenance_state`, `supersedes`. These make the ledger
self-verifying and lifecycle-aware without changing the 18-field core.

## Compatibility mapping

| Upstream | Ledger field(s) |
|----------|-----------------|
| P62 source ids (SRC_011 malt-review, SRC_012 dramface, SRC_013 whiskymag) | `source_name`, with `source_class = expert_review`, `authority_tier = T2_expert` |
| P63 source classes | `source_class` (enum identical) |
| P63 certification paths A–F | `certification_level` + `certification_path` |
| P63 resolution `verification_source` | recorded as a separate ledger entry with `provenance_state = verified` |
| Sprint 1 `authority/confidence.yaml` | `confidence` |
| Sprint 1 `authority/authority_matrix.yaml` | `authority_tier` |
| Sprint 1 `authority/merge_policies.yaml` | `merge_strategy` |
| Sprint 1 rollup `schemas/evidence.schema.json` | references ledger rows by `evidence_id` |

## Determinism

- `evidence_id` and all hashes are pure functions of their inputs — the same
  observation always yields the same id (idempotent appends are detectable).
- Enumerated fields only; no free-form tiers/classes invented at write time.
- No randomness, no network calls in P64 — this is a standard, not a fetcher.

## No fabrication / read-only

- Absent data ⇒ `field_value = null`; a value is never invented to fill a row.
- P64 defines the ledger; it does not populate it from live sources and never
  writes to `production.db`.

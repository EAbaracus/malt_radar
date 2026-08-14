# Certification Handoff — MR-KEP P68

> Architecture/specification only. No implementation, OCR, parser, AI, or
> production interaction. References P62–P67; does not modify them.

## Certification entry requirements

A unit enters the Certification handoff (state `Certification Ready`) only when
**all** hold:

1. `validation_report.gate ∈ {PASS, PARTIAL}` (P65).
2. Every non-null `metadata` field references ≥1 `evidence_id` present in the
   `evidence_bundle` (evidence-first, P64/P65).
3. `authority_ceiling` respected: no T1-ceiling field certified from a
   T2/T3-only source (P63 `field_rules`, P65 null/enum policy).
4. Per-field `confidence` computed per `authority/confidence.yaml` and present.
5. A deterministic `certification_path` (A–F, P63) is assigned per field.
6. `merge_candidates` retained for any non-selected value (P65; P64 AR-4 no
   silent overwrite).
7. Bundle `checksum` (SHA-256) recorded in the run manifest.

## Handoff bundle contract

The handoff delivers a **`certification_bundle`** (P65 `bundle_spec.md`) whose
`payload.certifications[]` carries, per entity:

- `whisky_key` (deterministic entity key, P65)
- `confidence_min` (min per-field confidence)
- `fields` (canonical values)
- `evidence_index[]` — for every certified field: `field`, `evidence_id`,
  `authority_tier`, `certification_path` (full traceability)
- `audit_status = pending_audit`

The Certification Agent (Sprint 2) consumes this bundle; it does **not** re-fetch
or re-extract. All values are already evidenced.

## Manual-review conditions

Handoff is held for manual review (state → `Rejected` with `manual-review` reason)
when any of:

- `blocked_count >= BLOCKED_CAP` (5) during execution.
- An unresolvable conflict was routed by the Merge Agent (P63 conflict_resolution
  → Audit).
- A field's confidence is below `audit_warn_below` (0.60) but above the reject
  floor.
- `certification_path` would be `D` (conflict-routed) with losers unresolved.

## No production interaction

The handoff produces a **bundle only**. It performs **no** `production.db` write.
Promotion of certified values into production happens exclusively at the
**apply gate** (Sprint 2), which is an explicit, separately-approved transaction
per Malt Radar DB-safety rules (backup → inspect → apply → verify). The
certification handoff is the contract boundary; the apply gate is downstream and
out of Sprint 1 scope.

## AOUS reuse

The handoff is a pure declarative contract: a fixed schema (P65
`certification_bundle`), seven entry predicates, and four review predicates. An
AOUS orchestrator can evaluate it without code generation.

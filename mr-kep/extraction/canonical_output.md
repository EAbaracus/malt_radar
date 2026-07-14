# Canonical Output Model — MR-KEP P65

> Spec/schema only, deterministic, evidence-first, read-only, no fabrication.
> Companion to `extraction/canonical_output.schema.json`.

The Canonical Output is the ONE shape every extractor emits for a single entity.
It has seven parts.

## 1. `entity`
Identity of the subject.
- `entity_type` — distillery / brand / whisky / bottling (P63).
- `entity_id` — stable Malt Radar id (e.g. `W001997`) or `null` if unresolved
  (never fabricated).
- `entity_key` — deterministic normalized key (norm name + vintage + abv) used
  for IoU matching (P63).
- `display_name` — optional human label.

## 2. `metadata`
The canonical field values, already normalized per `authority/field_rules.yaml`.
Keys are the Sprint-1 canonical fields ONLY:
`distillery_name, region, country, abv, age_statement, cask_type, nose, palate,
finish, flavor_axes (7 axes), score, community_rating`.
- Every value is `null` when no source stated it (no fabrication).
- `abv` normalized via `strip_percent_cast_real`; `flavor_axes` are the 7
  canonical axes each in `[0.0, 1.0]`.

## 3. `evidence`
Array of P64 evidence ledger entries (by `evidence_id`) backing the fields. Every
non-null `metadata` field has ≥1 evidence entry. This is the evidence-first link:
no value without evidence.

## 4. `provenance`
Who/what produced this output: `extractor_id`, `extractor_version`, `run_id`,
`generated_at`, `deterministic: true`, `seed`. Enables reproducibility and audit.

## 5. `confidence`
- `overall` — the minimum per-field confidence across non-null fields.
- `per_field` — field → confidence in `[0,1]` (per `authority/confidence.yaml`).

## 6. `certification`
Per-field certification state (P63 paths):
- `certification_level` — uncertified / proposed / certified / rejected.
- `certification_path` — A–F (P63 `certification_paths.md`) or null.
- `authority_tier` — the tier that certified (or null).

## 7. `merge_candidates`
Alternative values NOT selected as the winner, retained for merge/audit (never
dropped — P64 AR-4). Each carries `field_name`, `value`, `source_class`,
`source_name`, `evidence_id`, `reason_not_selected`. Empty when single-source.

## Guarantees

- **Canonical & closed:** `additionalProperties: false` everywhere — no
  extractor may invent fields. New fields require a schema version bump.
- **Deterministic:** same inputs ⇒ identical output (fixed seed, normalized
  values, ordered arrays).
- **Evidence-first & no fabrication:** non-null field ⇒ evidence entry; absent ⇒
  null; alternatives kept in `merge_candidates`.
- **Compatible:** enums for `entity_type`, `source_class`, `certification_*`,
  `authority_tier`, and the 7 flavor axes are identical to P63/P64/Sprint 1.

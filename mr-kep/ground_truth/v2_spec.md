# P69 — Ground Truth Dataset v2 Specification

> **Sprint 1 is ARCHITECTURE FROZEN.** This document defines the **Ground Truth
> Dataset v2** — the gold-standard benchmark every future MR-KEP extractor is
> scored against. It uses **only existing Sprint 1 contracts** and introduces **no
> new interface, schema, or terminology**. Where it needs structure, it reuses
> the canonical fields (P65), entity types (P63/P65), source classes (P63),
> authority tiers (Sprint 1), evidence-ledger shape (P64), certification levels
> (P63), and confidence model (authority/confidence.yaml).
>
> **Documentation only.** No implementation, parser, OCR, extraction, AI, or
> production interaction. Sprint 1 artifacts are NOT modified.

---

## 1. Dataset directory structure

```
mr-kep/ground_truth/                 # (this dir; documentation + dataset manifests)
  README.md                          # pointer to this spec
  v2/
    dataset_metadata.yaml            # §3 dataset-level metadata
    entries/
      <entity_type>/                 # distillery | brand | whisky | bottling (P65 enum)
        <entity_key>.json            # §2 one ground-truth entry per entity
        ...
    splits/
      train.jsonl                    # stratified sample pointers (§11) — references entry keys
      validation.jsonl
      test.jsonl
    reviews/
      <entity_key>.review.yaml       # §6/§15 human-review records
    revisions/
      <entity_key>.rev.yaml          # §5 revision history (append-only)
    certification/
      <entity_key>.cert.yaml         # §7 certification state
    metrics/
      quality_report.yaml            # §16 dataset quality metrics
    CHANGELOG.yaml                   # §14 change history
```

> The directory is a **specification artifact**. The actual `.json` entries are
> produced by the human review + certification workflow (§6–§7), not by any
> automated extractor. No production data is touched.

---

## 2. Entry layout

One entry = the ground-truth canonical record for a single entity. It mirrors the
P65 canonical output shape (so an extractor's output can be diffed field-by-field)
plus a `ground_truth` overlay carrying the verified value, the evidence backing
it, and its certification state.

```yaml
# entries/<entity_type>/<entity_key>.json  (illustrative shape; values are human-verified)
entity_type: whisky                      # P65 enum
entity_key:  "the-glenlivet-12yo-40"     # deterministic key (P65)
display_name: "The Glenlivet 12 Year Old"

# Canonical fields (P65 metadata keys) — the ground truth value, NOT null unless truly absent
ground_truth:
  distillery_name: "The Glenlivet"
  region: "Speyside"
  country: "Scotland"
  abv: 40.0
  age_statement: 12
  cask_type: "American Oak"               # or null if source truly silent
  nose:   "..."                           # verified prose
  palate: "..."
  finish: "..."
  flavor_axes:                           # 7 axes, each 0.0–1.0 or absent (P65)
    smoky: 0.1
    peaty: 0.05
    fruity: 0.7
    sweet: 0.6
    spicy: 0.3
    maritime: 0.1
    sherry: 0.4
  score: 92                              # 0–100 (P65)
  community_rating: null                 # 0–5 or null

# Per-field backing evidence (P64 ledger shape; EV-<16hex> ids)
field_evidence:
  abv:
    value: 40.0
    evidence_id: "EV-1a2b3c4d5e6f7a8b"   # matches P64 evidence_id pattern
    source_class: official               # P63 enum
    source_name: "producer_technical_sheet"
    authority_tier: T1_authoritative
    certification_path: A                # P63
    confidence: 0.98                      # authority/confidence.yaml
  region:
    value: "Speyside"
    evidence_id: "EV-9f8e7d6c5b4a3928"
    source_class: official
    source_name: "SWA_registry"
    authority_tier: T1_authoritative
    certification_path: A
    confidence: 0.95

# Human-verified review state (§6, §15)
review:
  status: reviewed_approved              # P64 review_status enum
  reviewer: "<human-id>"                 # never an AI id (no AI in this phase)
  reviewed_at: "2026-07-15T10:00:00Z"
  notes: "Cross-checked producer sheet + SWA registry."

# Certification vector (P63 levels; P65 certification schema shape)
certification:
  per_field:
    abv:        { certification_level: certified,   certification_path: A, authority_tier: T1_authoritative }
    region:      { certification_level: certified,   certification_path: A, authority_tier: T1_authoritative }
    community_rating: { certification_level: uncertified, certification_path: null, authority_tier: null }
```

Keys used: entity_type/entity_key (P65); canonical fields (P65 metadata); 
evidence_id / source_class / authority_tier / certification_path (P64/P63);
review_status (P64 provenance). **No new keys beyond Sprint 1 vocabulary.**

---

## 3. Dataset metadata

`v2/dataset_metadata.yaml` — dataset-level, deterministic:

```yaml
dataset: ground_truth
version: "2.0.0"                       # semver; see §13
schema_version: "1.0.0"                # P65 canonical_output.schema.json version it conforms to
spec_version: "69.1.0"                 # P69 spec version
created: "2026-07-15"
entity_types: [distillery, brand, whisky, bottling]   # P65 enum
canonical_fields:                       # P65 metadata keys (13)
  - distillery_name - region - country - abv - age_statement - cask_type
  - nose - palate - finish - flavor_axes - score - community_rating
source_classes: [official, regulatory, official_wayback, book, expert_review, structured_metadata, community]  # P63
authority_tiers: [T1_authoritative, T2_expert, T3_community]   # Sprint 1
certification_paths: [A,B,C,D,E,F]      # P63
confidence_model: "authority/confidence.yaml"   # certify_min 0.70, audit_warn 0.60
entry_count: 0                          # filled as entries are certified (§7)
coverage:                              # per entity_type / field fill rate (derived, §16)
  distillery: {}
  brand: {}
  whisky: {}
  bottling: {}
stratification:                        # §11
  strata: [entity_type, source_class_mix, authority_tier, field_density]
  split_ratios: { train: 0.70, validation: 0.15, test: 0.15 }
frozen_refs:                           # explicit Sprint 1 freeze anchors (§4)
  - SPRINT1_ARCHITECTURE_FREEZE.md
  - extraction/canonical_output.schema.json
  - evidence/evidence_schema.json
  - resolution/source_resolution_matrix.csv
  - authority/confidence.yaml
```

---

## 4. Entry metadata

Per-entry metadata block (inside each entry file or a sidecar) — reuses P65
`provenance` shape so reviewers record how the ground truth was established:

```yaml
entry_metadata:
  entity_key: "the-glenlivet-12yo-40"
  entity_type: whisky
  created_at: "2026-07-15T10:00:00Z"
  updated_at: "2026-07-15T10:00:00Z"
  provenance:                          # P65 provenance shape (deterministic=true const)
    extractor_id: "human-ground-truth" # explicit: NOT an automated extractor
    extractor_version: "2.0.0"
    run_id: "GT-v2-0001"
    generated_at: "2026-07-15T10:00:00Z"
    deterministic: true
    seed: 0
  review_status: reviewed_approved     # P64 enum
  certification_status: certified       # per dataset (§7)
  n_evidence: 2
  confidence_min: 0.95                  # min per-field confidence (P65/confidence.yaml)
  strata: [whisky, official_T1, high_density]
```

---

## 5. Revision model

Ground-truth entries are **append-only / versioned**, mirroring P64's immutable
ledger philosophy (no in-place edits of a certified fact).

- Each entry carries `entry_metadata.updated_at` and a `revisions/` history file.
- A correction creates a **new revision** (bump `version` in semver `MAJOR.MINOR.PATCH`);
  the prior value is retained under `superseded_by` (cf. P64 `supersedes`).
- Certified entries are **never silently mutated**: changing a certified value
  requires re-running §6 review + §7 certification, producing a new certification
  record rather than overwriting the old.
- Revision reasons are recorded (typo, new source discovered, source retracted).
- Determinism: same entry_key + same evidence ⇒ same ground-truth value; a
  revision is a new immutable fact, not a mutable cell.

---

## 6. Review workflow

Human-only review (no AI, per restriction). Mirrors P64 `review_status` lifecycle.

1. **Draft** — entry created with `review_status: auto` (placeholder) → immediately
   set to `needs_review`.
2. **Assign** — a human reviewer is assigned (id recorded in `entry_metadata`).
3. **Verify** — reviewer checks each `ground_truth` field against its
   `field_evidence` (source URL / citation + quote). Uses the §15 checklist.
4. **Decide**:
   - `reviewed_approved` → proceed to §7 certification.
   - `reviewed_rejected` → entry quarantined; reason recorded; not in any split.
   - `needs_review` (unresolved) → returned to queue, conflict note attached.
5. **Record** — `reviews/<entity_key>.review.yaml` stores reviewer id, timestamp,
   per-field verdicts, notes. No automated promotion past `needs_review`.

---

## 7. Certification workflow

Reuses P63 certification levels + P65 certification schema shape.

- Pre-condition: `review_status == reviewed_approved`.
- For each field, assign `certification_level` ∈ {uncertified, proposed, certified,
  rejected} and `certification_path` ∈ {A–F, null} per P63 `certification_paths.md`.
- A field is **certified** only if its `confidence >= certify_min (0.70)` and its
  `authority_tier` satisfies the field's `authority_ceiling` (P63 matrix, e.g.
  identity/region/country require T1; sensory requires T2+).
- Output `certification/<entity_key>.cert.yaml` in P65 certification-record shape:
  `whisky_key`, `confidence_min` (≥0.70), `fields`, `evidence_index[]`,
  `audit_status` (pending_audit).
- Dataset-level `entry_count` and `coverage` update only on certification.
- No production write (Sprint 1 apply gate is downstream).

---

## 8. Evidence requirements

Every ground-truth field value MUST satisfy Sprint 1 evidence-first (P64):

- ≥1 `evidence_id` of pattern `EV-<16 hex>` referencing a P64 ledger entry.
- Each evidence entry carries `source_class`, `source_name`, `authority_tier`,
  `retrieval_hash` (SHA-256 binding), and either `source_url` or `source_citation`
  (offline rule).
- Null fields MUST be justified: `null` only when **no source stated the value**;
  the justification is recorded (per P65 "null with explicit reason").
- No fabricated values; a value without traceable evidence is `uncertified`, not
  guessed.

---

## 9. Corroboration rules

Deterministic multi-source agreement (authority/confidence.yaml `agreement`):

- Two **independent** sources (different publisher; same publisher under different
  URLs does NOT count) agreeing exactly → `+0.03` bonus each, capped `+0.10`.
- A field certified from a single T1 source is valid (no agreement needed) but
  carries no agreement bonus.
- Conflicting values → routed to human review (§6); not auto-resolved. Unresolved
  conflict ⇒ `certification_level: rejected` for the conflicting field(s).
- Corroboration is recorded per field in `field_evidence` (n_evidence, list of
  evidence_ids).

---

## 10. Confidence model

Uses **authority/confidence.yaml** unchanged:

- Base by evidence type (primary_source_quote 0.95, bottle_print 0.98,
  expert_quote 0.90, aggregated_link 0.55, inferred 0.20).
- Agreement bonus additive_cap (per_source 0.03, max 0.10, min 2 independent).
- Penalties: missing_evidence −0.50, low_authority_tier −0.30,
  normalization_failed −0.25, conflicting_unresolved −0.15.
- Thresholds: extraction_min 0.20, validation_min 0.40, merge_min 0.50,
  **certify_min 0.70**, audit_warn_below 0.60.
- Rounding: 4 decimals, round_half_even (deterministic, no float drift).
- `confidence_min` of a certified entry = min per-field confidence; must be ≥0.70.

---

## 11. Stratified sampling methodology

To build train/validation/test splits that are representative and bias-controlled:

- **Strata dimensions** (from `dataset_metadata.stratification.strata`):
  1. `entity_type` (distillery/brand/whisky/bottling)
  2. `source_class_mix` (share of T1/T2/T3 evidence per entry)
  3. `authority_tier` (dominant tier of certified fields)
  4. `field_density` (fraction of 13 canonical fields non-null: low/med/high)
- **Deterministic assignment:** sort entries by `entity_key` (stable), then assign
  to train/validation/test by a fixed hash of `entity_key` modulo 100 against
  `split_ratios` (train 70 / val 15 / test 15). Same key ⇒ same split every run
  (reproducible; no randomness).
- **Stratum balance:** report per-stratum counts in `metrics/quality_report.yaml`;
  if any stratum has <5 entries, flag (§16) but do not re-sample with RNG.
- `splits/*.jsonl` store **entry_key pointers only** (not copies) → dataset stays
  single-source-of-truth.

---

## 12. Golden benchmark policy

- The **test split is frozen golden**: once certified, its entries are
  **immutable** and used as the invariant scoring target for every extractor.
- An extractor is scored by field-level exact/normalized match against
  `ground_truth` + `field_evidence`, weighted by `confidence` and `authority_tier`.
- Golden entries may only change via §5 revision (new immutable revision), never
  in place; a changed golden entry bumps dataset `version` MAJOR.
- Leakage guard: an extractor's training must exclude any golden-test entity_key
  (enforced by split pointers, §11).

---

## 13. Version compatibility

- Dataset `version` is semver `MAJOR.MINOR.PATCH`:
  - MAJOR: breaking change to entry layout / canonical-field set / frozen refs.
  - MINOR: added entries, new certified fields within existing schema.
  - PATCH: corrections via §5 revision, metadata fixes.
- `schema_version` pins the P65 canonical_output.schema.json it conforms to
  (currently `1.0.0`). A dataset claiming compatibility MUST match this pin.
- Forward compatibility: newer extractors reading an older v2 dataset MUST ignore
  unknown keys gracefully (P65 `additionalProperties` policy is inherited for the
  ground_truth overlay's non-canonical sections).
- No Sprint 1 interface is redefined by a version bump.

---

## 14. Change history model

`v2/CHANGELOG.yaml` (append-only, human-maintained):

```yaml
- version: 2.0.0
  date: "2026-07-15"
  type: initial
  author: "<human-id>"
  changes:
    - "Established v2 ground-truth spec per P69."
    - "Frozen against Sprint 1 contracts (SPRINT1_ARCHITECTURE_FREEZE.md)."
  frozen_refs: [SPRINT1_ARCHITECTURE_FREEZE.md, extraction/canonical_output.schema.json, ...]
- version: 2.0.1
  date: "2026-07-20"
  type: patch
  author: "<human-id>"
  changes:
    - "Corrected abv for entity_key X via revision (superseded prior)."
```

Each row is immutable; corrections add rows, never edit old ones (P64 append-only).

---

## 15. Human review checklist

Per entry, reviewer confirms:

- [ ] Every non-null `ground_truth` field has ≥1 `EV-<16hex>` evidence_id.
- [ ] Each evidence entry has `source_class`, `source_name`, `authority_tier`,
      `retrieval_hash`; and `source_url` XOR `source_citation`.
- [ ] Null fields have an explicit "source silent" justification.
- [ ] `authority_tier` satisfies the field's P63 `authority_ceiling`
      (identity/region/country ⇒ T1; sensory ⇒ T2+).
- [ ] Per-field `confidence` computed per authority/confidence.yaml and ≥0.70 for
      certified fields; `confidence_min` recorded.
- [ ] Conflicting sources resolved by human (no auto-resolve); unresolved ⇒
      `rejected`.
- [ ] `certification_path` ∈ {A–F, null} assigned per P63.
- [ ] No fabricated values; quotes/citations traceable.
- [ ] Entry belongs to correct `entity_type` and `strata`.
- [ ] Reviewer id + timestamp recorded; `review_status: reviewed_approved`.

---

## 16. Dataset quality metrics

Reported in `metrics/quality_report.yaml` (derived, deterministic):

- `entry_count` (certified).
- `coverage` per entity_type × canonical field (fill rate 0–1).
- `mean_confidence_min` across certified entries.
- `tier_distribution`: count of T1/T2/T3-backed certified fields.
- `stratum_balance`: per-stratum entry counts (§11); flag any <5.
- `evidence_density`: mean evidence_ids per certified field.
- `null_justification_rate`: fraction of null fields with recorded justification.
- `corroboration_rate`: fraction of certified fields with ≥2 independent sources.
- `golden_freeze_integrity`: test-split entries unchanged since freeze (hash check).
- `schema_conformance`: 100% of entries validate against P65 canonical shape +
  P64 evidence_id pattern.

---

## 17. Acceptance criteria

The v2 dataset is **accepted** iff ALL hold:

1. Every entry validates against the P65 canonical field set + P64 evidence_id
   pattern (no schema drift).
2. Every certified field has `confidence >= 0.70` and satisfies its P63
   `authority_ceiling`.
3. Every non-null field has ≥1 valid `EV-<16hex>` evidence entry with
   `source_url` XOR `source_citation`.
4. `review_status == reviewed_approved` and a `reviews/*.review.yaml` exists for
   every certified entry.
5. Test split is frozen (golden) and excluded from any training pointer.
6. Stratified splits reproducible: same `entity_key` ⇒ same split across runs.
7. `CHANGELOG.yaml` covers every version with frozen_refs to Sprint 1.
8. No production data modified; no automated extractor produced any value.

---

## 18. Definition of Done

- [x] Directory structure defined (§1) — reuses Sprint 1 layout conventions.
- [x] Entry layout defined (§2) — mirrors P65 canonical output + P64 evidence.
- [x] Dataset metadata defined (§3) — pins Sprint 1 frozen refs.
- [x] Entry metadata defined (§4) — P65 provenance shape.
- [x] Revision model defined (§5) — append-only, P64-compatible.
- [x] Review workflow defined (§6) — human-only, P64 review_status.
- [x] Certification workflow defined (§7) — P63 levels + P65 cert shape.
- [x] Evidence requirements defined (§8) — P64 evidence-first.
- [x] Corroboration rules defined (§9) — authority/confidence.yaml agreement.
- [x] Confidence model defined (§10) — authority/confidence.yaml (unchanged).
- [x] Stratified sampling defined (§11) — deterministic, reproducible.
- [x] Golden benchmark policy defined (§12).
- [x] Version compatibility defined (§13) — semver, pins P65 schema_version.
- [x] Change history model defined (§14) — append-only CHANGELOG.
- [x] Human review checklist defined (§15).
- [x] Quality metrics defined (§16).
- [x] Acceptance criteria defined (§17).
- [x] No new interface/schema/terminology vs Sprint 1.
- [x] No implementation, parser, OCR, extraction, AI, or production interaction.

---

## Verification — ad-hoc, read-only (NOT a suite)

See delivery message for the PASS/FAIL read-only check.

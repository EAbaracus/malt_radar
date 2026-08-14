# P70 — Ground Truth Candidate Selection

> **Sprint 1 is frozen. P69 is approved.** This document defines the
> **methodology for selecting the first Ground Truth Dataset (v2) candidates** —
> the specific documents/entities that will become human-reviewed, certified
> ground-truth entries. It reuses P67 (qualification), P63 (source classes /
> authority), P65 (canonical fields), and P69 (dataset + golden policy). **No new
> interface, schema, or terminology.**
>
> **Restrictions (enforced):** No implementation. No extraction. No parser. No
> OCR. No AI. No production interaction. Documentation only.

---

## 1. Eligibility criteria

A candidate (a `(document, entity)` pair or a standalone entity) is **eligible**
iff ALL hold:

1. **Classifiable** — the document maps to exactly one of the 12 P67 classes
   (G1 passes); `unknown` → ineligible.
2. **Gate-pass** — the P67 gate (G0→G5) is one of `Extract Later`, `Extract
   Normally`, `High Priority` (i.e. NOT `Reject` / `Archive Only`).
3. **Authority floor** — per P63 `authority_ceiling`, the candidate's field set
   must be certifiable: T1-only fields (identity/region/country) require a T1
   source in the candidate's evidence plan; otherwise only T2/T3_community-allowable fields
   are eligible.
4. **Evidence obtainable** — at least one P62 source in the candidate's class's
   `preferred_source_order` (P63 matrix) is reachable and license-clear
   (`license_risk < 0.6`).
5. **P69-admissible** — the entity_type ∈ {distillery, brand, whisky, bottling}
   (P65/P69) and the candidate targets ≥1 of the 13 canonical fields.
5. **OCR ready** (if class `ocr_need==true`) — G4 passes (text layer or OCR stage
   available, `ocr_quality > 0.0`).

The 12 P67 document classes the candidate's class must be one of: Book, Magazine,
Official PDF, Product Sheet, Marketing Brochure, Auction Catalogue, Archived
Snapshot, Research Paper, Blog Article, Review Website Export, Database Dump,
Scanned Document (`document_classes.md`).

## 2. Exclusion criteria

A candidate is **excluded** if ANY hold:

- P67 gate == `Reject` or `Archive Only` (incl. hard overrides: `license_risk==1.0`,
  `T3_community ∧ identity_usefulness < 0.2`, OCR-blocked scan).
- `license_risk >= 0.6` (P67 G2) — cannot evidence without exposure.
- `unknown` class or insufficient surface attributes to classify (no fabrication).
- Entity type outside the P65/P69 four-type set.
- Duplicate of an already-certified or already-in-review candidate
  (`entity_key` collision within the dataset).
- Source reachable only via blocked/rate-limited path with no fallback in
  `preferred_source_order` (P63 fallback_chains).
- Targets only fields the candidate's authority tier cannot certify (P63 ceiling)
  and has no higher-tier source available. Excludes `T3_community`-only
  candidates whose targeted fields require T1/T2 (e.g. identity/region/country).

## 3. Source precedence

Derived directly from P63 `source_resolution_matrix.csv` `preferred_source_order`
and `fallback_chain` per (entity_type, field_type, field):

- For each canonical field, the candidate's evidence plan follows the field's
  `preferred_source_order` (e.g. identity/region/country →
  `official>regulatory>official_wayback>book`; abv →
  `official>official_wayback>regulatory`; sensory → `expert_review>book`).
- `verification_source` (P63) is the cross-check source used during human review
  (P69 §6/§15).
- `certification_source` (P63) is the authority that may certify the field.
- On source unavailability, follow `fallback_chains.md` deterministically; if the
  chain exhausts, the field is excluded (not guessed).

## 4. Diversity constraints

To avoid a biased benchmark (P69 §11 strata), the first candidate batch MUST
satisfy:

- **Entity-type spread:** at least 1 candidate from each of the 4 entity types.
- **Authority spread:** candidates backed by T1, T2, and T3_community sources all present
  (T3_community only for T3_community-allowable fields like `community_rating`).
- **Source-class spread:** ≥3 distinct P63 source classes represented
  (e.g. official, expert_review, book).
- **Field-coverage spread:** the union of targeted canonical fields covers ≥10 of
  the 13 fields.
- **Document-class spread:** ≥4 of the 12 P67 classes represented.
- **Difficulty spread:** include at least one `High Priority`, one `Extract
  Normally`, and one `Extract Later` (P67 gate) candidate to exercise the full
  qualification range.

## 5. Sampling quotas

Deterministic quotas for the **first batch** (sized for a manageable human-review
load; aligns with P69 §11 splits):

| Bucket | Basis | Quota |
|--------|-------|:----:|
| Total first batch | — | **24 candidates** |
| Per entity type | P69 strata | 6 each (distillery/brand/whisky/bottling) |
| By gate | P67 gate | High Priority ≥8, Extract Normally ≥10, Extract Later ≥6 |
| By authority ceiling | P63 | T1-backed ≥8, T2-backed ≥12, T3_community-only ≥2 |
| By source class | P63 | official ≥6, expert_review ≥6, book ≥4, structured_metadata ≥2, community ≥2 |
| Golden (test) subset | P69 §12 | exactly 6, frozen on certification |

Assignment is deterministic: rank eligible candidates by
`(gate_priority, authority_tier, entity_type, document_class, source_name)`, then
fill quotas in order; ties broken by `entity_key` lexicographic (reproducible).

## 6. Conflict escalation rules

- **Within-candidate field conflict** (two sources disagree on a value): route to
  P69 §6 human review as `needs_review`; never auto-resolve. Unresolved ⇒ field
  `certification_level: rejected` (P63 conflict_resolution).
- **Authority conflict** (T1 vs T2 disagree): T1 wins per P63
  `authority_ceiling`; if T1 absent, escalate to human review.
- **Duplicate `entity_key`** proposed twice: second is excluded (§2).
- **Source retraction / correction**: re-run §1–§5; if a certified entry is
  affected, apply P69 §5 revision (new immutable revision, bump version).
- **Quota impossibility** (e.g. not enough T1 candidates): escalate to human
  steward; do NOT relax authority floors (no fabrication of authority).

## 7. Review assignment workflow

1. **Batch build** — eligibility (§1) + exclusion (§2) + quotas (§5) produce the
   candidate list (deterministic).
2. **Stratify** — tag each candidate with P69 strata
   (entity_type, source_class_mix, authority_tier, field_density).
3. **Assign reviewer** — round-robin across the human reviewer pool by `entity_key`
   hash (deterministic, no AI). Reviewer id recorded in P69 `entry_metadata`.
4. **Review** — per P69 §6/§15 checklist (evidence present, tier ceiling met,
  `confidence >= 0.70`, nulls justified, `review_status == reviewed_approved`).
5. **Certify or reject** — certified ⇒ P69 §7 certification record; rejected ⇒
   quarantined, reason logged, not in any split.
6. **Golden freeze** — the 6 test-subset candidates, once certified, are frozen
   (P69 §12); their `entity_key`s are excluded from any training pointer.

## 8. Expected evidence requirements per candidate

Per P69 §8 / P64 evidence-first, each candidate MUST carry:

- ≥1 `EV-<16hex>` evidence entry per non-null targeted field.
- Each evidence entry: `source_class`, `source_name`, `authority_tier`,
  `retrieval_hash` (SHA-256), and `source_url` XOR `source_citation`.
- `confidence` per `authority/confidence.yaml` (≥0.70 to certify the field).
- For certified fields: `certification_path` ∈ {A–F} (P63) recorded.
- Null targeted fields: explicit "source silent" justification (P65 null policy).
- Minimum evidence depth by authority: T1 field ⇒ ≥1 T1 source; sensory ⇒ ≥1
  expert_review or book; `community_rating` ⇒ ≥1 community source.

## 9. Certification readiness score

A per-candidate **readiness score** (0–100, deterministic) predicts how cleanly
the candidate will certify. Reuses P67 factors + P69 evidence rules:

```
readiness = 100 * (
    0.30 * authority_factor        # P67 Authority weight mapping
  + 0.20 * evidence_depth_factor   # min(1, evidence_ids / targeted_fields)
  + 0.20 * ceiling_satisfaction    # 1.0 if all targeted fields meet authority_ceiling
  + 0.15 * confidence_factor       # min per-field confidence (capped 1.0)
  + 0.15 * review_clarity          # 1.0 if no conflict/unknown, else 0.0
)
```
- `readiness >= 80` → auto-eligible for golden subset (P69 §12).
- `readiness < 50` → flagged for extra reviewer attention (not excluded).
- Pure function of declared constants + evidence plan; no inference.

## 10. Manual-review priority rules

Reviewers process in this deterministic order (highest first):

1. **Golden-subset candidates** (P69 §12) — must be certified first to freeze.
2. **`readiness >= 80` AND `gate == High Priority`** — high-value, low-risk.
3. **Authority-critical** — candidates carrying T1 identity/region/country fields
   (P63 ceiling) — highest knowledge value.
4. **`gate == Extract Normally`** by `readiness` desc.
5. **`gate == Extract Later`** by `readiness` desc.
6. **Tie-break:** `entity_key` lexicographic (reproducible).
Conflicts (§6) and `readiness < 50` items are injected at priority 2 (attention).

---

## Definition of Done

- [x] Eligibility criteria defined (§1) — reuses P67 gates + P63 ceiling + P69 types.
- [x] Exclusion criteria defined (§2) — mirrors P67 hard overrides + no-fabrication.
- [x] Source precedence defined (§3) — P63 preferred_order / fallback_chains.
- [x] Diversity constraints defined (§4) — P69 strata coverage.
- [x] Sampling quotas defined (§5) — deterministic, reproducible.
- [x] Conflict escalation rules defined (§6) — P63 conflict_resolution + P69 revision.
- [x] Review assignment workflow defined (§7) — human-only, P69 §6/§15.
- [x] Expected evidence per candidate defined (§8) — P64/P69 evidence-first.
- [x] Certification readiness score defined (§9) — reuses P67 factors.
- [x] Manual-review priority rules defined (§10) — deterministic ordering.
- [x] No new interface/schema/terminology vs Sprint 1 / P67 / P69.
- [x] Restrictions honored (no impl/extraction/parser/OCR/AI/production).

## Verification — ad-hoc, read-only (NOT a suite)

See delivery message for PASS/FAIL.

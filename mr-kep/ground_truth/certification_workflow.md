# GSD Certification Workflow
## Malt Radar · MR-KEP Ground Truth Dataset

> **Document type:** Design specification — documentation only  
> **Governed by:** AGENTS.md · HERMES.md · P69 (GSD-2 Spec) · P70 (Operational Spec)  
> **Contracts reused:** `evidence.schema.json` · `field_rules.yaml` · `confidence.yaml` · `merge_policies.yaml` · `authority_matrix.yaml`  
> **No new schemas. No implementation. No production writes.**

---

## 1. Purpose

This document defines the **complete human-driven certification workflow** for
promoting a GSD candidate entry from `DRAFT` to `CERTIFIED` status.

Certification is the act of a **human reviewer** verifying, with primary sources,
that every field in a GSD entry is true, traceable, and meets all evidence thresholds
defined in Sprint 1 authority contracts.

**The pipeline never certifies. Only a human reviewer certifies.**

---

## 2. Governing Contracts (Sprint 1 — Frozen)

| Contract | File | Role in Certification |
|----------|------|-----------------------|
| Authority matrix | `mr-kep/authority/authority_matrix.yaml` | Defines T1/T2/T3 tiers |
| Field rules | `mr-kep/authority/field_rules.yaml` | Per-field evidence type and ceiling |
| Confidence model | `mr-kep/authority/confidence.yaml` | Base scores, bonuses, penalties, thresholds |
| Merge policies | `mr-kep/authority/merge_policies.yaml` | Conflict resolution policy names |
| Source priority | `mr-kep/authority/source_priority.yaml` | Tie-breaking within a tier |
| Evidence schema | `mr-kep/schemas/evidence.schema.json` | Structure of every evidence record |
| Certification schema | `mr-kep/schemas/certification.schema.json` | Output artifact structure |

No new schemas are introduced by this workflow.

---

## 3. Workflow Inputs and Outputs

### 3.1 Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `candidate_list.csv` | `mr-kep/ground_truth/` | Pool of 100 candidate whiskies |
| Reviewer | Human | Named individual performing the review |
| Sprint 1 authority contracts | `mr-kep/authority/` | Immutable reference for all decisions |

### 3.2 Outputs

| Output | Location | Description |
|--------|----------|-------------|
| GSD entry JSON | `entries/GSD-NNNN.json` | Certified record |
| History stub | `change_history/GSD-NNNN_history.jsonl` | Created empty at r1 |
| Updated index | `gsd_corpus_index.yaml` | `certification_status` updated |
| Review queue removal | `review_queue/` | PENDING copy deleted on success |

---

## 4. Stage Map

```
 ┌────────────────────────────────────────────────────────────────────────────────┐
 │                    GSD HUMAN CERTIFICATION WORKFLOW                            │
 └────────────────────────────────────────────────────────────────────────────────┘

 [CANDIDATE POOL]
    candidate_list.csv
         │
         │ Reviewer selects next entry
         ▼
 ══════════════════════════════════════════
 STAGE 1 — ENTRY CREATION            DRAFT
 ══════════════════════════════════════════
  1a. Assign GSD-NNNN (next available ID)
  1b. Populate product_identity from official source
  1c. Populate official_authority (T1 URL)
  1d. Create change_history JSONL stub (empty)
  1e. Set: review_status=DRAFT, revision=r1
  1f. Save: entries/GSD-NNNN.json
  1g. Add to index with status=DRAFT
         │
         ▼
 ══════════════════════════════════════════
 STAGE 2 — IDENTITY VERIFICATION
 ══════════════════════════════════════════
  2a. Open official_authority.official_url
  2b. Confirm: distillery, country, region
  2c. Record T1 evidence record for each identity field
  2d. Apply normalization: trim_canonical_case / canonical_region_enum / iso_country_enum
  2e. If conflict → apply reject_on_conflict → HOLD
         │
         │ Identity confirmed
         ▼
 ══════════════════════════════════════════
 STAGE 3 — METADATA VERIFICATION
 ══════════════════════════════════════════
  3a. Locate bottle_print or primary_source_quote for: abv, age_statement, cask_type
  3b. Record T1 evidence record for each metadata field
  3c. Normalize: strip_percent_cast_real (abv) · extract_first_integer_year (age)
               canonical_cask_enum (cask_type)
  3d. If ABV conflict > 0.1% between T1 sources → reject_on_conflict → HOLD
         │
         │ Metadata confirmed
         ▼
 ══════════════════════════════════════════
 STAGE 4 — TASTING NOTE SOURCING
 ══════════════════════════════════════════
  4a. Locate T2 expert review: nose, palate, finish
  4b. Preferred source: WhiskyFun (priority 10 per source_priority.yaml)
  4c. Record T2 evidence record (expert_quote) for each sensory field
  4d. Set is_primary_note: true on chosen review
  4e. Locate second T2 source if first is Whisky Advocate (corroboration rule)
  4f. Add additional_notes if second source found
         │
         │ Primary T2 note confirmed
         ▼
 ══════════════════════════════════════════
 STAGE 5 — FLAVOR AXIS DERIVATION
 ══════════════════════════════════════════
  5a. Derive 7-axis scores from T2 note(s)
  5b. Apply: canonical_7axis normalization
  5c. Permitted derivation methods:
        expert_consensus   → ≥2 independent T2 sources agree
        single_expert      → 1 T2 source; axes_locked=false unless confidence ≥ 0.85
        inferred_from_notes→ axes not stated; derived from descriptors; requires ≥2 notes
  5d. Set axes_locked appropriately
  5e. Record T2 evidence record per axis
  5f. Confirm: all 7 axes non-null and in [0.0, 10.0]
         │
         │ All axes populated
         ▼
 ══════════════════════════════════════════
 STAGE 6 — CONFIDENCE COMPUTATION
 ══════════════════════════════════════════
  6a. identity    = min(conf(distillery), conf(country), conf(region)) + agreement_bonus
  6b. metadata    = min(conf(abv), conf(age_statement), conf(cask_type))
  6c. flavor      = mean(conf(smoky..sherry))
  6d. tasting_notes = min(conf(nose), conf(palate), conf(finish))
  6e. authority   = 1.0 − (0.30 × tier_violations) − (0.15 × missing_tier_records)
  6f. overall     = min(identity, metadata, flavor, tasting_notes, authority)
  6g. Round all values: 4dp, round_half_even
         │
         │ Confidence computed
         ▼
 ══════════════════════════════════════════
 STAGE 7 — GATE EVALUATION (10 gates)
 ══════════════════════════════════════════
  G1  Identity completeness
  G2  T1 authority present and URL reachable
  G3  Metadata fully evidenced (T1)
  G4  T2 primary note present and URL reachable
  G5  All 7 flavor axes populated
  G6  No inferred-only field
  G7  All source_urls reachable (HTTP 200 or archived)
  G8  No price field anywhere in record
  G9  confidence.overall ≥ 0.70
  G10 confidence.authority ≥ 0.85

  IF all 10 PASS → proceed to STAGE 8
  IF any FAIL    → entry status → HOLD (see §6)
         │
         │ All 10 gates PASS
         ▼
 ══════════════════════════════════════════
 STAGE 8 — CERTIFICATION SIGN-OFF
 ══════════════════════════════════════════
  8a. Set review_status = VERIFIED
  8b. Set certification_status = CERTIFIED
  8c. Set reviewed_at = current ISO 8601 datetime
  8d. Set reviewer = reviewer identifier
  8e. Assign benchmark_split: train | validation | test
  8f. Assign certification_tier: Gold | Silver | Bronze
  8g. Save final entries/GSD-NNNN.json (r1)
  8h. Append empty line to change_history/GSD-NNNN_history.jsonl
  8i. Update gsd_corpus_index.yaml: status=CERTIFIED
  8j. Remove review_queue/GSD-NNNN_r1_PENDING.json if present
         │
         ▼
 ══════════════════════════════════════════
 CERTIFIED — Entry locked as gold reference
 ══════════════════════════════════════════
```

---

## 5. Stage-by-Stage Time Estimates

These estimates guide reviewer capacity planning. All times assume a prepared
reviewer with browser access to T1 and T2 sources.

| Stage | Estimated Time | Primary Activity |
|-------|---------------|-----------------|
| 1 — Entry creation | 10 min | Open template, assign ID, fill header |
| 2 — Identity verification | 15 min | Open official URL, confirm 3 fields, write 3 evidence records |
| 3 — Metadata verification | 20 min | Find bottle spec, confirm ABV/age/cask, normalize and record |
| 4 — Tasting note sourcing | 20 min | Find T2 review, copy nose/palate/finish, verify URL |
| 5 — Flavor axis derivation | 25 min | Score 7 axes from note(s), record 7 evidence records |
| 6 — Confidence computation | 10 min | Apply confidence.yaml formulas to all fields |
| 7 — Gate evaluation | 10 min | Work through 10-gate checklist |
| 8 — Sign-off | 10 min | Set statuses, assign split, update index |
| **Total per entry** | **~2 hours** | |

**Phase 1 estimate (100 CERTIFIED entries):** ~200 reviewer-hours.

---

## 6. HOLD Protocol

When any gate fails, the entry enters HOLD. This is not a rejection — it means
the reviewer needs more information or source material.

### 6.1 HOLD Record

The entry header must record the failing gate:

```json
"review_status": "HOLD",
"hold_reason": "G7 — source_url for abv field returned 404; archived URL not found",
"hold_since": "2026-07-14T10:00:00Z",
"hold_gate": "G7"
```

### 6.2 HOLD Resolution Steps

```
1. Record the failing gate and reason in the entry header.
2. Move the working copy to review_queue/GSD-NNNN_r1_PENDING.json.
3. Do NOT update gsd_corpus_index.yaml certification_status (it stays HOLD).
4. Reviewer researches the specific blocking issue.
5. When issue resolved, return entry to PENDING_REVIEW state.
6. Re-run the checklist from the failing gate onward.
7. If all gates now PASS, proceed to STAGE 8.
```

### 6.3 HOLD Escalation

If a HOLD cannot be resolved within 5 review sessions:
- Move entry to `rejected/GSD-RJCT-NNNN.json`.
- Record `rejection_reason` and `rejected_at`.
- Mark GSD-NNNN ID as permanently retired in the index.
- Select a replacement candidate from `candidate_list.csv`.

---

## 7. Update Workflow (Post-Certification)

When new evidence contradicts a CERTIFIED entry:

```
1. Set certification_status → REQUIRES_UPDATE in the index.
2. Create review_queue/GSD-NNNN_rN_PENDING.json (copy of current certified entry).
3. Increment revision: rN → r(N+1) in the PENDING copy.
4. Apply the change to the PENDING copy only.
5. Re-run only the affected gates (not all 10 unless scope is wide).
6. If affected gates PASS:
   a. Recompute confidence.
   b. Set certification_status → CERTIFIED, revision → r(N+1).
   c. Append prior revision snapshot to change_history JSONL.
   d. Replace entries/GSD-NNNN.json with PENDING copy.
   e. Delete PENDING copy.
   f. Update index.
7. If any gate FAILS → HOLD.
```

---

## 8. Batch Certification Order

To maximise early corpus usefulness, certify in this priority order:

| Round | Entries | Criteria |
|-------|---------|----------|
| Round 1 | 15 entries | Priority 1 test-split entries (hidden benchmark) |
| Round 2 | 20 entries | Priority 1 train-split entries (Scotland, Japan) |
| Round 3 | 20 entries | Priority 1 validation-split entries (USA, Ireland) |
| Round 4 | 25 entries | Priority 2 entries across all countries |
| Round 5 | 20 entries | Phase 1 completion batch (fills stratum gaps) |

---

## 9. Definition of Done

This certification workflow is **done** when:

```
[ ] 100 CERTIFIED entries exist in entries/ directory
[ ] gsd_corpus_index.yaml shows certified_entries = 100
[ ] All CERTIFIED entries: confidence.overall ≥ 0.70
[ ] All CERTIFIED entries: confidence.identity ≥ 0.90
[ ] Zero entries with price fields
[ ] Zero entries with inferred-only facts
[ ] All change_history JSONL stubs present (even if empty)
[ ] Stratification coverage report confirms corpus_balanced in 5 of 7 strata
[ ] This document signed off by project owner
```

---

## 10. GO / NO-GO

### Workflow Design Verification

| Check | Status |
|-------|--------|
| Only Sprint 1 contracts reused | ✅ PASS |
| No new schemas introduced | ✅ PASS |
| No implementation code written | ✅ PASS |
| No production writes | ✅ PASS |
| Human-first (pipeline cannot certify) | ✅ PASS |
| Evidence-first (every fact requires quote + URL) | ✅ PASS |
| Deterministic (same inputs → same outputs) | ✅ PASS |
| All 10 gates inherited from P69 | ✅ PASS |
| production.db SHA-256 unchanged | ✅ PASS |

```
STATUS: GO — Workflow design complete.
```

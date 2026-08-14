# Certification Evidence Review Bundle â€” P305.5

**Mode:** READ ONLY exposure Â· no code changes Â· no staging/production writes Â· no certification changes Â· no promotion
**Date:** 2026-07-18
**Purpose:** Expose all evidence required for a human certification decision. **This document does NOT decide anything.** Every decision cell is left blank for the reviewer.

**Candidate:** `evidence_id = EDR-b6108f7ac8d252af` (`normalized_name = "ardbeg 10"`)

---

## 1. Candidate Identity

| Field | Value (verified from `staging_editorial.db`, read-only) |
|---|---|
| `evidence_id` | `EDR-b6108f7ac8d252af` |
| `normalized_name` | `ardbeg 10` |
| `raw_name` | `Ardbeg 10` |
| `source_id` | `whiskyfun` |
| current **certification state** | `HOLD` |
| current **provenance state** | `staging_unverified` |
| `match_status` | `unmatched` |
| `authority_tier` | `T2_expert` |
| `extraction_method` | `structured_extraction` |
| `evidence_confidence` | `1.0` |
| `score_value` | `92.0` |

---

## 2. Evidence Summary

- **Source artifact:** `mr-kep/fixtures/sample_whisky.json` (pre-produced real fixture; not a live scrape)
- **Source class / authority tier:** `T2_expert`
- **Qualification:** 1 unit, `in_scope=True`
- **Extraction Execution:** `State.COMPLETED`, 10 evidence records
- **Canonicalization / Flavor Mapping:** 7 canonical axes resolved (`d4_reducer.flavor_mapper.FlavorMapper`)
- **Deduplication:** `SemanticDeduplicator` â†’ `duplicate=False`
- **Field coverage:** all 10 evidence fields present, each confidence â‰¥ `CERTIFY_MIN (0.70)` (`evidence_confidence = 1.0`)
- **Certification aggregate:** `HOLD` (per `runtime_report.json` â†’ `certification.state = "HOLD"`, `fields = 10`)

---

## 3. Field-Level Review Table

For the six T1-ceiling identity fields. `authority_tier` is the **actual** tier from the evidence; `required_tier` is the engine ceiling (`FIELD_CEILING`). `confidence` reflects the extracted/normalized value (`evidence_confidence = 1.0`). `decision_needed` is left **blank** for the human.

| field | value | confidence | authority_tier (actual) | required_tier | decision_needed |
|---|---|---|---|---|---|
| `distillery_name` | `Ardbeg` | 1.0 | `T2_expert` | `T1_authoritative` |  |
| `region` | `Islay` | 1.0 | `T2_expert` | `T1_authoritative` |  |
| `country` | `Scotland` | 1.0 | `T2_expert` | `T1_authoritative` |  |
| `abv` | `46.0` | 1.0 | `T2_expert` | `T1_authoritative` |  |
| `age_statement` | `10` | 1.0 | `T2_expert` | `T1_authoritative` |  |
| `cask_type` | `Ex-Bourbon` | 1.0 | `T2_expert` | `T1_authoritative` |  |

> The five non-identity fields (`nose`, `palate`, `finish`, `flavor_axes`, `score`) have a `T2_expert` ceiling and are therefore certifiable under the actual `T2_expert` authority. Only the six identity fields above force the `HOLD`.

---

## 4. Flavor Evidence

- **Seven-axis vector** (real `flavor_vector_json`):

  ```json
  {"smoky": 0.9, "peaty": 0.85, "fruity": 0.3, "sweet": 0.2, "spicy": 0.5, "maritime": 0.8, "sherry": 0.0}
  ```

- **Source confidence:** `1.0`
- **Normalization notes:** all 7 canonical axes present and within valid range [0,1]; `maritime`/`smoky`/`peaty` dominant (consistent with an Islay peated single malt); `sherry` = 0.0 (no sherry-cask evidence in source).

---

## 5. Deduplication Review

- **Duplicate status:** `duplicate=False` (no semantic duplicate detected)
- **Match confidence:** `None` (`match_status = unmatched`)
- **Linked candidates:** none â€” the record is not linked to a master whisky entry

---

## 6. Certification Blocker Explanation

**Why HOLD exists:**
The certification engine (`certification_engine/__init__.py`) returns `HOLD` whenever any field reaches `proposed` (Path C). Path C applies when `confidence â‰¥ 0.70` but the evidence authority does **not** satisfy the field ceiling. The six identity fields above require `T1_authoritative`, but the evidence carries `authority_tier = T2_expert`. Therefore those six fields cap at `proposed` â†’ aggregate state = **HOLD**. This is the **correct, expected** behavior of the deterministic engine, not a defect.

Separately, `provenance_state = staging_unverified` because the runtime writes that flag by design and **no provenance-ratification step exists** in the pipeline to flip it. This is a procedural gap, not a code bug.

**What human decision resolves it:**
- Accept the `T2_expert` evidence for the T1-ceiling identity fields (documented via the P305 `certification_decision_form.md` + authority override policy), **or**
- Promote the authority tier for those fields (explicit human approval), **and**
- Ratify provenance (`staging_unverified â†’ verified`) via the provenance ratification form.

Until those are recorded, the candidate stays **PENDING HUMAN CERTIFICATION**.

---

## 7. Reviewer Questions

- [ ] **Accept T2 evidence?** (accept `T2_expert` source for the six T1-ceiling identity fields)
- [ ] **Ratify provenance?** (`staging_unverified â†’ verified`; validate `content_hash` against source)
- [ ] **Approve certification?** (record explicit GO to move HOLD â†’ approvable)

_All questions are left pending. No decision is recorded in this bundle._

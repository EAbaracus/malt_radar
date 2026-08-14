# Certification Diagnostic Report â€” P305.7

**Mode:** READ ONLY Â· No decisions made Â· No state changes
**Date:** 2026-07-18
**Candidate:** `evidence_id = EDR-b6108f7ac8d252af` Â· `normalized_name = ardbeg 10`
**Purpose:** Explain exactly why certification = HOLD, so you can make an informed decision.

---

## 1. Certification Execution Trace

### Engine walk (from `certification_engine/__init__.py`, verified)

The engine evaluates every field in the evidence ledger. For each field it runs `determine_certification_path()`:
```
evidence_entries  â†’  Path D? (conflict?)     â†’ if yes: REJECTED
                     Path F? (no evidence?)   â†’ if yes: REJECTED
                     Path E? (conf < 0.70?)   â†’ if yes: REJECTED
                     satisifies ceiling?       â†’ if yes: CERTIFIED (Path A)
                     else (conf â‰¥ 0.70 but authority below ceiling)
                                              â†’ PROPOSED (Path C)
```

Then `aggregate_certification()`:
```
any REJECTED â†’ BUG?           â†’ aggregate = REJECTED
any PROPOSED â†’ NEEDS REVISION â†’ aggregate = HOLD
else                            aggregate = CERTIFIED
```

### What happened for this candidate

| Step | Result |
|---|---|
| Evidence ledger size | 10 fields |
| Conflicts found (Path D) | 0 (none) |
| Fields with no evidence (Path F) | 0 (all 10 present) |
| Fields below confidence threshold (Path E) | 0 (all â‰¥ 0.70) |
| Fields that **satisfy** authority ceiling (Path A â†’ CERTIFIED) | **5 fields** (nose, palate, finish, flavor_axes, score) |
| Fields that **do NOT** satisfy authority ceiling (Path C â†’ PROPOSED) | **6 fields** (distillery_name, region, country, abv, age_statement, cask_type) |
| Aggregate result | **HOLD** (because 6 fields are PROPOSED) |

### The rule that failed

The check `_tier_rank(authority_tier) <= _tier_rank(ceiling)`:

```
_tier_rank("T2_expert")   = 2    (the evidence's actual authority)
_tier_rank("T1_authoritative") = 1    (the field's required ceiling)

2 <= 1 â†’ FALSE â†’ authority is TOO LOW for this ceiling
```

**This is NOT a bug.** It is correct, deterministic engine behavior. The engine is designed to hold when the evidence's authority tier is below the field's ceiling.

---

## 2. Evidence Gap Analysis

### Per-field: actual authority vs required ceiling

| field | value | evidence source | authority tier (actual) | required tier (ceiling) | gap |
|---|---|---|---|---|---|
| distillery_name | Ardbeg | whiskyfun (fixture line 24) | T2_expert | **T1_authoritative** | authority below ceiling |
| region | Islay | whiskyfun (fixture line 25) | T2_expert | **T1_authoritative** | authority below ceiling |
| country | Scotland | whiskyfun (fixture line 26) | T2_expert | **T1_authoritative** | authority below ceiling |
| abv | 46.0 | whiskyfun (fixture line 27, raw: "46%") | T2_expert | **T1_authoritative** | authority below ceiling |
| age_statement | 10 | whiskyfun (fixture line 28) | T2_expert | **T1_authoritative** | authority below ceiling |
| cask_type | Ex-Bourbon | whiskyfun (fixture line 29) | T2_expert | **T1_authoritative** | authority below ceiling |

### Reference: why these fields require T1

`FIELD_CEILING` (from `certification_engine/__init__.py`, lines 36â€“49):
- `T1_authoritative`: `distillery_name, region, country, abv, age_statement, cask_type` â€” identity/producer attributes that typically require distillery, government, or brand-authority sources.
- `T2_expert`: `nose, palate, finish, flavor_axes, score` â€” sensory/expert-review attributes that can be provided by an independent reviewer.

The 5 fields with `T2_expert` ceiling (nose, palate, finish, flavor_axes, score) **did certify successfully** under the whiskyfun T2 authority. They are NOT the blockers.

---

## 3. Matching Diagnosis

| Attribute | Value |
|---|---|
| normalized_name | `ardbeg 10` |
| match attempts | **0** â€” no match algorithm was executed |
| candidates considered | none |
| why unmatched | The orchestrator (`kep_runtime/run.py`) writes `match_status = "unmatched"` by design. No matching/linking step exists in the current pipeline. The record was inserted into staging as an independent entry, not linked to a master whisky record. |
| match_confidence | `None` â€” no matching was attempted |

**This does not block certification.** The `match_status` is independent of certification state. A record can be certified and still unmatched (the master-linking happens at a separate stage). However, promotion into production would ideally require the link to be resolved.

---

## 4. Confidence Breakdown

| Metric | Value | Notes |
|---|---|---|
| All field confidences | `1.0` | Every evidence record has confidence = 1.0 |
| `evidence_confidence` | `1.0` | Overall evidence confidence from staging row |
| Certification threshold (`CERTIFY_MIN`) | `0.70` | Hard-coded in `certification_engine/__init__.py` line 30 |
| Failed thresholds | **0** | No field failed the confidence threshold |
| Minimum confidence across all fields | `1.0` | All â‰¥ 0.70 |

**The confidence threshold is NOT the problem.** No field is below 0.70. The HOLD is caused by the authority ceiling, NOT by insufficient confidence.

---

## 5. Human Decision Options

### Option A: Accept (approve certification as-is)

- **What you'd be accepting:** The six T1-ceiling identity fields were provided by a T2_expert source (whiskyfun). These values are correct (distillery=Ardbeg, region=Islay, country=Scotland, abv=46%, age=10, cask=Ex-Bourbon â€” all internally consistent and verifiable). You'd be accepting that for THIS candidate, the T2 evidence is sufficient.
- **What changes:** Certification would move from PROPOSED â†’ APPROVED (documented in the approval record). The staging row itself would still have `provenance_state = staging_unverified` and `certification = HOLD` in the DB (the engine is not re-run; the approval is recorded externally).
- **Risk:** Low â€” the values match the source and profile; you can see the source snippets in P305.6 Â§3.

### Option B: Reject

- **What you'd be rejecting:** The entire candidate. HOLD remains. No promotion path.
- **What would need to change for re-approval:** You'd need new evidence from a T1 authority (e.g., Ardbeg distillery official data, SWA registration, government records) for the six identity fields.
- **When this makes sense:** If you believe T2 blog evidence is categorically unsuitable for distillery/region/abv data.

### Option C: Request additional evidence

- **What additional evidence would resolve HOLD:** A T1-authority source for the six identity fields. Examples:
  - Official distillery page (ardbeg.com) for distillery_name, region, country
  - SWA (Scotch Whisky Association) registration for age_statement, abv, cask_type
  - UK government labelling database
- **What happens:** The pipeline would need to be re-run with this T1 evidence to achieve CERTIFIED.

### Summary

| Decision | Effect | What's needed |
|---|---|---|
| Accept | HOLD â†’ APPROVED (documented) | Your explicit GO + reviewer identity |
| Reject | HOLD stays; candidate blocked | New T1 evidence for re-attempt |
| Request more evidence | Pipeline re-run with T1 source | Acquisition of official T1 source |

---

**This report is diagnostic only. No decision has been made. Certification remains HOLD. Provenance remains staging_unverified.**

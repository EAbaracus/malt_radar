# Batch Review & Feedback Loop â€” P322

**Mode:** READ ONLY + DOCUMENTATION ONLY Â· No production writes Â· No certification changes Â· No new promotion
**Date:** 2026-07-18

---

## 1. Batch Summary

| Field | Value |
|---|---|
| `batch_id` | `PROMO-BATCH-20260718-001` |
| Total candidates considered | 4 |
| Approved + promoted | **3** (Ardbeg 10yo, Talisker 10yo, Lagavulin 16yo) |
| Held | **1** (Clynelish 14yo) |
| Human reviewer | `eltun` |
| Precedent used | `PROMO-20260718-001` â€” single candidate approval path |

### Production impact

| Table | Before | After | Delta |
|---|---|---|---|
| flavor_evidence | 990 | **993** | +3 |
| tasting_notes | 1,849 | **1,852** | +3 |
| promotion_audit_log | 3 | **4** | +1 |
| whiskies | 4,749 | 4,749 | 0 (expected) |
| integrity_check | ok | ok | âœ… |

### Execution timeline

| Step | Status |
|---|---|
| Staging updates (match_status, provenance) | âœ… |
| Batch manifest generation | âœ… |
| Pre-promotion backup | âœ… |
| EditoriaPromotionWriter.execute() | âœ… 3 rows |
| tasting_notes insert | âœ… 3 rows |
| promotion_audit_log insert | âœ… 1 row |
| Post-promotion validation | âœ… integrity=ok |
| Rollback triggered | âŒ Not needed |

---

## 2. Approved Candidate Analysis

### Ardbeg 10 Year Old (W001152)

| Factor | Assessment |
|---|---|
| Identity strength | 3/8 fields VERIFIED, 4 MISSING (production data gaps) |
| Match confidence | HIGH â€” name + age (10) uniquely identify |
| Evidence quality | 0.85 heuristic â€” adequate |
| Flavor vector | smoky+peaty dominant â€” consistent with Ardbeg |
| Risk | LOW |

**What worked:** Evident match by name+age. Source `whiskynotes_be` is credible. Flavor vector coherent.

**What could improve:** Production record W001152 missing distillery_id, region, country. Filling these production data gaps would strengthen future identity verification for all W-series candidates.

### Talisker 10 Year Old (W000976)

| Factor | Assessment |
|---|---|
| Identity strength | **8/8 fields VERIFIED** â€” strongest in batch |
| Match confidence | HIGH â€” brand, distillery (D0004), region (Islands), country (Scotland) all confirmed |
| Evidence quality | 0.85 heuristic â€” adequate |
| Flavor vector | spicy+maritime dominant â€” consistent with Talisker |
| Risk | LOW |

**What worked:** Production record W000976 has distillery_id linking to distilleries table, which provided region, country, and brand. This made identity verification trivial.

**What could improve:** ABV 45.8% from candidate matches official Talisker 10yo bottling, but production record stores `None`. Adding ABV to production records would cross-validate.

### Lagavulin 16 Year Old (W001100)

| Factor | Assessment |
|---|---|
| Identity strength | 3/8 fields VERIFIED, 4 MISSING (production data gaps) |
| Match confidence | HIGH â€” name + age (16) uniquely identify |
| Evidence quality | 0.85 heuristic â€” adequate |
| Flavor vector | **6 active axes** (richest in batch), peaty=0.5, sherry=0.33 |
| Risk | LOW |

**What worked:** Richest flavor profile in batch. ABV 43.0% matches official Lagavulin 16yo standard (independently verifiable).

**What could improve:** Same production data gap as Ardbeg â€” W001100 has no distillery linkage. Sherry cask influence (0.33) is notable and could be cross-referenced with cask type data if production had that field.

---

## 3. Held Candidate Analysis

### Clynelish 14 Year Old (W000496)

| Factor | Assessment |
|---|---|
| Match status | `manual_review` â†’ BLOCKED the promotion writer |
| Provenance | `staging_unverified` â†’ set to `HOLD` |
| Identity strength | 3/8 fields VERIFIED, 4 MISSING (same production data gap) |
| Match confidence | HIGH â€” name + age (14) uniquely identify |
| Evidence quality | 0.85 heuristic â€” adequate |
| Flavor vector | sweet+maritime dominant â€” consistent with Clynelish waxy profile |
| Risk | LOW (same profile as approved candidates) |

### Why held

Clynelish was held for one reason: **no human decision was made.** The user only explicitly approved 3 candidates (Ardbeg, Talisker, Lagavulin). Clynelish's `match_status` remained `manual_review` and its `provenance_state` was set to `HOLD` as a default, which the promotion writer correctly rejected.

**Classification: NOT a data quality issue.** Clynelish is structurally identical to the 3 approved candidates â€” same T2_expert authority, same heuristic extraction (0.85), same production data gap pattern. The hold was a scheduling/routing gap, not an evidence rejection.

---

## 4. Hold Reason Classification

| Hold reason | Candidates affected | Frequency | Remediation |
|---|---|---|---|
| **No human decision made** | Clynelish 14yo (W000496) | 1 / 4 | Add explicit "DECISION REQUIRED" flag for candidates that are structurally ready but lack human review. If batch approval is partial, process should prompt for remaining candidates. |
| **match_status = manual_review** | Clynelish 14yo (W000496) | 1 / 4 | Implement automated resolution: if match_score â‰¥ 0.85 and normalized names align, auto-promote to `exact`. Only escalate to manual_review when ambiguity exists. |
| **provenance = staging_unverified** | **All** candidates pre-approval | 4 / 4 | Add a "ratify all passing" command that batch-updates provenance for all candidates that have passed evidence review. Currently each needs individual update. |

### Underlying pattern

The hold mechanism worked correctly â€” the writer properly rejected a candidate that didn't meet promotable criteria. However, Clynelish was functionally equivalent to the 3 approved candidates. The hold was procedural (no human action) rather than evidentiary (data defect).

**Recommendation:** In future batches, if N candidates pass evidence review and the reviewer approves N-1, automatically prompt: "Clynelish 14yo (W000496) has the same evidence profile as approved candidates â€” approve to batch, hold, or reject?"

---

## 5. Evidence Gaps

### Gap 1: Heuristic extraction formatting artifacts

| Issue | Frequency | Example | Impact |
|---|---|---|---|
| Leading colon in sensory notes | 4 / 4 batch candidates | `": intense peat, smoke and citrus."` | Minor â€” data is usable but has cosmetic artifact |
| Missing `conclusion` field | 4 / 4 | â€” | Low â€” nose/palate/finish are sufficient |
| Missing `published_date` | 4 / 4 | â€” | Low â€” not required for evidence |
| Missing `author` (in some) | 2 / 4 | Clynelish, Talisker, Lagavulin | Low â€” source domain is sufficient attribution |

**Action:** Add a post-extraction cleaning step to strip leading colons from sensory notes. This is a simple string operation but would improve data quality for all heuristic-extracted candidates.

### Gap 2: Production data gaps

| Missing field | Affected whisky_ids | Impact on verification |
|---|---|---|
| distillery_id | W001152, W000496, W001100 | Identity relies solely on name+age matching |
| region | W001152, W000496, W001100 | Cannot verify region claim |
| country | W001152, W000496, W001100 | Cannot verify country claim |
| brand | W001152, W000496, W001100 | No brand cross-reference |
| ABV | All W-series | Cannot cross-validate candidate ABV claims |

**Action:** Enrich production records with distillery_id for W001152, W000496, and W001100. This would upgrade identity verification from 3/8 to 7/8 VERIFIED for these candidates (matching Talisker's verification level).

### Gap 3: Match resolution for unmatched candidates

| Candidate | Status | Issue |
|---|---|---|
| EDR-b6108f7ac8d252af (ardbeg 10) | Already promoted | Was promoted while `match_status=unmatched` via human GO override |
| EDR-06ed8d58194bf156 (highland park 12) | Already promoted (pre-P313) | Same pattern |
| EDR-4e3ddd35a9b701e2 (glenmorangie 18) | Already promoted (pre-P313) | Same pattern |

These 3 candidates were promoted without ever having their `match_status` resolved to `exact`. The staging records still show `unmatched` or `exact` but `staging_unverified`. This creates a disconnect between staging state and production state.

**Action:** After promotion, update staging to reflect final state: `match_status=exact`, `provenance_state=APPROVED`, `promotion_status=PROMOTED`.

---

## 6. Extraction Improvements

### Current state

| Method | Candidates | Confidence | Artifacts | Use case |
|---|---|---|---|---|
| `structured_extraction` | 1 (EDR-b6108f7ac8d252af) | 1.0 | None | Manual, high-quality extraction |
| `heuristic` | 6 (all batch candidates) | 0.85 | Leading colons, missing optional fields | Automated, bulk extraction |

### Recommendation 1: Post-extraction cleanup

Add a normalization step after heuristic extraction:

```python
# Strip leading colon + space from sensory notes
for field in ["nose", "palate", "finish"]:
    if value.startswith(": "):
        value = value[2:]
```

This is a zero-risk change that would clean all 4 batch candidates' sensory notes.

### Recommendation 2: Extraction method scoring

Heuristic extraction produces usable data but has systemic artifacts. Consider:

- `structured_extraction` = 1.0 confidence (human-reviewed or precise parsing)
- `heuristic` = 0.85 confidence (reliable but may have formatting issues)
- Add a `cleaned_heuristic` = 0.90 confidence (heuristic + post-processing)

### Recommendation 3: Mandatory field checklist

Define minimum viable evidence:

| Field | Required for promotion? | Current coverage |
|---|---|---|
| score_value | âœ… Yes | âœ… 100% |
| nose | âœ… Yes | âœ… 100% |
| palate | âœ… Yes | âœ… 100% |
| finish | âœ… Yes | âœ… 100% |
| flavor_vector (7 axes) | âœ… Yes | âœ… 100% |
| conclusion | âŒ Optional | 0% |
| published_date | âŒ Optional | 0% |
| author | âŒ Optional | ~50% |

The current mandatory set is adequate. No field should be added to "required" without a clear use case.

---

## 7. Future Certification Recommendations

### Recommendation A: Batch-level identity verification

**Problem:** Each candidate's identity was verified independently against production, but batch-level patterns (e.g., "all W-series records lack distillery_id") were only visible after manual review.

**Solution:** Add a pre-batch data quality report that checks all candidates against production and surfaces systemic gaps before human review.

### Recommendation B: Automatic match resolution

**Problem:** `match_status = manual_review` requires human action even when evidence is clear.

**Solution:** Implement automated match resolution logic:

```python
if match_confidence >= 0.85 and all(
    field in production_whiskies(normalized_name)
    for field in ["name", "age", "type"]
):
    auto_resolve_to("exact")
```

This would have auto-resolved all 4 batch candidates to `exact`, removing the need for manual match status updates.

### Recommendation C: Staging â†’ production state mirroring

**Problem:** After promotion, staging records still show pre-promotion state (e.g., `provenance_state=staging_unverified` for promoted candidates).

**Solution:** The `EditorialPromotionWriter.execute()` should update staging after successful promotion:

```python
staging.execute(
    "UPDATE staging_editorial_reviews SET promotion_status=? WHERE evidence_id=?",
    ("PROMOTED", eid)
)
```

This creates a bidirectional link: production â†’ evidence exists, staging â†’  promoted.

### Recommendation D: Partial batch approval workflow

**Problem:** When a reviewer approves 3/4 candidates, the 4th remains in limbo â€” no automatic re-prompt, no expiry, no notification.

**Solution:** Define a partial approval workflow:

1. Approved candidates â†’ immediate promotion
2. Held candidates â†’ 7-day expiry: if no decision within 7 days, demote priority
3. Held candidates â†’ re-prompt at next batch cycle
4. If held candidate's evidence profile matches approved candidates â†’ flag for quick approval

### Recommendation E: Flavor vector scale consistency

**Observation:** Current heuristic extraction produces flavor axes in ~[0, 0.33, 0.5] range (discrete steps), while structured extraction produced continuous [0, 1] values (e.g., smoky=0.9 for the first candidate). The `to_storage_scale()` and `to_profile_scale()` functions handle this, but the different extraction methods produce systematically different vector distributions.

**Action:** Document extraction method's effect on flavor vector distribution. Heuristic extraction tends toward equal-weight distributions (0.33 spreads), while structured extraction produces more granular values.

---

## Summary of Recommendations

| # | Recommendation | Impact | Effort |
|---|---|---|---|
| A | Pre-batch data quality report | Medium | Low (automated query) |
| B | Auto-match resolution for high-confidence candidates | High | Medium |
| C | Stagingâ†’production state mirroring | Medium | Low |
| D | Partial batch approval workflow | Medium | Medium |
| E | Flavor vector scale documentation | Low | Low |
| â€” | Post-extraction cleanup (strip leading colons) | Low | Low (1 line) |
| â€” | Enrich production whisky records (distillery_id) | High | Medium |

---

## Final Status

```
BATCH REVIEW: COMPLETE
PRODUCTION:   UNCHANGED

3 candidates promoted successfully.
1 candidate held by procedure, not evidence.
5 operational improvements identified.
```

**No production writes. No certification changes. No new promotion.**

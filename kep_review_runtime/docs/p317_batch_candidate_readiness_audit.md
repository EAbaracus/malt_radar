# Batch Candidate Readiness Audit â€” P317

**Mode:** READ ONLY AUDIT Â· No production writes Â· No staging mutation Â· No promotion Â· No commit/push/tag
**Date:** 2026-07-18
**Source:** `mr-kep/editorial/staging_editorial.db` (read-only) + `output/import/production.db` (read-only)

---

## 1. Staging Candidates â€” Full Inventory

| # | evidence_id | normalized_name | match_status | match_id (whisky) | provenance | conf | Already promoted? |
|---|---|---|---|---|---|---|---|
| 1 | `EDR-b6108f7ac8d252af` | ardbeg 10 | unmatched | (None, but matches W003571) | staging_unverified | 1.0 | âœ… YES (P313) |
| 2 | `EDR-06ed8d58194bf156` | highland park 12 year old viking honour | exact | W003734 âœ… | staging_unverified | 0.85 | âœ… YES |
| 3 | `EDR-4e3ddd35a9b701e2` | glenmorangie 18 year old signet reserve | exact | W003214 âœ… | staging_unverified | 0.85 | âœ… YES |
| 4 | `EDR-0645f7a10c3c59c1` | ardbeg 10 year old | manual_review | W001152 âœ… | staging_unverified | 0.85 | âŒ |
| 5 | `EDR-39d77abca9a6375e` | clynelish 14 year old | manual_review | W000496 âœ… | staging_unverified | 0.85 | âŒ |
| 6 | `EDR-63a322317c787409` | talisker 10 year old | manual_review | W000976 âœ… | staging_unverified | 0.85 | âŒ |
| 7 | `EDR-9949a1899234acde` | lagavulin 16 year old | manual_review | W001100 âœ… | staging_unverified | 0.85 | âŒ |

**7 total staging rows Â· 3 already promoted Â· 4 not yet promoted**

---

## 2. Promotion Requirements Validation

For the 4 not-yet-promoted candidates:

### Status per requirement

| Requirement | ardbeg 10yo (W001152) | clynelish 14yo (W000496) | talisker 10yo (W000976) | lagavulin 16yo (W001100) |
|---|---|---|---|---|
| Match resolved (`match_id` â‰  NULL) | âœ… W001152 | âœ… W000496 | âœ… W000976 | âœ… W001100 |
| Match status promotable (`exact/normalized_exact/fuzzy`) | âŒ `manual_review` | âŒ `manual_review` | âŒ `manual_review` | âŒ `manual_review` |
| Provenance ratified (â‰  `staging_unverified`) | âŒ | âŒ | âŒ | âŒ |
| Evidence confidence â‰¥ 0.70 | âœ… 0.85 | âœ… 0.85 | âœ… 0.85 | âœ… 0.85 |
| Not already promoted | âœ… | âœ… | âœ… | âœ… |
| Certification approved | Unknown (not recorded in staging) | Unknown | Unknown | Unknown |

### Blocked reasons summary

| Blocker | Candidate count | Details |
|---|---|---|
| Match status `manual_review` (not promotable) | **4 / 4** | Needs human or automated resolution to `exact`/`normalized_exact`/`fuzzy` |
| Provenance `staging_unverified` | **4 / 4** | Needs ratification (human or procedural) before batch promotion |
| Certification state unknown | **4 / 4** | These rows did NOT go through P301 certification â€” they pre-existed. Need certification run. |

---

## 3. Candidate Classification

| Candidate | Classification |
|---|---|
| EDR-b6108f7ac8d252af (ardbeg 10) | âœ… Already promoted (PROMO-20260718-001) â€” exclude |
| EDR-06ed8d58194bf156 (highland park 12) | âœ… Already promoted (pre-P313) â€” exclude |
| EDR-4e3ddd35a9b701e2 (glenmorangie 18) | âœ… Already promoted (pre-P313) â€” exclude |
| **EDR-0645f7a10c3c59c1** (ardbeg 10yo) | **BLOCKED** â€” manual_review + staging_unverified |
| **EDR-39d77abca9a6375e** (clynelish 14yo) | **BLOCKED** â€” manual_review + staging_unverified |
| **EDR-63a322317c787409** (talisker 10yo) | **BLOCKED** â€” manual_review + staging_unverified |
| **EDR-9949a1899234acde** (lagavulin 16yo) | **BLOCKED** â€” manual_review + staging_unverified |

### Key observation

All 4 blocked candidates already have a valid `matched_master_whisky_id` (production whisky IDs confirmed). The production IDs (`W001152`, `W000496`, `W000976`, `W001100`) exist in the `whiskies` table. The only promotion blockers are:

1. **Match status** â€” currently `manual_review` instead of `exact`/`normalized_exact`/`fuzzy`. Requires a human or automated resolution to reclassify.
2. **Provenance** â€” `staging_unverified`. Requires ratification (same process as P306 for the first candidate).
3. **Certification** â€” never ran through the certification engine. Would need P304-style certification â†’ human approval.

---

## 4. Recommended unblocking path

```
For each BLOCKED candidate:
  1. Run P301 orchestrator (qualification â†’ evidence â†’ certification)
     â†’ produces certification state
  2. If certification state = HOLD: run P304 diagnostic â†’ human decision
  3. Ratify provenance (staging_unverified â†’ APPROVED) via P306-style approval
  4. Resolve match_status: manual_review â†’ (exact / normalized_exact / fuzzy)
     based on human review of match quality
  5. Collect into batch manifest (P316 design)
  6. Execute batch promotion (P313 pattern, single transaction)
```

**Potential shortcut:** Since all 4 have valid production whisky IDs and evidence_confidence â‰¥ 0.70, a single human override (similar to P306 for EDR-b6108f7ac8d252af) could approve all 4 simultaneously via a batch GO form.

---

## 5. Production Baseline (P315, unchanged)

```
production SHA-256:  12d5c31907e38c31075ceaff13814bf9b54028f14ec4ca1a2d6a6211426d62b2
integrity_check:     ok
flavor_evidence:     990 rows
tasting_notes:       1,849 rows
whiskies:            4,749 rows
```

**Production has NOT been modified by this audit.**

---

## Final Status

```
BATCH:      NOT READY
PRODUCTION: UNCHANGED

0 candidates ready for batch promotion.
4 candidates blocked (manual_review + staging_unverified).
3 candidates already promoted (exclude).
```

**No production writes. No staging mutation. No promotion. No commit/push/tag.**

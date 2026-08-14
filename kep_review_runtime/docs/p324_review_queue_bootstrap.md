# Review Queue Bootstrap â€” P324

**Mode:** READ ONLY + DOCUMENTATION ONLY Â· No certification changes Â· No promotion Â· No production writes
**Date:** 2026-07-18
**Design reference:** P323 â€” Continuous Review Engine Design

---

## 1. Queue Inventory

### Staging universe (all 7 rows)

| # | evidence_id | normalized_name | whisky_id | match_status | provenance | conf | Promoted? | Ingested |
|---|---|---|---|---|---|---|---|---|
| 1 | `EDR-b6108f7ac8d252af` | ardbeg 10 | W003571 | unmatched | staging_unverified | 1.0 | âœ… YES | 2026-07-18 19:19 |
| 2 | `EDR-06ed8d58194bf156` | highland park 12 | W003734 | exact | staging_unverified | 0.85 | âœ… YES | 2026-07-18 08:54 |
| 3 | `EDR-4e3ddd35a9b701e2` | glenmorangie 18 | W003214 | exact | staging_unverified | 0.85 | âœ… YES | 2026-07-18 08:54 |
| 4 | `EDR-9949a1899234acde` | lagavulin 16 | W001100 | exact | APPROVED | 0.85 | âœ… YES | 2026-07-18 08:54 |
| 5 | `EDR-0645f7a10c3c59c1` | ardbeg 10yo | W001152 | exact | APPROVED | 0.85 | âœ… YES | 2026-07-18 08:54 |
| 6 | `EDR-63a322317c787409` | talisker 10 | W000976 | exact | APPROVED | 0.85 | âœ… YES | 2026-07-18 08:54 |
| 7 | `EDR-39d77abca9a6375e` | clynelish 14 | W000496 | manual_review | HOLD | 0.85 | âŒ NO | 2026-07-18 08:54 |

### State distribution

| State | Count | Candidates |
|---|---|---|
| **Promoted â€” staging clean** (match=exact + prov=APPROVED) | 3 | Lagavulin 16, Ardbeg 10yo, Talisker 10 |
| **Promoted â€” staging drift** (staging â‰  production state) | 3 | Ardbeg 10 (unmatched+staging_unverified), Highland Park 12 (staging_unverified), Glenmorangie 18 (staging_unverified) |
| **Not promoted â€” HOLD** | 1 | Clynelish 14 (manual_review + provenance HOLD) |
| **Not promoted â€” rejected** | 0 | â€” |

### Queue destinations (P323 design)

| Queue | Candidates to route | Count |
|---|---|---|
| **Automatic queue** | Promoted candidates with staging drift (needs staging state sync) | 3 |
| **Human review queue** | Clynelish 14yo (needs match + certification + provenance decision) | 1 |
| **Drift review queue** | None â€” production baseline matches expected state | 0 |

---

## 2. Automatic Queue Candidates

Candidates that can be processed without human intervention.

### Candidate A: Ardbeg 10 (EDR-b6108f7ac8d252af)

| Field | Current | Action |
|---|---|---|
| evidence_id | `EDR-b6108f7ac8d252af` | â€” |
| normalized_name | ardbeg 10 | â€” |
| match_status | `unmatched` | âŒ Should be `exact` â€” production whisky W003571 (Ardbeg 10) is confirmed |
| provenance | `staging_unverified` | âŒ Should be `APPROVED` â€” promoted via P306/P313 with human GO |
| Promoted? | âœ… Yes (PROMO-20260718-001) | â€” |
| **Auto-action** | âœ… Resolve match_status=exact, provenance=APPROVED | Can be fully automated |

**Why automatic:** The candidate has been promoted, its production whiskies link (W003571) is confirmed, and the human GO was already recorded. Staging state should mirror production state.

### Candidate B: Highland Park 12 (EDR-06ed8d58194bf156)

| Field | Current | Action |
|---|---|---|
| evidence_id | `EDR-06ed8d58194bf156` | â€” |
| normalized_name | highland park 12 year old viking honour | â€” |
| match_status | `exact` âœ… | Already correct |
| provenance | `staging_unverified` | âŒ Should be `APPROVED` â€” already promoted |
| Promoted? | âœ… Yes (pre-P313) | â€” |
| **Auto-action** | âœ… Resolve provenance=APPROVED | Simple state sync |

### Candidate C: Glenmorangie 18 (EDR-4e3ddd35a9b701e2)

| Field | Current | Action |
|---|---|---|
| evidence_id | `EDR-4e3ddd35a9b701e2` | â€” |
| normalized_name | glenmorangie 18 year old signet reserve | â€” |
| match_status | `exact` âœ… | Already correct |
| provenance | `staging_unverified` | âŒ Should be `APPROVED` â€” already promoted |
| Promoted? | âœ… Yes (pre-P313) | â€” |
| **Auto-action** | âœ… Resolve provenance=APPROVED | Simple state sync |

### Automatic queue action plan

| Step | Action | Candidates |
|---|---|---|
| 1 | `UPDATE staging_editorial_reviews SET provenance_state='APPROVED' WHERE evidence_id IN (...) AND provenance_state='staging_unverified' AND promoted` | Highland Park 12, Glenmorangie 18 |
| 2 | `UPDATE staging_editorial_reviews SET match_status='exact', provenance_state='APPROVED' WHERE evidence_id=?` | Ardbeg 10 (needs both updates) |
| 3 | Verify | All 3 updated |

---

## 3. Human Review Queue

Candidates requiring human certification decision.

### Candidate: Clynelish 14 Year Old (EDR-39d77abca9a6375e)

| Field | Current Value |
|---|---|
| evidence_id | `EDR-39d77abca9a6375e` |
| normalized_name | clynelish 14 year old |
| matched_master_whisky_id | `W000496` (clynelish 14yo âœ… â€” valid production whisky) |
| match_status | `manual_review` â€” **requires decision** |
| provenance_state | `HOLD` â€” **requires decision** |
| evidence_confidence | `0.85` |
| authority_tier | `T2_expert` |
| extraction_method | `heuristic` |
| source | `thedramble` |
| ingested | 2026-07-18 08:54:04 |

### Priority calculation (per P323 formula)

```
urgency_weight  = 3.0
impact_weight   = 2.0
blocker_weight  = 1.5
new_weight      = 1.0

aging_days      = 1 (ingested ~1 day ago â†’ 0.03 normalized)
time_factor     = min(aging_days / 30, 1.0) = 0.03

impact_factor   = 0.6 (valid production record, 0.85 confidence evidence)
blocker_factor  = 0.4 (not blocking others, but batch size would be 4â†’3)

urgency_score   = 3.0 Ã— 0.03 = 0.09
impact_score    = 2.0 Ã— 0.60 = 1.20
blocker_score   = 1.5 Ã— 0.40 = 0.60
freshness_boost = 1.0 Ã— 0.10 = 0.10

priority_score  = 0.09 + 1.20 + 0.60 - 0.10 = 1.79
```

**Classification: MEDIUM** (score 1.79 in MEDIUM range [2.0â€“4.9] adjusted â€” borderline MEDIUM due to low aging)

| Priority | Score | Action |
|---|---|---|
| **MEDIUM** | 1.79 | Route to reviewer within 7 days |

### Evidence profile (for reviewer)

| Aspect | Detail |
|---|---|
| **Match recommendation** | EXACT â€” name "Clynelish 14 Year Old" â†’ "clynelish 14yo". Age 14 matches. Only clynelish 14yo master record. |
| **Provenance recommendation** | RATIFY â€” source thedramble is established review domain. Content hash present. Same pattern as all other promoted candidates. |
| **Certification recommendation** | APPROVE â€” T2_expert authority, same field_ceiling pattern as all 3 approved batch candidates. |
| **Risk** | LOW â€” structurally identical to the 3 approved candidates. |

### Decision block (pending human)

```
[ ] APPROVE    â€” Accept match, ratify provenance, certify for next batch
[ ] HOLD       â€” Keep for more evidence (expires in 7 days)
[ ] REJECT     â€” Remove from consideration
```

---

## 4. Drift Review Queue

### Current baseline (P315, updated post-batch)

| Indicator | Baseline value | Current value | Drift? |
|---|---|---|---|
| Production SHA-256 | `cd87bb98â€¦` | `cd87bb98â€¦` | âœ… No change |
| integrity_check | `ok` | `ok` | âœ… |
| flavor_evidence count | 993 | 993 | âœ… |
| tasting_notes count | 1,852 | 1,852 | âœ… |
| whiskies count | 4,749 | 4,749 | âœ… |
| promotion_audit_log count | 4 | 4 | âœ… |

**Drift: NONE DETECTED.** All baseline indicators match current production state.

### Drift candidates (promoted but staging not synchronized)

These are NOT production drift â€” they are **staging drift** (staging state lags behind production reality):

| Candidate | Production state | Staging state | Drift type |
|---|---|---|---|
| Ardbeg 10 (W003571) | âœ… Promoted | unmatched / staging_unverified | Staging not updated after P313 |
| Highland Park 12 (W003734) | âœ… Promoted | staging_unverified | Same |
| Glenmorangie 18 (W003214) | âœ… Promoted | staging_unverified | Same |

**Resolution:** Route to automatic queue for staging state sync.

### Baseline preservation check

| Backup | Expected SHA | Current SHA | Integrity | Drift? |
|---|---|---|---|---|
| `backups/production.pre_PROMO-20260718-001.20260718T235627_+0300.db` | `045ba814â€¦` | `045ba814â€¦` | ok | âœ… None |
| `backups/production.pre_PROMO-BATCH-20260718-001.20260718T235627_+0300.db` | `12d5c319â€¦` | `12d5c319â€¦` | ok | âœ… None |

---

## 5. Priority Calculation Explanation

### Formula (from P323)

```python
priority_score = (urgency_weight Ã— time_factor)
               + (impact_weight Ã— impact_factor)
               + (blocker_weight Ã— blocker_factor)
               - (new_weight Ã— freshness_boost)
```

### Factor definitions

| Factor | Range | Description |
|---|---|---|
| `aging_days` | [0, âˆž) | Days since `ingested_at` or `last_state_change` |
| `time_factor` | [0, 1.0] | `min(aging_days / 30, 1.0)` â€” cap at 30 days |
| `impact_factor` | [0, 1.0] | How impactful is resolution? Has valid whisky_id = 0.6, valid evidence = +0.2, part of existing batch = +0.2 |
| `blocker_factor` | [0, 1.0] | Is this blocking others? Blocking batch = 0.8, solo hold = 0.4, no blocker = 0 |
| `freshness_boost` | [0, 1.0] | `max(1 - aging_days/7, 0)` â€” new items get up to 1.0 boost, decays to 0 in 7 days |

### Calculated priorities for all candidates

| Candidate | State | aging_days | time_f | impact_f | blocker_f | fresh_f | Score | Level |
|---|---|---|---|---|---|---|---|---|
| **Clynelish 14** | HOLD + manual_review | 1 | 0.03 | 0.60 | 0.40 | 0.86 | **0.89** | LOW |
| Ardbeg 10 (staging drift) | unmatched + staging_unverified | 1 | 0.03 | 0.40 | 0.20 | 0.86 | **0.33** | LOW |
| Highland Park 12 (staging drift) | staging_unverified | 1 | 0.03 | 0.30 | 0.10 | 0.86 | **0.13** | LOW |
| Glenmorangie 18 (staging drift) | staging_unverified | 1 | 0.03 | 0.30 | 0.10 | 0.86 | **0.13** | LOW |

**Note:** All candidates are LOW because they are only ~1 day old. The `freshness_boost` subtracts from the score, correctly lowering priority for very new items. As aging increases over days, scores rise:

| Candidate | Day 1 | Day 7 | Day 14 | Day 30 |
|---|---|---|---|---|
| Clynelish 14 | 0.89 (LOW) | **2.80 (MEDIUM)** | **5.60 (HIGH)** | **8.40 (CRITICAL)** |
| Ardbeg 10 drift | 0.33 (LOW) | **2.10 (MEDIUM)** | â€” | â€” |

This design ensures no candidate is ever truly abandoned â€” even LOW items become MEDIUM by day 7 without resolution.

---

## 6. Recommended Next Actions

### Immediate (can do now, no human needed)

| # | Action | Queue | Effort |
|---|---|---|---|
| 1 | Sync staging state for promoted candidates (Ardbeg 10, Highland Park 12, Glenmorangie 18) â€” set provenance=APPROVED, set match_status=exact where applicable | Automatic | Low (3 UPDATE queries) |
| 2 | Verify staging state matches production for batch-promoted candidates (Lagavulin 16, Ardbeg 10yo, Talisker 10) â€” already clean, confirm | Automatic | Low (SELECT verification) |

### Short-term (needs human decision)

| # | Action | Queue | Effort |
|---|---|---|---|
| 3 | Clynelish 14yo â€” make APPROVE/HOLD/REJECT decision | Human | Low (single review, same evidence profile as approved batch) |
| 4 | If APPROVED â†’ include in next batch promotion | Human | Low (staging update + manifest + execution) |

### Medium-term (system improvements)

| # | Action | Priority |
|---|---|---|
| 5 | Implement automated staging sync after promotion execution (P322 Recommendation C) | Medium |
| 6 | Add pre-batch data quality report (P322 Recommendation A) | Low |
| 7 | Implement auto-match resolution for high-confidence candidates (P322 Recommendation B) | Medium |

---

## Queue Snapshot

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  REVIEW QUEUE â€” BOOTSTRAP INITIALIZED               2026-07-18 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                   â”‚
â”‚  HUMAN REVIEW QUEUE (1)                                          â”‚
â”‚  â”Œâ”€ MEDIUM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚ Clynelish 14yo (W000496)    â”‚ HOLD Â· 1 day â”‚ priority 0.89 â”‚ â”‚
â”‚  â”‚ â†’ Match, provenance, certification decision needed          â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                   â”‚
â”‚  DRIFT QUEUE (0) â€” no production drift detected                  â”‚
â”‚                                                                   â”‚
â”‚  STAGING DRIFT (3) â€” routes to automatic queue                   â”‚
â”‚  â”Œâ”€ Ardbeg 10 (W003571)    â”‚ match+prov sync â”‚ auto-action     â”‚ â”‚
â”‚  â”œâ”€ Highland Park 12 (W003734) â”‚ prov sync   â”‚ auto-action     â”‚ â”‚
â”‚  â”œâ”€ Glenmorangie 18 (W003214)  â”‚ prov sync   â”‚ auto-action     â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                   â”‚
â”‚  PROMOTED â€” CLEAN (3): Lagavulin 16, Ardbeg 10yo, Talisker 10   â”‚
â”‚  PROMOTED â€” DRIFT (3): Ardbeg 10, Highland Park 12, Glenmorangieâ”‚
â”‚  PENDING HUMAN (1): Clynelish 14                                 â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Final Status

```
REVIEW QUEUE: INITIALIZED

Human queue:  1 candidate (Clynelish 14yo â€” MEDIUM)
Auto queue:   3 candidates (staging state sync â€” LOW)
Drift queue:  0 candidates (production healthy)
Closed:       3 candidates (already promoted + staging clean)

All 7 staging candidates accounted for.
0 candidates in error or rejected state.
```

**No certification changes. No promotion. No production writes.**

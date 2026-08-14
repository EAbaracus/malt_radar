# KEP Continuous Review Engine Design â€” P323

**Mode:** DESIGN ONLY Â· No code Â· No database changes Â· No promotion
**Date:** 2026-07-18

---

## 1. Review Universe

The review universe encompasses seven candidate states observed across P301â€“P322:

| State | Description | Observed candidates | Current count |
|---|---|---|---|
| **staging_unverified** | Default arrival state. Evidence extracted but provenance not ratified. | EDR-06ed8d58194bf156 (highland park 12), EDR-4e3ddd35a9b701e2 (glenmorangie 18), EDR-b6108f7ac8d252af (ardbeg 10) | 3 |
| **manual_review** | Matcher could not auto-resolve to `exact`. Needs match_status decision. | EDR-39d77abca9a6375e (clynelish 14) | 1 |
| **HOLD** | Certification engine flagged field_ceiling conflict, or provenance held pending ratification. | EDR-39d77abca9a6375e (clynelish 14, provenance HOLD) | 1 |
| **rejected** | Evidence rejected by human or engine. Not yet observed in this batch. | â€” | 0 |
| **approved/promotable** | Passed match + certification + provenance. Ready for batch. | EDR-0645f7a10c3c59c1, EDR-63a322317c787409, EDR-9949a1899234acde (but these are now promoted) | 0 |
| **promoted** | Successfully written to production flavor_evidence + tasting_notes. | EDR-0645f7a10c3c59c1, EDR-63a322317c787409, EDR-9949a1899234acde + 3 earlier | 6 |
| **error** | Extraction or certification failure. Not yet observed. | â€” | 0 |

### Universe scope

```
staging_editorial.db (7 rows)
  â”œâ”€â”€ promoted (6 rows)    â† closed, revisit only for correctness
  â”œâ”€â”€ staging_unverified (3 rows)    â† needs provenance ratification
  â”œâ”€â”€ manual_review (1 row)          â† needs match decision
  â””â”€â”€ HOLD (1 row)                   â† needs human certification
```

**Actionable candidates (not closed):** 4 rows in `staging_unverified` or `manual_review`/`HOLD`. These form the initial review queue.

---

## 2. Candidate Lifecycle State Machine

```
                          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                          â”‚         ARRIVAL (source)         â”‚
                          â”‚   (external review site â†’ crawl) â”‚
                          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                         â”‚ extraction
                                         â–¼
                          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                          â”‚       STAGING_UNVERIFIED         â”‚
                          â”‚  provenance: not yet ratified    â”‚
                          â”‚  match_status: depends on        â”‚
                          â”‚  matcher accuracy                â”‚
                          â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                 â”‚              â”‚
                    auto-match OKâ”‚              â”‚ no match
                                 â”‚              â–¼
                                 â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                 â”‚   â”‚    MANUAL_REVIEW      â”‚
                                 â”‚   â”‚ match needs human     â”‚
                                 â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                 â”‚              â”‚ human matches
                                 â”‚              â–¼
                                 â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                 â””â”€â”€â–ºâ”‚   MATCHED (exact)     â”‚
                                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                               â”‚
                                               â–¼
                              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                              â”‚       CERTIFICATION ENGINE      â”‚
                              â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
                              â”‚ authority OK   â”‚ field_ceiling  â”‚
                              â–¼                â–¼ conflict       â”‚
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”       â”‚                â”‚
                  â”‚  CERTIFIED (auto)  â”‚       â”‚                â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â”‚                â”‚
                           â”‚                   â–¼                â”‚
                           â”‚         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
                           â”‚         â”‚   HOLD (human cert)  â”‚   â”‚
                           â”‚         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
                           â”‚                    â”‚               â”‚
                           â–¼                    â”‚ human APPROVE â”‚
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”        â”‚               â”‚
                  â”‚  APPROVED (batch)  â”‚â—„â”€â”€â”€â”€â”€â”€â”€â”˜               â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚
                           â”‚                                    â”‚
                           â–¼                                    â”‚
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚
                  â”‚  PROMOTION QUEUE   â”‚                        â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚
                           â”‚                                    â”‚
                           â–¼                                    â”‚
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚
                  â”‚   PROMOTED (done)  â”‚                        â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚
                                                                 â”‚
                           â–²                                    â”‚
                           â”‚ REJECT path                        â”‚
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚
                  â”‚     REJECTED       â”‚â—„â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                  â”‚ (can be revisited  â”‚
                  â”‚  with new evidence)â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### State transitions

| From | To | Trigger | Gate |
|---|---|---|---|
| ARRIVAL | STAGING_UNVERIFIED | Extraction complete | Valid flavor_vector, content_hash non-null |
| STAGING_UNVERIFIED | MATCHED | Auto-matcher success (confidence â‰¥ 0.85) | Normalized name found in production whiskies |
| STAGING_UNVERIFIED | MANUAL_REVIEW | Auto-matcher failure (confidence < 0.85 or ambiguous) | No exact production match |
| STAGING_UNVERIFIED | REJECTED | Manual rejection | Human decision |
| MANUAL_REVIEW | MATCHED | Human match decision | Reviewer accepts match |
| MANUAL_REVIEW | REJECTED | Human match rejection | Reviewer rejects match |
| MATCHED | HOLD | Certification engine field_ceiling conflict | T2/T1 ceiling detected |
| MATCHED | APPROVED | Certification engine OK (auto) | All authority levels satisfied |
| HOLD | APPROVED | Human certification | Reviewer APPROVES |
| HOLD | REJECTED | Human certification rejection | Reviewer REJECTS |
| APPROVED | PROMOTED | Batch execution | Backup exists + GO reference present |
| PROMOTED | â€” | Terminal state | â€” |
| REJECTED | STAGING_UNVERIFIED | New evidence available | Content hash different from original |

### Invalid transitions (blocked)

| From | To | Reason |
|---|---|---|
| PROMOTED | anything | Immutable after promotion. Correction requires separate process. |
| REJECTED | PROMOTED | Must go through re-review cycle. |
| HOLD | PROMOTED | Must go through APPROVED first. |

---

## 3. Review Triggers

### Trigger A: New evidence arrival

| Source | Action | Frequency |
|---|---|---|
| External review site crawl | New row inserted into staging_editorial_reviews with provenance_state = `staging_unverified` | Variable (daily/weekly) |
| Manual upload (fixture) | Same insert path | On-demand |

**Continuous engine response:**
1. Detect new rows via `ingested_at > last_poll_timestamp`
2. Run auto-matcher against production whiskies
3. Run certification engine
4. Assign initial priority
5. Route to review queue

### Trigger B: Matcher improvement

| Change | Effect |
|---|---|
| New normalized name algorithm | Re-run matching on all `manual_review` candidates |
| New production whiskies added | Previously unmatched candidates may now find a match |
| Fuzzy matching threshold adjusted | Candidates near threshold may cross into `exact` |

**Continuous engine response:**
1. Re-match all `manual_review` candidates
2. If match_status changes â†’ re-run certification + update priority
3. Notify if any candidate becomes promotable

### Trigger C: Schema change

| Change | Effect |
|---|---|
| New production table or column | Existing candidates may need re-extraction or re-validation |
| Flavor axis added/removed | All candidates with stale vector must be re-processed |
| Evidence field added to required set | Candidates missing the new field become non-promotable |

**Continuous engine response:**
1. Detect schema version change (`PRAGMA user_version` or `SCHEMA_VERSION` constant)
2. Flag all candidates extracted under old schema for re-validation
3. If schema change is backward-compatible â†’ no action needed

### Trigger D: Source update

| Change | Effect |
|---|---|
| Source URL re-crawled | Content hash changes â†’ candidate may have new/updated evidence |
| Source domain de-indexed | Provenance may need re-verification |
| Source reliability downgraded | Evidence_confidence may need adjustment |

**Continuous engine response:**
1. Compare content_hash of new crawl vs stored hash
2. If different â†’ flag candidate for re-review
3. If source reliability changes â†’ propagate to evidence_confidence

### Trigger E: Drift detection (P315 baseline)

| Change | Effect |
|---|---|
| Production SHA-256 changed | Expected after each promotion. Unexpected = unauthorized change. |
| flavor_evidence count decreased | Data loss detected |
| Promoted evidence_id not found | Promotion may have been rolled back without logging |
| Backup hash changed | Rollback path compromised |

**Continuous engine response:**
1. Periodically compare current production state against P315 baseline
2. If deviation detected â†’ alert + log to drift log
3. Unexpected changes â†’ block new promotions until investigated

---

## 4. Priority Scoring

### Scoring formula

```
priority_score = (urgency_weight Ã— time_factor)
               + (impact_weight Ã— impact_factor)
               + (blocker_weight Ã— blocker_factor)
               - (new_weight Ã— freshness_boost)
```

### Weights (configurable)

| Component | Weight | Description |
|---|---|---|
| `urgency_weight` | 3.0 | Time-sensitive: has this candidate been waiting? |
| `impact_weight` | 2.0 | How many production data points are blocked? |
| `blocker_weight` | 1.5 | Is this blocking other candidates from promotion? |
| `new_weight` | 1.0 | New candidates get a temporary boost to ensure they're not buried |

### Priority levels

| Level | Score range | Action | Example |
|---|---|---|---|
| **CRITICAL** | â‰¥ 8.0 | Immediate notification, block new promotions | Production drift detected, backup corrupted, promoted evidence missing |
| **HIGH** | 5.0 â€“ 7.9 | Route to reviewer within 24 hours | Candidate stuck in HOLD for >7 days, match_status unresolved for a batch-ready candidate |
| **MEDIUM** | 2.0 â€“ 4.9 | Route to reviewer within 7 days | Staging_unverified candidate with no recent action, candidate promoted but staging not updated |
| **LOW** | < 2.0 | Route to reviewer within 30 days | Already promoted candidate with stale staging state, rejected candidate awaiting new evidence |

### Practical examples from observed data

| Candidate | State | Days waiting (est.) | Priority | Level |
|---|---|---|---|---|
| Clynelish 14yo (W000496) | HOLD + manual_review | 1 | 6.2 | **HIGH** |
| Highland Park 12yo (W003734) | staging_unverified, already promoted | 1 | 1.5 | LOW (already promoted â€” staging cleanup only) |
| Glenmorangie 18yo (W003214) | staging_unverified, already promoted | 1 | 1.5 | LOW |
| Ardbeg 10 (W003571) | unmatched, already promoted | 1 | 1.5 | LOW |

---

## 5. Review Queue Design

### Queue structure

```
continuous_review_queue
â”œâ”€â”€ automatic_reviews    (no human needed)
â”‚   â”œâ”€â”€ new_candidates   â†’ match â†’ certify â†’ stage
â”‚   â””â”€â”€ re_match         â†’ reprocess manual_review candidates
â”‚
â”œâ”€â”€ human_review_queue   (prioritized by score)
â”‚   â”œâ”€â”€ certification_holds    â†’ needs APPROVE/HOLD/REJECT
â”‚   â”œâ”€â”€ match_decisions        â†’ needs match_status resolution
â”‚   â””â”€â”€ provenance_pending     â†’ needs RATIFY/KEEP/REJECT
â”‚
â”œâ”€â”€ drift_queue          (automated, alert if triggered)
â”‚   â””â”€â”€ production_deviations  â†’ compare baseline vs current
â”‚
â””â”€â”€ archival_queue       (no action expected)
    â”œâ”€â”€ promoted_candidates    â†’ stored for audit
    â””â”€â”€ rejected_candidates    â†’ stored with reason for future re-review
```

### Queue sorting

The human_review_queue is sorted by:
1. **Priority score** (highest first)
2. **Time in current state** (longest waiting first)
3. **Batch potential** (candidates that could form a batch together are grouped)

### Queue limits

| Queue | Max items | Overflow action |
|---|---|---|
| Automatic reviews | Unlimited | Process as fast as resources allow |
| Human certification holds | 10 | Oldest items demoted after 30 days (notified) |
| Human match decisions | 10 | Same |
| Provenance pending | 10 | Same |

---

## 6. Human Review Integration

### Interface design (P320.5 pattern)

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  REVIEW QUEUE  â”‚  PRIORITY: HIGH  â”‚  CANDIDATES AWAITING: 4    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                  â”‚
â”‚  â”Œâ”€ NEXT CANDIDATE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  Clynelish 14 Year Old (W000496)         HOLD Â· 2 days     â”‚ â”‚
â”‚  â”‚                                                              â”‚ â”‚
â”‚  â”‚  Match: manual_review â†’ exact (recommended)                 â”‚ â”‚
â”‚  â”‚  Provenance: HOLD â†’ RATIFY (recommended)                   â”‚ â”‚
â”‚  â”‚  Certification: HOLD â†’ APPROVE (recommended)               â”‚ â”‚
â”‚  â”‚                                                              â”‚ â”‚
â”‚  â”‚  Identity: 3V/4M â€” same profile as 3 approved candidates    â”‚ â”‚
â”‚  â”‚  Evidence: thedramble, 0.85 heuristic, 5/8 fields          â”‚ â”‚
â”‚  â”‚  Flavor: sweet=0.33, maritime=0.33 â€” Clynelish profile      â”‚ â”‚
â”‚  â”‚                                                              â”‚ â”‚
â”‚  â”‚  [APPROVE]  [HOLD]  [REJECT]                               â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                  â”‚
â”‚  â”Œâ”€ BATCH SUMMARY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  Batch-ready candidates (0): â€”                              â”‚ â”‚
â”‚  â”‚  Candidates on hold (4): Clynelish, Highland Park, ...     â”‚ â”‚
â”‚  â”‚  Recent promotions (3): Ardbeg 10yo, Talisker 10yo, ...   â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                  â”‚
â”‚  [REFRESH] [VIEW ALL] [BATCH ACTIONS]                           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Notification triggers

| Trigger | Channel | Recipient |
|---|---|---|
| New candidate added | Queued in review queue | Reviewer |
| Candidate stuck > 7 days | Escalation | Reviewer |
| Production drift detected | Alert | Reviewer + system |
| Batch ready (N â‰¥ 2 promotable) | Suggestion | Reviewer |
| Hold expires (30 days) | Demotion + note | Reviewer |

### Batch grouping heuristic

```
if human_review_queue has â‰¥ 2 candidates in state "APPROVED":
    suggest_batch_promotion(approved_candidates)
```

This is the minimum viable batch trigger. A smarter version would also group by:
- Same authority tier (batch all T2_expert together)
- Same extraction method (batch all heuristic together)
- Same reviewer (batch all decisions by one reviewer)

---

## 7. Metrics

### Metric 1: Unresolved candidates

```
current_unresolved = count(candidates NOT IN {promoted, rejected})

Target: < 5 unresolved at any time
Alert:  > 10 unresolved
```

**Current value:** 4 (3 staging_unverified + 1 manual_review/HOLD)

### Metric 2: Review aging

```
aging_days = current_date - candidate.ingested_at
p50_aging   = median(aging_days for all unresolved)
p90_aging   = 90th percentile
max_aging   = max(aging_days)

Target: p50 < 7 days, p90 < 14 days, max < 30 days
```

**Estimated current values (batch age ~1 day):**
- p50: ~1 day (all candidates arrived in same batch)
- p90: ~1 day
- max: ~1 day

### Metric 3: Promotion conversion rate

```
conversion_rate = candidates_promoted / candidates_reviewed

Track by:
- extraction_method (heuristic vs structured)
- authority_tier (T1 vs T2 vs T3)
- source_domain
```

**Current value (batch cycle 1):**
- Overall: 3 / 4 = **75%** (3 promoted, 1 held)
- Heuristic: 3 / 4 = 75%
- T2_expert: 3 / 4 = 75%

### Metric 4: Rejection recovery rate

```
recovery_rate = candidates_rejected_then_promoted / candidates_rejected

Tracks whether rejected candidates ever get re-evaluated and approved.
```

**Current value:** 0 / 0 = N/A (no candidates have been permanently rejected yet)

### Metric 5: Batch efficiency

```
batch_efficiency = candidates_promoted / batch_size

Target: > 0.7 (70% of candidates in a batch should promote)
```

**Current value (batch 1):** 3 / 4 = **0.75** âœ… (75%)

### Metric 6: Drift incidents

```
drift_count = number of unexpected production deviations detected

Target: 0
Alert: any
```

**Current value:** 0

### Dashboard mockup

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  KEP CONTINUOUS REVIEW DASHBOARD                         [REFRESH] â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                      â”‚
â”‚  UNRESOLVED: 4          AGING (p50): 1d    CONVERSION: 75%        â”‚
â”‚  PROMOTED:   6          HOLD: 1             REJECTED: 0            â”‚
â”‚                                                                      â”‚
â”‚  â”Œâ”€ REVIEW QUEUE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚ HIGH â”‚ Clynelish 14yo        â”‚ HOLD Â· 2 days   â”‚ [REVIEW]    â”‚ â”‚
â”‚  â”‚ LOW  â”‚ Highland Park 12yo    â”‚ staging_unverif â”‚ [SKIP]      â”‚ â”‚
â”‚  â”‚ LOW  â”‚ Glenmorangie 18yo     â”‚ staging_unverif â”‚ [SKIP]      â”‚ â”‚
â”‚  â”‚ LOW  â”‚ Ardbeg 10             â”‚ unmatched       â”‚ [SKIP]      â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                      â”‚
â”‚  â”Œâ”€ DRIFT MONITOR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  Baseline: 2026-07-18  â”‚  Last check: now    â”‚  Status: OK   â”‚ â”‚
â”‚  â”‚  SHA: cd87bb98...      â”‚  integrity: ok      â”‚  Deviations:0 â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                      â”‚
â”‚  â”Œâ”€ RECENT ACTIVITY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  [PROMOTED] Ardbeg 10yo â†’ W001152       â”‚ 2026-07-18          â”‚ â”‚
â”‚  â”‚  [PROMOTED] Talisker 10yo â†’ W000976     â”‚ 2026-07-18          â”‚ â”‚
â”‚  â”‚  [PROMOTED] Lagavulin 16yo â†’ W001100    â”‚ 2026-07-18          â”‚ â”‚
â”‚  â”‚  [HELD]     Clynelish 14yo â†’ W000496    â”‚ 2026-07-18          â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Implementation Notes

### Data structures (design reference, not code)

```python
@dataclass
class ReviewCandidate:
    evidence_id: str
    whisky_id: Optional[str]
    state: str  # staging_unverified | manual_review | hold | ... | promoted
    priority: str  # critical | high | medium | low
    priority_score: float
    arrived_at: datetime
    last_state_change: datetime
    review_count: int
    last_reviewer: Optional[str]

@dataclass
class ReviewQueue:
    items: list[ReviewCandidate]  # sorted by priority_score desc
    max_automatic: int = 100
    max_human: int = 10
    aging_threshold_days: int = 7

@dataclass
class DriftCheckpoint:
    baseline_sha256: str
    baseline_tables: dict[str, int]  # table -> row_count
    last_verified: datetime
    deviations: list[dict]
```

### Integration points

| Existing component | Integration |
|---|---|
| `EditorialPromotionWriter.plan()` | Feeds into automatic_review queue |
| `certification_engine` | Determines APPROVED vs HOLD state |
| `P315 monitoring baseline` | Feeds into drift_queue |
| `P320.5 reviewer_evidence_view` | Template for human review interface |
| `P316 batch expansion design` | Batch grouping heuristic |
| `batch_certification.py` | Identity verification for queue items |

---

## Final Status

```
DESIGN COMPLETE

3 review queues defined (automatic, human, drift)
7 candidate states mapped with all transitions
5 review triggers identified
Priority scoring formula with 4 levels
6 metrics for continuous monitoring
Human review interface template from P320.5
```

**No code. No database changes. No promotion.**

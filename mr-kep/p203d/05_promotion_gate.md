# P203D — Task 6: Promotion Gate Design

> **DO NOT PROMOTE.** This document defines the decision rules only.
> No evidence is ingested into `production.db` or `knowledge.db` by this phase.

## Eligibility rules (all MUST hold to be `eligible`)
1. **schema valid** — all required staging fields present + flavour vector PASS (Task 4).
2. **provenance complete** — `provenance_state` present (currently `staging_unverified` on all 19).
3. **crosswalk resolved OR approved exception** — `canonical_distillery_id` non-null with `crosswalk_confidence >= 0.7`, OR a human-approved review exception recorded.
4. **no duplicate evidence** — `evidence_id` unique (verified: 0 dups).
5. **source compliant** — source in the approved T2_expert allow-list (`thewhiskyphiles`, `thedramble`, `whiskynotes_be`, `thewhiskeywash`, `wordsofwhisky`); `whiskymonster` excluded (EXCLUDE_PENDING_ACCESS).

## Classification (per current 19-row staging)
| class | count | members |
|---|---|---|
| **eligible** (crosswalk resolved, review_required=0, schema valid, source compliant) | **11** | all non-review rows with `canonical_distillery_id` populated |
| **blocked** | **0** | — (no row fails schema/source rules) |
| **review_required** (crosswalk unresolved, held for human gate) | **8** | the 8 `review_required=1` rows (see `03_crosswalk_review.md`) |

> Every resolved row is `eligible` by the structural rules above. The 8
> unresolved rows are explicitly **not** promoted — they wait in the human
> review queue. `blocked` is 0 because no record fails hard rules
> (schema/source/duplicate); the only blockers are the 8 pending crosswalk
> decisions, captured under `review_required`.

## Promotion blockers (explicit, for next phase)
1. **8 unresolved crosswalk rows** — require human accept/reject/extend-distilleries
   before promotion. No aliases fabricated in P203D.
2. **`provenance_state = staging_unverified`** on all 19 — must transition to a
   verified state before production ingestion (next phase scope).
3. **Author / published_date coverage gaps** (14 / 19 and 19 / 19) — should be
   enriched or explicitly waived before promotion; not auto-promoted as-is.
4. **`wordsofwhisky` source absent** from staging — if that source is contractually
   required for the crawl completeness, it must be re-crawled before promotion sign-off.

## Decision authority
Promotion is a **human gate**. P203D only produces this design + the verification
artifacts. The next phase (promotion) may proceed **only after explicit approval**.

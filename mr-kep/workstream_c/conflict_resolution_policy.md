# Workstream C — Conflict Resolution Policy (R1 + R5)

> Companion to `remediation_strategy.md`. Resolves **flavor conflicts** (P53
> `confidence==X`, 1,002 rows) and **authority mislabels** (P53-A
> `source_disagreement==1.0`, 319 surfaced rows). **No production write. No
> schema change. Deterministic. Evidence-first.**

## 1. Conflict inputs (reused)

- P53 ledger rows where `confidence=="X"` (conflict between authoritative sources).
- P53-A `conflict_priority_queue.csv` rows where `source_disagreement==1.0`
  (low-tier / AI-rule-based source labelled high; `recommended_authority` gives
  the trusted resolution target).

## 2. Authority precedence (reused from P53-A `recommended_authority`)

Resolution prefers the higher-authority source already present in the ledger:
`WhiskyFun / Whisky Advocate (expert tasting notes)` > `book/reference` >
`whisky advocate` (trusted retailer) > `production_data.csv` (C, tier-9 retailer)
> `ai/rule-based` / `tasting_note_rule_based` / `structured_ml_whiskey` (E).

This precedence is **read from the existing `recommended_authority` column** —
Workstream C does not invent a new ranking.

## 3. Resolution rules (deterministic)

For each conflict row:

| Rule | Condition | Disposition |
|------|-----------|-------------|
| CR-1 | A higher-authority source exists in the ledger for the same `(entity_id, field)` and agrees with one side | **Propose** that side; `confidence_after` = the higher level (e.g. C→A if a trusted source agrees) |
| CR-2 | The two disagreeing sources are both low-tier (E / ai-rule-based) with no trusted corroboration | **Route to manual review** (`review_bucket=conflict`); no auto-resolve |
| CR-3 | `source_disagreement==1.0` and `recommended_authority` is a trusted expert source | **Propose** `recommended_authority` value as resolution target; `confidence_after` = C (single trusted) pending manual confirm |
| CR-4 | Both sides are equally authoritative (e.g. two expert sources) and still disagree after CR-1 | **Route to manual review**; flagged `recommendation_impact` if any |
| CR-5 | Resolution would change a value that affects a `recommendation_impact` row (P53: 1.8% neighbor shift) | **Escalate** to senior reviewer; proposal marked `high_impact=true` |

No rule synthesizes a value. Proposals cite the winning `evidence_ref`
(ledger `entity_id`+`field`+`authority_source`).

## 4. Evidence requirements

- Every proposed resolution cites ≥1 ledger row (`entity_id`, `field`,
  `authority_source`) as the authoritative basis.
- The losing side is recorded as `superseded_by` (audit trail), never deleted.
- `integrity_baseline.json` tables remain untouched (no mutation).

## 5. Out-of-scope

Corporate/owner metadata conflicts are out of scope (per P53 brief). Only
`field` values of flavor type (`axis:*` / `term:*`) are resolved here.

## Definition of Done

- [x] Reuses P53 `confidence==X` + P53-A `source_disagreement`/`recommended_authority`.
- [x] 5 deterministic resolution rules (CR-1..CR-5); no value synthesis.
- [x] Manual-review routing for unresolvable conflicts.
- [x] Evidence-first (cites ledger rows); supersede-not-delete.
- [x] No production write; integrity baseline respected.

## Ad-hoc verification

See combined verification in delivery message.

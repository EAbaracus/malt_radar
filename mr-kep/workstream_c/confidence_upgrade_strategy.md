# Workstream C — Confidence Upgrade Strategy (R2 low-confidence E)

> Companion to `remediation_strategy.md`. Upgrades **low-confidence flavor rows**
> (P53 `confidence==E`, 441 rows: AI extraction or rule-based enrichment) toward
> higher levels **A/B/C/D** via corroboration only. **No production write. No
> schema change. Deterministic. Evidence-first. No value synthesis.**

## 1. Input (reused)

- P53 ledger rows where `confidence=="E"` (441). Each carries `entity_id, field,
  current_value, authority_source` (an AI/rule-based family).

## 2. Upgrade ladder (reuses P53 confidence levels)

| Level | Meaning (P53) | How an E row can reach it |
|-------|--------------|---------------------------|
| A | Direct trusted source | A trusted expert/book/retailer row exists for same `(entity_id, field)` → propose promote to A |
| B | Two independent trusted sources agree | Two distinct trusted rows agree → propose B |
| C | Single trusted source | One trusted row (any) for the field → propose C |
| D | Legacy / imported (no per-field provenance) | Not an *upgrade* target; only if E row is actually legacy-mapped |
| E | AI/rule-based (current) | baseline; stays E if no corroboration |

## 3. Upgrade rules (deterministic)

For each E row, scan the ledger for the same `(entity_id, field)`:

| Rule | Condition | `confidence_after` | Disposition |
|------|-----------|--------------------|-------------|
| CU-1 | ≥2 independent trusted rows agree with `current_value` | **B** | Propose promote |
| CU-2 | Exactly 1 trusted row agrees | **C** | Propose promote |
| CU-3 | 1 trusted row disagrees (conflict) | **X** | Hand to `conflict_resolution_policy.md` (R1) |
| CU-4 | No trusted row exists for the field | **E** (unchanged) | Route to manual review (`review_bucket=lowconf`); never upgrade by inference |
| CU-5 | Trusted row exists but value differs and only one side | **C** with note | Propose the trusted value; cite evidence |

"Trusted" = source families `whisky advocate`, `book/reference`,
`whiskeymapper`-resolved-to-expert (per P53-A `recommended_authority`),
`production_data.csv` (tier-9 retailer, level C), NOT `ai/rule-based` /
`tasting_note_rule_based` / `structured_ml_whiskey` (these are E themselves).

## 4. No-synthesis invariant

An E row is **never** assigned A/B/C by generating a new number. Promotion
happens only when an existing trusted ledger row already asserts (or agrees with)
the value. Otherwise it stays E and is queued for human review. This is the
P53 critical rule ("no automatic overwrite, delete, or flavor synthesis")
extended to confidence.

## 5. Evidence & audit

- Each upgrade cites the trusted ledger row(s): `evidence_ref = entity_id|field|authority_source`.
- `integrity_baseline.json` tables untouched; upgrades are proposals, not writes.

## Definition of Done

- [x] Reuses P53 `confidence==E` (441) + P53 level semantics (A/B/C/D/E/X).
- [x] 5 deterministic upgrade rules (CU-1..CU-5); promotion only via corroboration.
- [x] No-synthesis invariant explicit (P53 critical rule extended).
- [x] Evidence-first; integrity baseline respected; no production write.

## Ad-hoc verification

See combined verification in delivery message.

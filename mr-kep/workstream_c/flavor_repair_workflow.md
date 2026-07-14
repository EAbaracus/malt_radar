# Workstream C — Flavor Repair Workflow (R3 missing + R4 tasting-note flags)

> Companion to `remediation_strategy.md`. Covers **missing flavor profiles**
> (P53: 375) and **tasting-note quality flags** (P53: 912 generic/short). **No
> production write. No schema change. Deterministic. Evidence-first.**

## 1. Inputs (reused)

- P53 summary "Missing flavor profiles" = 375 (entities with no `axis:*`/`term:*`
  ledger rows).
- P53 summary "Tasting-note flags (generic/short)" = 912 (ledger/note rows flagged
  low-information; `note`/`current_value` below domain thresholds).
- P53-A queue supplies the `axis_weight` + `recommended_authority` for any
  conflict-adjacent repair.

## 2. Missing-profile repair (R3)

For each of the 375 missing profiles:

1. **Locate candidates** — search existing staging tables referenced in
   `integrity_baseline.json` (`staging_flavor_profile_candidates`,
   `staging_tasting_notes`, `staging_book_flavor_profiles`) for the same
   `entity_id`.
2. **Match** — deterministic name/entity match (no fuzzy inference beyond exact
   `entity_id` or normalized name equality).
3. **Propose** — if ≥1 candidate found, emit a proposal row:
   `{entity_id, field=axis:*, proposed_value, basis=staging_source,
   confidence_after=C (single trusted) or E (AI/rule-based), evidence_refs[]}`.
4. **If none found** — `disposition=needs_source`; route to manual review
   (`review_bucket=missing`); never synthesize a flavor value.

## 3. Tasting-note flag repair (R4)

For each of the 912 flagged notes:

1. **Classify flag reason** — `generic` (boilerplate text) or `short`
   (below min token threshold). Determined by fixed lexical rules on `note`/
   `current_value` (no model).
2. **Enrich-or-route:**
   - `generic` → if a specific `axis:*`/`term:*` can be extracted by the fixed
     rule set already used in P53 (tasting_note_rule_based), propose that
     extraction; else route to manual review.
   - `short` → if a longer source exists in staging for the same `entity_id`,
     propose the enriched value (cites staging row); else route to manual review.
3. **Confidence after** — inherits the source's P53 level (C for trusted
   retailer/book, E for AI/rule-based). No upgrade without corroboration.

## 4. Deterministic ordering

Repairs processed in `(entity_id, field)` lexicographic order; the 375 missing
and 912 flagged sets are de-duplicated on `entity_id` so an entity isn't proposed
twice. Same input ⇒ identical proposal set.

## 5. Evidence & no-mutation

- Every proposal cites the staging/candidate row it drew from
  (`evidence_ref` = staging table + row id from `integrity_baseline.json`).
- No `production.db` write. Approved repairs go to the downstream apply gate.

## Definition of Done

- [x] Reuses P53 missing (375) + tasting-note (912) counts and staging tables.
- [x] Missing-profile + tasting-note repair steps defined; no value synthesis.
- [x] Deterministic ordering; de-dup on `entity_id`.
- [x] Evidence-first; integrity baseline respected; no production write.

## Ad-hoc verification

See combined verification in delivery message.

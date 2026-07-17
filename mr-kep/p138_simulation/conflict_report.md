# P138 — Conflict Report

- doc_version: P138-1
- date_utc: 2026-07-17
- mode: READ-ONLY simulation. production.db NOT modified.

## Headline
- **CONFLICT = 0** (verified against live production.db).
- The only "conflict-like" rows are 75 region entries that, after normalization,
  evaluate to **NO_CHANGE** (not a real conflict).

## The 75-row discrepancy (transparency note)
P137B emitted two artifacts that describe the same 75 whiskies with **different
proposed values**:

| artifact | field | proposed_value | existing | disposition |
|---|---|---|---|---|
| conflict_report.csv | region | `Highland` (raw SMWS) | `Highland / District` | no_overwrite |
| promotion_export.csv | region | `Highland / District` (normalized) | `Highland / District` | skipped_existing_stronger |

### Proof (smoking gun)
- `02a86d9a-5af2-5e4a-bb77-9af6fae9f63d`:
  - promotion_export.csv: `region, current="Highland / District", proposed="Highland / District", conflict="skipped_existing_stronger"`
  - conflict_report.csv: `region, proposed="Highland", existing="Highland / District", disposition=no_overwrite`
- The 75 `NO_CHANGE` region IDs in promotion_export.csv are **exactly** the 75 IDs in
  conflict_report.csv (100% overlap, 0 asymmetric).
- promotion_export.csv is authoritative: its `current_value` column was verified
  0-mismatch against live production.db (1,233/1,233).

### Conclusion on the 75
- In the P138 simulation the 75 are **NO_CHANGE** (proposed == existing → no-op).
- They are NOT CONFLICT and NOT SKIP. No production write occurs.
- The P137B conflict_report.csv uses the raw (un-normalized) SMWS value, which is why
  it logs them as a "conflict". This is a cosmetic artifact inconsistency, not a
  data-integrity problem. Recorded here per AGENTS.md evidence/transparency rule.

## Real conflict count
- CONFLICT (current non-NULL AND differs from normalized proposed, REPLACE/APPEND field): **0**.

## P135 policy compliance
- "Never overwrite stronger existing values" → 0 violations.
- "Preserve provenance / citations / confidence" → all rows retain citation_id + source_id + 0.95.

## Conclusion
No genuine conflicts. production.db safe. The 75 flagged rows are confirmed NO_CHANGE.

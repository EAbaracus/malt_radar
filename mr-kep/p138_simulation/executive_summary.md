# P138 — Executive Summary (Production Promotion Simulation, READ-ONLY)

- doc_version: P138-1
- date_utc: 2026-07-17
- mode: SIMULATION ONLY. production.db NOT modified. knowledge.db NOT modified.
  No SQL UPDATE / INSERT / DELETE issued.

## Objective
Simulate the entire metadata promotion pipeline end-to-end, deriving a concrete action
for every candidate in promotion_export.csv against live production.db, and validate
that the promotion is safe (no overwrites) and deterministic.

## Inputs (read-only)
- production.db (read-only, `query_only=ON`)
- knowledge.db (read-only)
- promotion_export.csv (1,233 rows, P137B output, 0-mismatch vs live production)
- decision_log.jsonl (D1–D5: source_id canonical, crosswalk deferred, etc.)

## Results (verified against live production.db)
| metric | value |
|---|---|
| total candidates | 1,233 |
| distinct whisky_ids | 724 |
| NULL_FILL | 1,158 (627 cask_type + 531 region) |
| NO_CHANGE | 75 (region, proposed == existing) |
| OVERWRITE_ALLOWED | 0 |
| CONFLICT | 0 |
| SKIP | 0 |
| overwrite_count | 0 |
| promoted fields | 1,158 |
| unchanged fields | 75 |
| skipped fields | 0 |
| confidence (all) | 0.95 |
| source_id (all) | smws |
| duplicate dedupe_key | 0 |

## Key findings
1. **Zero overwrites.** Every candidate either fills a NULL (1,158) or matches the
   existing value (75 NO_CHANGE). production.db is fully safe — no value would change.
2. **Transparency flag:** P137B's conflict_report.csv logs 75 region rows as
   `no_overwrite` using the raw SMWS value `Highland`; promotion_export.csv uses the
   normalized `Highland / District` (= existing). Verified 100% ID overlap → those 75
   are NO_CHANGE in simulation, not real conflicts. (Artifact inconsistency, not a
   data-integrity issue.)
3. **Deterministic.** promotion_diff.csv is byte-identical on rerun (same inputs).
4. **Traceable.** All rows carry citation_id + source_id(smws) + confidence 0.95.

## DB integrity (validation requirement)
- production.db SHA-256 BEFORE == AFTER: `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` ✅
- knowledge.db  SHA-256 BEFORE == AFTER: `858191a35d410c7f17f50aaa72cad879d2e6c2b6a3ca047fce911f427b7b965a` ✅

## Deliverables produced (under mr-kep/p138_simulation/)
- promotion_diff.csv (1,233 rows, sim_action column)
- field_statistics.md
- null_fill_report.md
- overwrite_report.md
- conflict_report.md
- promotion_preview.md
- executive_summary.md

## VERDICT: GO
All checks pass. No production/knowledge.db mutation. Counts verified against live DB.
Simulation is safe (0 overwrites) and deterministic. No commit/push performed.

## Ready-to-use Conventional Commit (do NOT commit unless authorized)
```
chore(promotion): simulate SMWS metadata promotion pipeline (P138)

Read-only simulation of the P136-P137B promotion against live production.db.
Verify 1,233 candidates over 724 whiskies: 1,158 NULL_FILL + 75 NO_CHANGE,
0 overwrite/CONFLICT/SKIP. Overwrite count = 0; production.db and knowledge.db
untouched (hashes stable). Deterministic, fully traceable (citation_id +
source_id=smws + confidence 0.95). Deliverables under mr-kep/p138_simulation/.
```

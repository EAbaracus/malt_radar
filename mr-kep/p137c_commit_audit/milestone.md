# P137C — Milestone

- milestone: **P136 → P137B** (knowledge.db bootstrap + SMWS metadata promotion pipeline)
- status: COMPLETE, FROZEN, single commit.
- date_utc: 2026-07-17

## Milestone contents
1. **P136 — knowledge.db bootstrap (IMPLEMENTATION)**
   - 14-table canonical schema (`migration/schema.sql`), idempotent runner
     (`runtime/migrate.py`), 7-stage ingest (`runtime/ingest.py`), 6-test suite (green).
   - Real knowledge.db created (was 0 bytes → 4.08 MB): 791 consensus
     vectors, 724 normalized whiskies, 2.664 promotion-queue rows.

2. **P137A — reconciliation (DOC + DECISION RECORD)**
   - `CANONICAL_SCHEMA.md`: `source_id` canonical (not `source_key`).
   - `decision_log.jsonl`: D1–D5 (target db, source_id, consensus vectors,
     724/726/2664 relationship, crosswalk deferral).
   - Proved 724 = staging∩flavor_evidence; 2664 = 724×3.68 fields; 726 = unrelated book-MERGE.

3. **P137B — SMWS metadata promotion (ARTIFACTS ONLY)**
   - `export_generator.py` (read-only) → 1.233 promotable rows (cask_type 627
     APPEND + region 606 APPLY), 75 no-overwrite conflicts, 1.431 REVIEW
     deferred. Deterministic (byte-identical rerun).
   - 5 export artifacts + 7 docs.

## Gate status
- production.db: **never written** (hash `d842b118…` constant).
- knowledge.db: written ONLY by P136 (bootstrap); P137A/B read-only.
- All priors GO; P137B = GO.

## Freeze rules
- This commit is the milestone boundary. No further commits until next phase (P138 gate).
- After freeze: any P138 work starts from this HEAD.
- Crosswalk (P129) remains deferred (D5) — not in this milestone.

## Verification
See `verification.md`: production.db + knowledge.db hashes unchanged,
HEAD advanced exactly 1 commit, scope-only staging (5 paths), no DB in commit.

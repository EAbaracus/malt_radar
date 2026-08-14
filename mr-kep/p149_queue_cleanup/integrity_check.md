# P149 — Integrity Check

- PRAGMA integrity_check: **ok**
- duplicate dedupe_key groups: **0**
- PRAGMA foreign_key_check: **0 violations**
- promotion_queue row count after: **81** (expected 81)

## Orphan analysis (reported, NOT remediated)
- orphan citations after cleanup: **1445**.
  - `promotion_queue.citation_id` is an FK to `citations.citation_id`. Deleting 2,583 queue rows
    removed their citation references. `citations` still holds 2,246 rows (801 remain referenced by
    the 81 queue rows + `evidence` table).
  - Per spec, this task deletes ONLY promotion_queue rows; `citations` is intentionally NOT pruned.
    The 1,445 orphan citations are inert (unreferenced evidence) and do not affect production.db
    or promotion. A future cleanup (e.g. P150) may prune them — out of scope here.
- PRAGMA foreign_keys was OFF during delete (to allow queue-row removal without FK cascade);
  foreign_key_check confirms no dangling FK constraints exist post-delete.

## Reversibility
- `rollback.sql` re-inserts all 2,583 deleted rows (full column restore).
- pre-cleanup backup: `C:\Users\eltun\Documents\malt radar CLEAN\mr-kep\p149_queue_cleanup\backups\knowledge.db.pre_p149.20260717_151750.bak` (== KB BEFORE).
- original preserved as `knowledge.db.p149_old`.

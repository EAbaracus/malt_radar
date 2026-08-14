# P149C — Staged Files

The following 7 files were staged and committed (verified via `git show --name-only HEAD`):

| # | file |
|---|---|
| 1 | mr-kep/p149_queue_cleanup/cleanup_log.csv |
| 2 | mr-kep/p149_queue_cleanup/deleted_rows.csv |
| 3 | mr-kep/p149_queue_cleanup/remaining_queue.csv |
| 4 | mr-kep/p149_queue_cleanup/verification.md |
| 5 | mr-kep/p149_queue_cleanup/integrity_check.md |
| 6 | mr-kep/p149_queue_cleanup/executive_summary.md |
| 7 | mr-kep/p149_queue_cleanup/rollback.sql |

## Explicitly NOT committed (per spec)
- `mr-kep/p149_queue_cleanup/backups/` (contains knowledge.db.pre_p149.*.bak — a .db copy).
- `production.db`, `knowledge.db`, any `*.db`, `*.bak`, `knowledge.db.p149_old`.
- any `__pycache__/`, temporary scripts, scratch files.
- All other unrelated repo files (pre-existing modifications/untracked dirs).

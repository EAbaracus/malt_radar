# P150 — Deletion Candidates

Only safe, clearly-garbage files listed. Deletion requires explicit user authorization
(this audit is READ-ONLY and performs no deletion).

| path | size | reason | action |
|---|---|---|---|
| `nul` | 58 B | Windows reserved device-name file from a stray `> nul` redirect; no project data. | **DELETE** (safe) |

## NOT for deletion (keep as safety artifacts)
- `backups/production_pre_isolation_gate_20260715_224855.db` — pre-isolation production snapshot; recovery copy. Keep + gitignore.
- `knowledge.db.p149_old` — pre-P149 knowledge.db backup; rollback artifact. Keep + gitignore.
- `mr-kep/p149_queue_cleanup/backups/knowledge.db.pre_p149.*.bak` — P149 rollback backup. Keep + gitignore.

## Previous-session leftovers (ignore, don't delete)
- `.agents/`, `skills-lock.json`, `archive/` — runtime state; add to .gitignore, leave on disk.

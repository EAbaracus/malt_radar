# P203B — Migration

## How to apply
```bash
sqlite3 output/import/knowledge.db < mr-kep/p203b_crosswalk/migration.sql
```
## Pre-change gate (per AGENTS.md)
- Backup taken: `knowledge.db.pre_p203b.20260717_205445.bak`
- production.db hash BEFORE == AFTER (`8350fe9d…`) — zero production mutation.
## Reversible
- `rollback.sql` drops both tables; verified to restore pre-state cleanly (see rollback.md).
## No unrelated changes
- Only `distillery_crosswalk` + `distillery_crosswalk_review` added to knowledge.db.
## Indexes
- `idx_cw_external`, `idx_cw_entity`, `idx_cw_source`, `idx_cwr_external`.

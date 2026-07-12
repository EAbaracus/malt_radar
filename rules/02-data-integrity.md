# Rule 02: Data Integrity & DB Safety

Preserve the integrity of `production.db` at all costs.

## DB Rules:
1. Always create a pre-write backup in `output/import/backups/` named `production_[stage]_pre_[timestamp].db`.
2. Compute and log pre-write and post-write SHA256 hashes.
3. Run all writes inside a transaction (`BEGIN TRANSACTION` / `COMMIT`).
4. Execute `ROLLBACK` immediately if any error occurs.
5. Post-validation must include `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.

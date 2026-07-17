# Foreign Key Root Cause Analysis

## The Error
During `PRAGMA foreign_key_check`, SQLite returns the following fatal schema error:
```
sqlite3.OperationalError: foreign key mismatch - "price_history" referencing "whiskies"
```

## The Root Cause
SQLite strictly requires that any parent table referenced by a `FOREIGN KEY` constraint must enforce uniqueness on the referenced columns. Specifically, the referenced column(s) must be explicitly constrained by a `PRIMARY KEY` or a `UNIQUE` index.

1. The `price_history` table (and `staging_web_tasting_notes`) correctly declare a foreign key:
   `FOREIGN KEY (whisky_id) REFERENCES whiskies(whisky_id)`

2. However, the `whiskies` table schema is defined as:
   ```sql
   CREATE TABLE "whiskies" (
     "whisky_id" TEXT,
     "name" TEXT,
     "original_name" TEXT,
     "distillery_id" TEXT,
     ...
   )
   ```
   **Crucially, `whisky_id` lacks a `PRIMARY KEY` declaration and there is no `UNIQUE` index created for it.**

## Mechanism of Failure
Because `whiskies(whisky_id)` is not guaranteed unique by the schema, SQLite cannot safely evaluate referential integrity. 
- If `PRAGMA foreign_keys = ON` is enabled on the database connection, any `INSERT` into `price_history` or `UPDATE`/`DELETE` on `whiskies` will immediately crash with an `OperationalError`.
- If `PRAGMA foreign_key_check` is executed, SQLite halts the check entirely and throws the `OperationalError` because the schema itself is invalid.

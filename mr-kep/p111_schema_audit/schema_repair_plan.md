# Schema Repair Plan

SQLite does not support altering a table to add a `PRIMARY KEY` or `UNIQUE` constraint directly via `ALTER TABLE`. The following 5-step transactional procedure must be executed to repair the debt safely:

1. **Verify Uniqueness:**
   Run a `SELECT whisky_id, COUNT(*) FROM whiskies GROUP BY whisky_id HAVING COUNT(*) > 1;` query. Ensure the result is empty. Deduplicate if necessary.

2. **Begin Transaction:**
   `BEGIN IMMEDIATE;`

3. **Create shadow table with constraints:**
   ```sql
   CREATE TABLE whiskies_new (
       whisky_id TEXT PRIMARY KEY,
       name TEXT,
       original_name TEXT,
       distillery_id TEXT,
       ... (all other columns matching current schema)
   );
   ```

4. **Copy data to shadow table:**
   ```sql
   INSERT INTO whiskies_new SELECT * FROM whiskies;
   ```

5. **Swap and Commit:**
   ```sql
   DROP TABLE whiskies;
   ALTER TABLE whiskies_new RENAME TO whiskies;
   PRAGMA foreign_key_check; -- Should now return OK
   COMMIT;
   ```

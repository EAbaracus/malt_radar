# Migration Risk Assessment

## Operational Impact
- **Immediate Crash Risk: LOW.** The application is currently operating without `PRAGMA foreign_keys = ON`. Because SQLite defaults to unenforced foreign keys, DML operations (INSERT/UPDATE/DELETE) succeed without crashing the application.
- **Data Corruption Risk: HIGH.** Because foreign keys are not enforced, it is currently possible to:
  1. Insert a row into `price_history` with a non-existent `whisky_id` (orphan record).
  2. Delete a row from `whiskies` without cascading the deletion to `price_history`, leaving orphan records.
  3. Accidentally insert duplicate `whisky_id`s into `whiskies`, causing chaotic joins.

## Impact on Development & Migrations
- **Blocker:** The defect completely breaks `PRAGMA foreign_key_check`, preventing automated integrity testing during deployments or promotions.
- **Fragility:** If any future component or developer explicitly enables `PRAGMA foreign_keys = ON` on their connection pool, the application will begin experiencing immediate `OperationalError` crashes on writes.

## Overall Classification
**MEDIUM RISK** 
The system runs in its current state, but the lack of referential integrity enforcement exposes the database to silent corruption (orphan records). It represents significant technical debt that blocks proper relational database practices.

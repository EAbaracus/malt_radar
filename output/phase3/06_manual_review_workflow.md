# Manual Review Workflow

To protect the integrity of the master `whiskies` and `distilleries` tables, a Manual Review Workflow is mandatory for all incoming candidate data.

## Workflow Pipeline
1. **Ingestion**: Raw candidate CSV data is inserted into the respective `staging_*` table with `status = 'PENDING'`.
2. **Queue Generation**: A trigger or batch process creates a record in `staging_manual_review_queue` for every pending staging record.
3. **Admin Review Interface**: A user (administrator) examines the queue. The system provides:
   * The candidate data.
   * Suggested matches (via fuzzy matching or exact ID links).
   * Confidence scores and risk buckets.
4. **Resolution Action**: The user selects an action:
   * **CREATE_NEW**: Promotes the staging record to the master tables (e.g., inserts a new whisky).
   * **MERGE/LINK**: Discards the new record but links its sub-data (tasting notes, prices) to an existing master ID.
   * **DISCARD**: Rejects the candidate as a duplicate, false positive, or bad data.
5. **Execution**: The `resolution_action` is executed, moving data to master tables (if approved), and the staging record `status` is updated to `APPROVED` or `REJECTED`. The queue record receives a `resolved_at` timestamp.

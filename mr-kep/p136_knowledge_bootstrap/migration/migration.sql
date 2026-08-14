-- P136 migration.sql — idempotent forward migrations applied AFTER schema.sql.
-- Each block guarded by "IF NOT EXISTS" / version-gated checks so replay is safe.
-- New columns/tables for future web sources land here (never edit schema.sql in place
-- once applied to a real DB; add a new block below with an incremented guard).

-- Example future migration (web sources) — left as template, no-op until needed:
-- CREATE TABLE IF NOT EXISTS web_snapshots (
--     snapshot_id TEXT PRIMARY KEY,
--     source_id   TEXT NOT NULL,
--     url         TEXT NOT NULL,
--     fetched_at  TEXT,
--     raw_html    TEXT,
--     provenance  TEXT,
--     created_at  TEXT NOT NULL,
--     FOREIGN KEY (source_id) REFERENCES sources(source_id)
-- );

-- Index hygiene that may be added post-hoc:
-- CREATE INDEX IF NOT EXISTS idx_review_status ON review_queue(status);
-- CREATE INDEX IF NOT EXISTS idx_pq_entity ON promotion_queue(entity_key);

SELECT 'P136 migration.sql replayed (idempotent)';

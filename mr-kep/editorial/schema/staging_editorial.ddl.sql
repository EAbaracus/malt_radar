-- P201 staging schema. Lives in a SEPARATE staging database (NOT production.db).
-- Chosen over production.db staging_* tables because the task forbids production.db writes.
-- File target: mr-kep/editorial/staging_editorial.db  (created by the ingest tool, never committed).
-- Idempotent: evidence_id / source_url are natural keys; re-runs UPSERT, never duplicate.

PRAGMA foreign_keys = OFF;  -- staging-only; no FK to production.db (by design, production-safe)

CREATE TABLE IF NOT EXISTS staging_editorial_reviews (
    evidence_id                TEXT PRIMARY KEY,           -- EDR-<sha16>
    source_id                  TEXT NOT NULL,
    source_url                 TEXT NOT NULL UNIQUE,        -- dedup key (per robots-compliant fetch)
    authority_tier             TEXT NOT NULL,
    author                     TEXT,
    published_date             TEXT,
    content_hash               TEXT NOT NULL,              -- sha256 of raw page
    raw_name                   TEXT NOT NULL,
    normalized_name            TEXT NOT NULL,
    matched_master_whisky_id   TEXT,                        -- TEXT Wxxxxxx or NULL
    match_status               TEXT NOT NULL,
    match_confidence           REAL,
    score_value                REAL,
    score_scale_max            REAL,
    score_normalized           REAL,
    nose                       TEXT,
    palate                     TEXT,
    finish                     TEXT,
    conclusion                 TEXT,
    flavor_vector_json         TEXT NOT NULL,               -- canonical 7-axis JSON
    metadata_json              TEXT,                        -- optional specs JSON
    evidence_confidence        REAL NOT NULL,
    extraction_method          TEXT NOT NULL,
    provenance_state           TEXT NOT NULL DEFAULT 'staging_unverified',
    ingested_at                TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_editorial_src        ON staging_editorial_reviews(source_id);
CREATE INDEX IF NOT EXISTS idx_editorial_matched    ON staging_editorial_reviews(matched_master_whisky_id);
CREATE INDEX IF NOT EXISTS idx_editorial_prov       ON staging_editorial_reviews(provenance_state);

CREATE TABLE IF NOT EXISTS staging_editorial_profiles (
    profile_id                 TEXT PRIMARY KEY,            -- EDP-<sha16 of source_id+author>
    source_id                  TEXT NOT NULL,
    source_url                 TEXT,
    author                     TEXT NOT NULL,
    authority_tier             TEXT NOT NULL,
    review_count               INTEGER NOT NULL DEFAULT 0,
    avg_score                  REAL,
    style_vector_json          TEXT NOT NULL,               -- aggregate 7-axis of the critic
    evidence_confidence        REAL NOT NULL,
    provenance_state           TEXT NOT NULL DEFAULT 'staging_unverified'
);

CREATE INDEX IF NOT EXISTS idx_editorial_profile_src ON staging_editorial_profiles(source_id);

-- P136 knowledge.db — canonical production schema
-- Run via runtime/migrate.py (idempotent replay).
-- Every table: UUID PK (TEXT), created_at/updated_at (TEXT ISO8601),
-- confidence (REAL 0-1), source (TEXT), provenance (TEXT JSON).

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Migration tracking
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         INTEGER NOT NULL,
    description     TEXT,
    applied_at      TEXT NOT NULL,
    baseline_sig    TEXT
);

-- ---------------------------------------------------------------------------
-- Sources: every upstream origin (book, NotebookLM, SMWS, community, web)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id       TEXT PRIMARY KEY,            -- uuid
    source_type     TEXT NOT NULL,               -- book | notebooklm | smws | community | web
    source_name     TEXT NOT NULL,
    authority_tier  INTEGER NOT NULL,            -- T1=1 .. T4=4 (lower = higher authority)
    license_risk    TEXT DEFAULT 'unknown',      -- low | medium | high
    copyright_risk  TEXT DEFAULT 'unknown',
    url             TEXT,
    provenance      TEXT,                        -- JSON: ingest batch, tool version
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- ---------------------------------------------------------------------------
-- Books: one row per ingested book (PDF/EPUB)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS books (
    book_id         TEXT PRIMARY KEY,            -- uuid
    source_id       TEXT NOT NULL,
    title           TEXT,
    author          TEXT,
    isbn            TEXT,
    publisher       TEXT,
    file_hash       TEXT NOT NULL,               -- sha256 of source file (dedupe)
    format          TEXT,                        -- pdf | epub
    processed_at    TEXT,
    provenance      TEXT,
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- ---------------------------------------------------------------------------
-- book_pages: OCR/chunk output, page-aligned provenance
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS book_pages (
    page_id         TEXT PRIMARY KEY,            -- uuid
    book_id         TEXT NOT NULL,
    page_number     INTEGER,
    section         TEXT,
    raw_text        TEXT,
    parser_confidence REAL,                      -- OCR quality 0-1
    source          TEXT,
    provenance      TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

-- ---------------------------------------------------------------------------
-- citations: one per source fact anchor (book+page, smws pdf, notebooklm run)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS citations (
    citation_id     TEXT PRIMARY KEY,            -- uuid
    source_id       TEXT NOT NULL,
    book_id         TEXT,
    page_number     INTEGER,
    chunk_id        TEXT,
    raw_text        TEXT,
    source_hash     TEXT,                        -- sha256 of cited text (dedupe)
    source          TEXT,
    provenance      TEXT,
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

-- ---------------------------------------------------------------------------
-- evidence: extracted field-level claim (normalization stage output)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id     TEXT PRIMARY KEY,            -- uuid
    citation_id     TEXT NOT NULL,
    entity_key      TEXT,                        -- whisky_id or distillery_id (temp/resolved)
    entity_type     TEXT,                        -- whisky | distillery | brand | bottler
    field_name      TEXT NOT NULL,               -- abv | age | cask_type | tasting_note ...
    field_value     TEXT NOT NULL,
    normalized_value TEXT,                       -- after normalize stage
    extraction_method TEXT,                      -- regex | llm | lookup
    model_version   TEXT,
    confidence      REAL DEFAULT 0.0,
    signal_confidence REAL,                      -- cross-source agreement
    source          TEXT,
    provenance      TEXT,
    status          TEXT DEFAULT 'ACTIVE',       -- ACTIVE | SUPERSEDED | REJECTED
    created_at      TEXT NOT NULL,
    FOREIGN KEY (citation_id) REFERENCES citations(citation_id)
);

-- ---------------------------------------------------------------------------
-- canonical_flavor_vectors: consensus 7-axis (smoky,peaty,fruity,sweet,spicy,maritime,sherry)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS canonical_flavor_vectors (
    vector_id       TEXT PRIMARY KEY,            -- uuid
    entity_key      TEXT NOT NULL,               -- whisky_id (resolved)
    entity_type     TEXT DEFAULT 'whisky',
    smoky           REAL, peaty REAL, fruity REAL, sweet REAL,
    spicy           REAL, maritime REAL, sherry REAL,
    axis_scale      TEXT DEFAULT '0-100',        -- normalized input scale
    consensus_method TEXT,                       -- mean | weighted_mean | median
    source_count    INTEGER DEFAULT 0,           -- # corroborating evidence
    confidence      REAL DEFAULT 0.0,
    source          TEXT,
    provenance      TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- ---------------------------------------------------------------------------
-- canonical_tasting_notes: append-only per (entity, source)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS canonical_tasting_notes (
    note_id         TEXT PRIMARY KEY,            -- uuid
    entity_key      TEXT NOT NULL,
    entity_type     TEXT DEFAULT 'whisky',
    nose            TEXT, palate TEXT, finish TEXT,
    note_hash       TEXT,                        -- dedupe key
    source          TEXT,
    provenance      TEXT,
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- normalized_metadata: resolved entity attributes (post-consensus)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS normalized_metadata (
    entity_key      TEXT PRIMARY KEY,            -- whisky_id / distillery_id
    entity_type     TEXT NOT NULL,
    name            TEXT,
    distillery_id   TEXT,
    country         TEXT,
    region          TEXT,
    type            TEXT,
    age             REAL,
    abv             REAL,
    nas             INTEGER,
    cask_type       TEXT,                        -- ';'-joined canonical casks
    finish_type     TEXT,
    bottle_size     REAL,
    cask_strength   INTEGER,
    brand           TEXT,
    meta_critic_score REAL,
    data_confidence REAL,
    completed_fields INTEGER,
    notes_for_review TEXT,
    source          TEXT,
    provenance      TEXT,
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- ---------------------------------------------------------------------------
-- confidence: per-field confidence ledger (audit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS confidence (
    conf_id         TEXT PRIMARY KEY,            -- uuid
    entity_key      TEXT NOT NULL,
    field_name      TEXT NOT NULL,
    field_conf      REAL NOT NULL,
    extraction_conf REAL,
    parser_conf     REAL,
    signal_conf     REAL,
    source_conf     REAL,
    source_tier     INTEGER,
    source          TEXT,
    provenance      TEXT,
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- promotion_queue: rows ready for production promotion (gated)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS promotion_queue (
    queue_id        TEXT PRIMARY KEY,            -- uuid
    entity_key      TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    field_name      TEXT NOT NULL,
    current_value   TEXT,
    proposed_value  TEXT NOT NULL,
    field_class     TEXT NOT NULL,               -- IMMUTABLE|APPEND|REPLACEABLE|REVIEW
    action          TEXT NOT NULL,               -- APPLY|APPEND|REVIEW|REJECT
    confidence      REAL DEFAULT 0.0,
    citation_id     TEXT,
    source          TEXT,
    dedupe_key      TEXT UNIQUE,                 -- (entity,field,source_hash) — enforces C2 idempotency
    status          TEXT DEFAULT 'pending',      -- pending|approved|promoted|rejected
    created_at      TEXT NOT NULL,
    FOREIGN KEY (citation_id) REFERENCES citations(citation_id)
);

-- ---------------------------------------------------------------------------
-- review_queue: REVIEW-REQUIRED / conflict / ambiguous items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_queue (
    review_id       TEXT PRIMARY KEY,            -- uuid
    entity_key      TEXT,
    entity_type     TEXT,
    issue_type      TEXT NOT NULL,               -- conflict|identity|low_conf|historical
    detail          TEXT,
    suggested_action TEXT,
    source          TEXT,
    provenance      TEXT,
    status          TEXT DEFAULT 'open',         -- open|resolved|ignored
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- source_priority: configured precedence (P135 conflict_policy)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_priority (
    priority_id     TEXT PRIMARY KEY,            -- uuid
    source_type     TEXT NOT NULL,
    authority_tier  INTEGER NOT NULL,
    rank            INTEGER NOT NULL,            -- 1 = highest
    notes           TEXT,
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- merge_history: every applied merge (idempotency + audit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS merge_history (
    merge_id        TEXT PRIMARY KEY,            -- uuid
    entity_key      TEXT NOT NULL,
    field_name      TEXT NOT NULL,
    value_before    TEXT,
    value_after     TEXT,
    action          TEXT NOT NULL,
    citation_id     TEXT,
    dedupe_key      TEXT UNIQUE,                 -- enforces C2 idempotency
    source          TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (citation_id) REFERENCES citations(citation_id)
);

-- ---------------------------------------------------------------------------
-- processing_log: stage-level run log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processing_log (
    log_id          TEXT PRIMARY KEY,            -- uuid
    run_id          TEXT NOT NULL,
    stage           TEXT NOT NULL,               -- raw|normalize|canonicalize|merge|consensus|queue|review|export
    action          TEXT,
    target_table    TEXT,
    target_record   TEXT,
    detail          TEXT,
    status          TEXT DEFAULT 'ok',           -- ok|warn|error
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Indexes (performance + dedupe)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_books_hash      ON books(file_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_entity ON evidence(entity_key, field_name);
CREATE INDEX IF NOT EXISTS idx_evidence_cit    ON evidence(citation_id);
CREATE INDEX IF NOT EXISTS idx_cit_hash        ON citations(source_hash);
CREATE INDEX IF NOT EXISTS idx_vec_entity      ON canonical_flavor_vectors(entity_key);
CREATE INDEX IF NOT EXISTS idx_note_entity     ON canonical_tasting_notes(entity_key);
CREATE INDEX IF NOT EXISTS idx_note_hash       ON canonical_tasting_notes(note_hash);
CREATE INDEX IF NOT EXISTS idx_meta_entity     ON normalized_metadata(entity_key);
CREATE INDEX IF NOT EXISTS idx_pq_dedupe       ON promotion_queue(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_pq_status       ON promotion_queue(status);
CREATE INDEX IF NOT EXISTS idx_mh_dedupe       ON merge_history(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_conf_entity     ON confidence(entity_key, field_name);
CREATE INDEX IF NOT EXISTS idx_src_type        ON sources(source_type);

CREATE TABLE books (
    book_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    isbn TEXT UNIQUE,
    publisher TEXT
);

CREATE TABLE book_versions (
    version_id TEXT PRIMARY KEY,
    book_id TEXT REFERENCES books(book_id) ON DELETE CASCADE,
    file_hash TEXT NOT NULL UNIQUE,
    format TEXT,
    processed_at TEXT
);

CREATE TABLE citations (
    citation_id TEXT PRIMARY KEY,
    version_id TEXT REFERENCES book_versions(version_id) ON DELETE CASCADE,
    page_number INTEGER,
    chunk_id TEXT,
    raw_text TEXT NOT NULL,
    source_hash TEXT NOT NULL
);

CREATE INDEX idx_citations_version ON citations(version_id);
CREATE INDEX idx_citations_hash ON citations(source_hash);

CREATE TABLE evidence_nodes (
    evidence_id TEXT PRIMARY KEY,
    citation_id TEXT REFERENCES citations(citation_id),
    extraction_method TEXT,
    model_version TEXT,
    extracted_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'ARCHIVED'))
);

CREATE INDEX idx_evidence_citation ON evidence_nodes(citation_id);

CREATE TABLE extracted_facts (
    fact_id TEXT PRIMARY KEY,
    evidence_id TEXT REFERENCES evidence_nodes(evidence_id),
    entity_key_raw TEXT,
    descriptor_raw TEXT,
    confidence_score REAL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'ARCHIVED'))
);

CREATE INDEX idx_facts_evidence ON extracted_facts(evidence_id);
CREATE INDEX idx_facts_entity ON extracted_facts(entity_key_raw);

CREATE TABLE consensus_nodes (
    consensus_id TEXT PRIMARY KEY,
    whisky_id TEXT NOT NULL,
    algorithm_version TEXT,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'ARCHIVED')),
    UNIQUE(whisky_id, algorithm_version)
);

CREATE INDEX idx_consensus_whisky ON consensus_nodes(whisky_id);

CREATE TABLE canonical_vectors (
    vector_id TEXT PRIMARY KEY,
    consensus_id TEXT REFERENCES consensus_nodes(consensus_id),
    smoky INTEGER,
    peaty INTEGER,
    fruity INTEGER,
    sweet INTEGER,
    spicy INTEGER,
    maritime INTEGER,
    sherry INTEGER,
    UNIQUE(consensus_id)
);

CREATE INDEX idx_vector_consensus ON canonical_vectors(consensus_id);

CREATE TABLE promotion_runs (
    run_id TEXT PRIMARY KEY,
    run_timestamp TEXT NOT NULL,
    run_hash TEXT NOT NULL,
    status TEXT
);

CREATE INDEX idx_promo_run_hash ON promotion_runs(run_hash);

CREATE TABLE promotion_candidates (
    candidate_id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES promotion_runs(run_id),
    vector_id TEXT REFERENCES canonical_vectors(vector_id),
    whisky_id TEXT,
    promotion_status TEXT
);

CREATE INDEX idx_promo_candidate_run ON promotion_candidates(run_id);

CREATE TABLE audit_logs (
    log_id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES promotion_runs(run_id),
    action TEXT,
    target_table TEXT,
    target_record TEXT,
    details TEXT,
    created_at TEXT
);

CREATE INDEX idx_audit_run ON audit_logs(run_id);

CREATE TABLE schema_metadata (
    schema_version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL,
    baseline_schema_signature TEXT NOT NULL
);

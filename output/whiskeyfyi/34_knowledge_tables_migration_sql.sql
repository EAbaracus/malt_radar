CREATE TABLE IF NOT EXISTS knowledge_regions (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    source_id VARCHAR(100) UNIQUE,
    region_name VARCHAR(100),
    country VARCHAR(100),
    description TEXT,
    url VARCHAR(255),
    confidence VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_glossary_terms (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    term VARCHAR(255) UNIQUE,
    definition TEXT,
    category VARCHAR(100),
    url VARCHAR(255),
    confidence VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_guides (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    title VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    category VARCHAR(100),
    summary TEXT,
    url VARCHAR(255),
    import_recommendation VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS external_reference_links (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50), -- e.g. 'distillery'
    entity_uuid UUID,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    url VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

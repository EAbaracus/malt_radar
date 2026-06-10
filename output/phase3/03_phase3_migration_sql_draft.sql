-- Phase 3 Migration SQL Draft
-- NOTE: THIS IS A DRAFT. DO NOT EXECUTE AGAINST PRODUCTION.

-- 1. Entity Master Tables
CREATE TABLE brands (
    brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bottlers (
    bottler_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bottler_name TEXT NOT NULL UNIQUE,
    country TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    headquarters TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE external_entities (
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL UNIQUE,
    entity_type TEXT,
    base_url TEXT
);

CREATE TABLE entity_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL, -- 'brand', 'bottler', 'company', 'distillery'
    entity_id INTEGER NOT NULL,
    alias_name TEXT NOT NULL
);

CREATE TABLE entity_external_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    link_type TEXT -- 'wikipedia', 'official', 'api'
);

-- 2. Relationship Tables
CREATE TABLE whisky_product_entities (
    whisky_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    relationship_type TEXT, -- 'owned_by', 'branded_as'
    PRIMARY KEY (whisky_id, entity_type, entity_id)
);

CREATE TABLE distillery_company_links (
    distillery_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    ownership_start_year INTEGER,
    ownership_end_year INTEGER,
    PRIMARY KEY (distillery_id, company_id)
);

CREATE TABLE bottler_product_links (
    whisky_id INTEGER NOT NULL,
    bottler_id INTEGER NOT NULL,
    bottling_year INTEGER,
    PRIMARY KEY (whisky_id, bottler_id)
);

-- 3. Staging Tables
CREATE TABLE staging_new_products (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT,
    raw_name TEXT,
    raw_distillery TEXT,
    raw_age TEXT,
    raw_vintage TEXT,
    raw_abv TEXT,
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging_tasting_notes (
    staging_note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT,
    staging_product_id INTEGER, -- nullable
    whisky_id INTEGER, -- nullable (if mapped to master)
    nose TEXT,
    palate TEXT,
    finish TEXT,
    status TEXT DEFAULT 'PENDING'
);

CREATE TABLE staging_historical_menu_prices (
    staging_price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whisky_id INTEGER NOT NULL,
    malt_list_name TEXT,
    historical_menu_price REAL,
    currency TEXT DEFAULT 'GBP',
    pour_size_ml INTEGER DEFAULT 35,
    price_context TEXT,
    source_name TEXT,
    status TEXT DEFAULT 'PENDING'
);

CREATE TABLE staging_external_reviews (
    staging_review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT,
    whisky_id INTEGER,
    reviewer_name TEXT,
    score REAL,
    review_text TEXT,
    status TEXT DEFAULT 'PENDING'
);

CREATE TABLE staging_manual_review_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    staging_table_name TEXT NOT NULL,
    staging_record_id INTEGER NOT NULL,
    assigned_to TEXT,
    review_notes TEXT,
    resolution_action TEXT, -- 'CREATE_NEW', 'MERGE', 'DISCARD'
    resolved_at TIMESTAMP
);

-- 4. Knowledge Tables
CREATE TABLE knowledge_regions (
    region_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE,
    description TEXT,
    characteristics TEXT
);

CREATE TABLE knowledge_glossary_terms (
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL UNIQUE,
    definition TEXT NOT NULL
);

CREATE TABLE knowledge_guides (
    guide_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    published_date DATE
);

CREATE TABLE external_reference_links (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_table TEXT NOT NULL,
    knowledge_id INTEGER NOT NULL,
    url TEXT NOT NULL
);

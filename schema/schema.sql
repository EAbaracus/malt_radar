-- ============================================================================
-- Malt Radar - Canonical SQLite Schema
-- Schema version : canonical-1 (P56, regenerated from live)
-- Generated (UTC): 2026-07-12T17:32:52Z
-- Source         : output/import/production.db (live, single source of truth)
-- Method         : regenerated verbatim from sqlite_master (syntax preserved)
-- Object counts  : tables=34, indexes=3, views=0, triggers=0
-- SHA256(ddl)    : 7e75d35052da5b3d01d663ba9296c6e9a3dc45829573476264573423e806e9b9   -- hash of DDL body below (timestamp excluded)
-- ============================================================================

-- ----- TABLES (34) -----
CREATE TABLE bottler_product_links (
    whisky_id INTEGER NOT NULL,
    bottler_id INTEGER NOT NULL,
    bottling_year INTEGER,
    PRIMARY KEY (whisky_id, bottler_id)
);

CREATE TABLE bottlers (
    bottler_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bottler_name TEXT NOT NULL UNIQUE,
    country TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE brands (
    brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    headquarters TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "distilleries" (
"distillery_id" TEXT,
  "name" TEXT,
  "country" TEXT,
  "region" TEXT,
  "owner" REAL,
  "parent_company" REAL,
  "founded_year" REAL,
  "founder" REAL,
  "status" REAL,
  "location" REAL,
  "coordinates" REAL,
  "official_website" REAL,
  "wikidata_id" REAL,
  "wikipedia_url" REAL,
  "data_confidence" TEXT,
  "notes_for_review" REAL
);

CREATE TABLE distillery_company_links (
    distillery_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    ownership_start_year INTEGER,
    ownership_end_year INTEGER,
    PRIMARY KEY (distillery_id, company_id)
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

CREATE TABLE external_entities (
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL UNIQUE,
    entity_type TEXT,
    base_url TEXT
);

CREATE TABLE external_reference_links (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_table TEXT NOT NULL,
    knowledge_id INTEGER NOT NULL,
    url TEXT NOT NULL
);

CREATE TABLE "flavor_profiles" (
"whisky_id" TEXT,
  "whisky_name" TEXT,
  "production_bottle_name" TEXT,
  "match_score" INTEGER,
  "match_method" TEXT,
  "flavor_vector" TEXT,
  "flavor_profile" TEXT,
  "flavor_tags" TEXT,
  "flavor_source" TEXT,
  "flavor_data_confidence" TEXT,
  "production_price" REAL,
  "production_rating" REAL,
  "production_region" TEXT,
  "notes_for_review" TEXT
, source_count INTEGER DEFAULT 1, evidence_count INTEGER DEFAULT 1, enrichment_version INTEGER DEFAULT 1);

CREATE TABLE knowledge_glossary_terms (
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL UNIQUE,
    definition TEXT NOT NULL
, source TEXT, category TEXT, url TEXT, confidence TEXT);

CREATE TABLE knowledge_guides (
    guide_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    published_date DATE
, source TEXT, slug TEXT, category TEXT, summary TEXT, url TEXT, import_recommendation TEXT);

CREATE TABLE knowledge_regions (
    region_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE,
    description TEXT,
    characteristics TEXT
, source TEXT, source_id TEXT, country TEXT, url TEXT, confidence TEXT);

CREATE TABLE official_source_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    source_category TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    confidence REAL DEFAULT 1.0,
    retrieved_at TEXT NOT NULL,
    license_risk TEXT DEFAULT 'low',
    copyright_risk TEXT DEFAULT 'low',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE price_history (
            price_id TEXT PRIMARY KEY,
            whisky_id TEXT,
            source_name TEXT,
            source_record_key TEXT,
            price_value REAL,
            currency TEXT,
            price_context TEXT,
            pour_size_ml REAL,
            observed_at TEXT,
            source_file TEXT,
            source_url TEXT,
            approval_status TEXT,
            import_recommendation TEXT,
            created_at TEXT
            ,FOREIGN KEY (whisky_id) REFERENCES whiskies(whisky_id)
        );

CREATE TABLE promotion_audit_log (
    promotion_id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_record_id TEXT,
    promotion_status TEXT NOT NULL,
    promoted_by TEXT,
    promotion_note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE review_actions (
    action_id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    review_status TEXT NOT NULL,
    action_type TEXT NOT NULL,
    reviewer TEXT,
    reviewer_note TEXT,
    previous_status TEXT,
    new_status TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE review_conflict_log (
    conflict_id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_record_key TEXT,
    conflict_type TEXT NOT NULL,
    conflict_detail TEXT,
    resolution_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE review_status_transitions (
    transition_id TEXT PRIMARY KEY,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    action_type TEXT NOT NULL,
    allowed INTEGER NOT NULL DEFAULT 1,
    requires_note INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE staging_book_flavor_profiles (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whisky_id TEXT NOT NULL,
    whisky_name TEXT,
    production_bottle_name TEXT,
    match_score INTEGER,
    match_method TEXT,
    flavor_vector TEXT,
    flavor_profile TEXT,
    flavor_tags TEXT,
    flavor_source TEXT,
    flavor_data_confidence TEXT,
    production_region TEXT,
    notes_for_review TEXT,
    
    -- Staging/Review metadata
    source_system TEXT,
    source_book TEXT,
    source_page_or_section TEXT,
    distillery_name TEXT,
    age_statement TEXT,
    cask_or_maturation TEXT,
    abv REAL,
    nose_summary TEXT,
    palate_summary TEXT,
    finish_summary TEXT,
    overall_style_summary TEXT,
    match_strategy TEXT,
    decision_reason TEXT,
    conflict_existing_profile INTEGER DEFAULT 0,
    radar_conflict INTEGER DEFAULT 0,
    approval_status TEXT DEFAULT 'staging_pending_review',
    reviewer_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Radar Raw Columns
    smoky INTEGER,
    peaty INTEGER,
    sherry INTEGER,
    fruity INTEGER,
    floral INTEGER,
    spicy INTEGER,
    sweet INTEGER,
    oak INTEGER,
    maritime INTEGER,
    winey INTEGER,
    malty INTEGER,
    nutty INTEGER,
    herbal INTEGER,
    waxy INTEGER,
    oily INTEGER,
    light_body INTEGER,
    rich_body INTEGER
, extraction_method TEXT);

CREATE TABLE staging_external_reviews (
    staging_review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT,
    whisky_id INTEGER,
    reviewer_name TEXT,
    score REAL,
    review_text TEXT,
    status TEXT DEFAULT 'PENDING'
);

CREATE TABLE staging_flavor_profile_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT NOT NULL,
            whisky_name TEXT,
            production_bottle_name TEXT,
            source_system TEXT,
            source_type TEXT,
            source_url TEXT,
            source_file TEXT,
            source_title TEXT,
            source_ref TEXT,
            traceability_status TEXT,
            candidate_class TEXT,
            flavor_profile TEXT,
            flavor_vector TEXT,
            flavor_tags TEXT,
            evidence_summary TEXT,
            active_axis_count INTEGER,
            max_score REAL,
            source_confidence REAL,
            signal_confidence REAL,
            overall_confidence REAL,
            duplicate_risk INTEGER DEFAULT 0,
            qa_status TEXT DEFAULT 'pending_review',
            import_status TEXT DEFAULT 'staging_candidate',
            notes_for_review TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE staging_flavor_profile_candidates_full (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT,
            whisky_name TEXT,
            production_bottle_name TEXT,
            source_system TEXT,
            source_type TEXT,
            source_url TEXT,
            source_file TEXT,
            source_title TEXT,
            source_ref TEXT,
            traceability_status TEXT,
            candidate_class TEXT,
            flavor_profile TEXT,
            flavor_vector TEXT,
            flavor_tags TEXT,
            evidence_summary TEXT,
            active_axis_count INTEGER,
            max_score REAL,
            source_confidence REAL,
            signal_confidence REAL,
            overall_confidence REAL,
            duplicate_risk INTEGER,
            qa_status TEXT,
            import_status TEXT,
            notes_for_review TEXT,
            created_at TEXT
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
, master_name TEXT, source_file TEXT, source_confidence TEXT, risk_level TEXT, approval_status TEXT, import_recommendation TEXT);

CREATE TABLE staging_manual_review_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    staging_table_name TEXT NOT NULL,
    staging_record_id INTEGER NOT NULL,
    assigned_to TEXT,
    review_notes TEXT,
    resolution_action TEXT, -- 'CREATE_NEW', 'MERGE', 'DISCARD'
    resolved_at TIMESTAMP
, source_name TEXT, source_file TEXT, candidate_type TEXT, candidate_name TEXT, related_whisky_id TEXT, related_entity_name TEXT, issue_type TEXT, reason TEXT, suggested_action TEXT, approval_status TEXT);

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
, source_name TEXT, source_id TEXT, source_slug TEXT, product_name TEXT, distillery_name TEXT, bottler_name TEXT, brand_name TEXT, country TEXT, region TEXT, age TEXT, abv TEXT, product_type TEXT, source_url TEXT, triage_status TEXT, approval_status TEXT, import_recommendation TEXT);

CREATE TABLE staging_notebooklm_flavor_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT NOT NULL,
            whisky_name TEXT,
            source_whisky_name TEXT,
            source_system TEXT NOT NULL,
            source_hint TEXT,
            confidence TEXT,
            match_score REAL,
            match_name_score REAL,
            match_distillery_score REAL,
            nose_summary TEXT,
            palate_summary TEXT,
            finish_summary TEXT,
            flavour_tags TEXT,
            smoky REAL,
            sherry REAL,
            fruity REAL,
            sweet REAL,
            spicy REAL,
            oaky REAL,
            maritime REAL,
            approval_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(whisky_id, source_system)
        );

CREATE TABLE staging_p6_flavor_profile_candidates (
                whisky_id TEXT,
                whisky_name TEXT,
                production_bottle_name TEXT,
                source_system TEXT,
                source_type TEXT,
                source_url TEXT,
                source_file TEXT,
                source_title TEXT,
                source_ref TEXT,
                traceability_status TEXT,
                flavor_profile TEXT,
                flavor_vector TEXT,
                flavor_tags TEXT,
                evidence_summary TEXT,
                active_axis_count INTEGER,
                max_score REAL,
                source_confidence REAL,
                signal_confidence REAL,
                overall_confidence REAL,
                approval_status TEXT,
                created_at TEXT
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
, source_name TEXT, source_review_id TEXT, source_slug TEXT, product_name TEXT, source_url TEXT, conclusion TEXT, source_verified TEXT, matched_master_whisky_id TEXT, match_status TEXT, approval_status TEXT, import_recommendation TEXT);

CREATE TABLE staging_web_tasting_notes (
            staging_note_id TEXT PRIMARY KEY,
            whisky_id TEXT NOT NULL,
            whisky_name TEXT NOT NULL,
            source_system TEXT NOT NULL,
            source_url TEXT,
            raw_note_text TEXT NOT NULL,
            nose TEXT,
            palate TEXT,
            finish TEXT,
            overall TEXT,
            confidence_score REAL,
            extraction_method TEXT NOT NULL,
            approval_status TEXT NOT NULL DEFAULT 'staging_pending_review',
            created_at TEXT NOT NULL,
            FOREIGN KEY(whisky_id) REFERENCES whiskies(whisky_id)
        );

CREATE TABLE "tasting_notes" (
"whisky_id" TEXT,
  "normalized_name" TEXT,
  "distillery_id" TEXT,
  "source_url" REAL,
  "source_name" REAL,
  "data_confidence" TEXT,
  "notes_for_review" REAL,
  "nose_notes" TEXT,
  "palate_notes" TEXT,
  "finish_notes" TEXT,
  "aroma_tags" REAL
, source_system TEXT, source_doc TEXT, source_entry_number TEXT);

CREATE TABLE "whiskies" (
"whisky_id" TEXT,
  "name" TEXT,
  "original_name" TEXT,
  "distillery_id" TEXT,
  "country" TEXT,
  "region" TEXT,
  "type" TEXT,
  "age" REAL,
  "age_statement" TEXT,
  "nas" TEXT,
  "abv" REAL,
  "bottle_size" REAL,
  "cask_type" TEXT,
  "finish_type" REAL,
  "cask_strength" TEXT,
  "meta_critic_score" REAL,
  "user_score" REAL,
  "data_confidence" TEXT,
  "completed_fields" TEXT,
  "notes_for_review" TEXT,
  "brand" TEXT
);

CREATE TABLE whisky_product_entities (
    whisky_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    relationship_type TEXT, -- 'owned_by', 'branded_as'
    PRIMARY KEY (whisky_id, entity_type, entity_id)
);

-- ----- INDEXES (3) -----
CREATE INDEX idx_staging_book_flavor_profiles_approval_status ON staging_book_flavor_profiles(approval_status);

CREATE INDEX idx_staging_book_flavor_profiles_source_system ON staging_book_flavor_profiles(source_system);

CREATE INDEX idx_staging_book_flavor_profiles_whisky_id ON staging_book_flavor_profiles(whisky_id);

-- ----- source_audit (ETL provenance log) -----
-- Created here so `ingest()` (which replays schema.sql) provisions the table
-- before inserting audit rows. Missing from the original schema → ingestion
-- tests failed with "no such table: source_audit".
CREATE TABLE source_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT,
    source_type TEXT,
    domain TEXT,
    extraction_timestamp TEXT,
    extracted_records_count INTEGER,
    status TEXT
);

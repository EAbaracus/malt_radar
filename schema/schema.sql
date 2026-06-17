-- SQLite schema

CREATE TABLE countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    name TEXT NOT NULL,
    UNIQUE(name, country_id),
    FOREIGN KEY(country_id) REFERENCES countries(id)
);

CREATE TABLE distilleries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_distillery_id TEXT UNIQUE,
    name TEXT UNIQUE NOT NULL,
    country_id INTEGER,
    region_id INTEGER,
    status TEXT,
    production_capacity_lpa REAL,
    number_of_stills INTEGER,
    official_website TEXT,
    confidence_score TEXT,
    notes TEXT,
    FOREIGN KEY(country_id) REFERENCES countries(id),
    FOREIGN KEY(region_id) REFERENCES regions(id)
);

CREATE TABLE independent_bottlers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    country_id INTEGER,
    official_website TEXT,
    confidence_score TEXT,
    notes TEXT,
    FOREIGN KEY(country_id) REFERENCES countries(id)
);

CREATE TABLE whisky_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_whisky_id TEXT UNIQUE,
    name TEXT NOT NULL,
    distillery_id INTEGER,
    bottler_id INTEGER,
    bottling_type TEXT,
    age_statement INTEGER,
    vintage_year INTEGER,
    bottling_year INTEGER,
    release_year INTEGER,
    number_of_bottles INTEGER,
    abv REAL,
    price_original REAL,
    price_currency TEXT,
    product_url TEXT,
    confidence_score TEXT,
    notes TEXT,
    FOREIGN KEY(distillery_id) REFERENCES distilleries(id),
    FOREIGN KEY(bottler_id) REFERENCES independent_bottlers(id)
);

CREATE TABLE cask_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE product_cask_types (
    product_id INTEGER,
    cask_type_id INTEGER,
    PRIMARY KEY(product_id, cask_type_id),
    FOREIGN KEY(product_id) REFERENCES whisky_products(id),
    FOREIGN KEY(cask_type_id) REFERENCES cask_types(id)
);

CREATE TABLE flavor_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE product_flavor_tags (
    product_id INTEGER,
    flavor_tag_id INTEGER,
    PRIMARY KEY(product_id, flavor_tag_id),
    FOREIGN KEY(product_id) REFERENCES whisky_products(id),
    FOREIGN KEY(flavor_tag_id) REFERENCES flavor_tags(id)
);

CREATE TABLE source_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT,
    source_type TEXT,
    domain TEXT,
    extraction_timestamp TEXT,
    extracted_records_count INTEGER,
    status TEXT
);

CREATE TABLE entity_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    UNIQUE(entity_type, entity_id, source_url)
);

CREATE TABLE rejected_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT,
    scraped_product_name TEXT,
    unmatched_field TEXT,
    source_value TEXT,
    database_value TEXT,
    match_attempt_date TEXT,
    problem_type TEXT
);

CREATE TABLE review_needed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,
    entity_name TEXT,
    field_name TEXT,
    current_value TEXT,
    problem_reason TEXT,
    suggested_action TEXT,
    source_urls TEXT,
    confidence_score TEXT
);

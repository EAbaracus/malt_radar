import csv
import sqlite3
import json
import os
import re
import argparse
from datetime import datetime

NULL_EQUIVALENTS = {"unknown", "", "-", ",", "null", "none", "na", "nas"}

COLUMN_ALIASES = {
    # General aliases
    "name": "name",
    "country": "country", "region": "region",
    
    # Distillery aliases
    "distillery_id": "original_distillery_id",
    "production_capacity": "production_capacity_lpa", "production_capacity_lpa": "production_capacity_lpa", "capacity": "production_capacity_lpa",
    "number_of_stills": "number_of_stills", "stills": "number_of_stills",
    
    # Bottler aliases
    "bottler": "bottler_name", "bottler_name": "bottler_name", "brand": "bottler_name",
    
    # Whisky products aliases
    "product_name": "name", "production_bottle_name": "name", "whisky_name": "name",
    "whisky_id": "original_whisky_id",
    "bottling_type": "bottling_type", "type": "bottling_type",
    "age_statement": "age_statement", "age": "age_statement", "age_years": "age_statement",
    "vintage_year": "vintage_year", "vintage": "vintage_year",
    "bottling_year": "bottling_year", "bottled": "bottling_year",
    "release_year": "release_year",
    "number_of_bottles": "number_of_bottles",
    "abv": "abv", "alcohol": "abv",
    "price_original": "price_original", "price": "price_original", "production_price": "price_original",
    "price_currency": "price_currency", "currency": "price_currency",
    "product_url": "product_url",
    "source_urls": "source_urls", "urls": "source_urls",
    "flavor_profile_keywords": "flavor_profile_keywords", "flavor_tags": "flavor_profile", "flavor_profile": "flavor_profile",
    "cask_type": "cask_type",
    "source_dataset": "source_dataset",
    "image": "image_url", "image_url": "image_url",
    
    # Common
    "status": "status",
    "confidence_score": "confidence_score", "confidence": "confidence_score", "data_confidence": "confidence_score",
    "official_website": "official_website", "website": "official_website",
    "notes": "notes", "notes_for_review": "notes",
    
    # Source audit
    "source_title": "source_title", "source_type": "source_type", "domain": "domain",
    "extraction_timestamp": "extraction_timestamp", "extracted_records_count": "extracted_records_count",
    
    # Rejected matches
    "scraped_product_name": "scraped_product_name", "unmatched_field": "unmatched_field",
    "source_value": "source_value", "database_value": "database_value",
    "match_attempt_date": "match_attempt_date", "problem_type": "problem_type",
    
    # Review needed
    "entity_type": "entity_type", "entity_name": "entity_name", "field_name": "field_name",
    "current_value": "current_value", "problem_reason": "problem_reason", "suggested_action": "suggested_action"
}

NUMERICAL_COLUMNS = {
    "production_capacity_lpa": float,
    "number_of_stills": int,
    "age_statement": int,
    "vintage_year": int,
    "bottling_year": int,
    "release_year": int,
    "number_of_bottles": int,
    "abv": float,
    "price_original": float,
    "extracted_records_count": int
}

ENUM_ALLOWED_VALUES = {
    "status": {"active", "closed", "mothballed", "planned", "demolished", "silent"},
    "confidence_score": {"high", "medium", "low", "manual_review", "rejected"},
    "bottling_type": {"official", "independent"},
    "source_type": {"api", "scraper", "manual", "bulk"},
    "audit_status": {"success", "partial", "failed"},
    "problem_type": {"name_mismatch", "missing_entity", "data_conflict", "formatting_error"}
}

class IngestionReport:
    def __init__(self):
        self.total_rows_read = 0
        self.inserted_countries = 0
        self.inserted_regions = 0
        self.inserted_distilleries = 0
        self.inserted_independent_bottlers = 0
        self.inserted_whisky_products = 0
        self.skipped_products = 0
        self.duplicate_products_reused = 0
        self.source_urls_inserted = 0
        self.existing_review_imported = 0
        self.etl_generated_review = 0
        self.rejected_matches_count = 0
        self.failed_rows = 0
        self.low_confidence_count = 0
        self.database_integrity_status = "Unknown"

def clean_value(val):
    if val is None:
        return None
    if isinstance(val, str):
        v = val.strip()
        if v.lower() in NULL_EQUIVALENTS:
            return None
        return v
    return val

def map_row(row):
    mapped = {}
    for k, v in row.items():
        if k is None: continue
        k_clean = k.strip().lower()
        if k_clean in COLUMN_ALIASES:
            mapped[COLUMN_ALIASES[k_clean]] = clean_value(v)
        else:
            mapped[k_clean] = clean_value(v)
    return mapped

def safe_cast(val, col_name):
    if val is None:
        return None, None
    if col_name not in NUMERICAL_COLUMNS:
        return val, None
    
    target_type = NUMERICAL_COLUMNS[col_name]
    
    if isinstance(val, str):
        val = re.sub(r'[^\d\.\-]', '', val)
        if val == "" or val == "-" or val == ".":
            return None, f"Failed to extract numeric from string for {col_name}"

    try:
        if target_type == int:
            return int(float(val)), None
        else:
            return float(val), None
    except ValueError:
        return None, f"Cannot cast '{val}' to {target_type.__name__} for {col_name}"

def normalize_enum(val, enum_name):
    if val is None:
        return None, None
    val_lower = val.lower().replace(" ", "_")
    if val_lower in ENUM_ALLOWED_VALUES.get(enum_name, set()):
        return val_lower, None
    return None, f"Invalid enum value '{val}' for {enum_name}"

def split_casks(cask_str):
    if not cask_str: return []
    parts = re.split(r'[&,\/;]+', cask_str)
    return [p.strip() for p in parts if p.strip()]

def split_flavors(flavor_str):
    if not flavor_str: return []
    if flavor_str.startswith("[") and flavor_str.endswith("]"):
        try:
            arr = json.loads(flavor_str)
            if isinstance(arr, list):
                return [str(x).strip() for x in arr]
        except:
            pass
    parts = re.split(r'[&,\/;]+', flavor_str)
    return [p.strip() for p in parts if p.strip()]

def split_urls(urls_str):
    if not urls_str: return []
    parts = re.split(r'[\s,;|]+', urls_str)
    return [p.strip() for p in parts if p.strip()]

def ingest(input_dir, db_path, reset):
    if reset and os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if reset or not os.path.exists(db_path):
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema', 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                cursor.executescript(f.read())
        else:
            print(f"Error: Schema not found at {schema_path}")
            return
            
    report = IngestionReport()

    def get_or_create_country(name):
        if not name: return None
        cursor.execute("SELECT id FROM countries WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row: return row[0]
        cursor.execute("INSERT INTO countries (name) VALUES (?)", (name,))
        report.inserted_countries += 1
        return cursor.lastrowid

    def get_or_create_region(name, country_id):
        if not name: return None
        cursor.execute("SELECT id FROM regions WHERE name = ? AND country_id IS ?", (name, country_id))
        row = cursor.fetchone()
        if row: return row[0]
        cursor.execute("INSERT INTO regions (name, country_id) VALUES (?, ?)", (name, country_id))
        report.inserted_regions += 1
        return cursor.lastrowid
        
    def get_or_create_cask_type(name):
        if not name: return None
        cursor.execute("SELECT id FROM cask_types WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row: return row[0]
        cursor.execute("INSERT INTO cask_types (name) VALUES (?)", (name,))
        return cursor.lastrowid
        
    def get_or_create_flavor_tag(name):
        if not name: return None
        cursor.execute("SELECT id FROM flavor_tags WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row: return row[0]
        cursor.execute("INSERT INTO flavor_tags (name) VALUES (?)", (name,))
        return cursor.lastrowid

    def log_review_needed(entity_type, entity_name, field_name, current_val, reason, action, source_urls=None, confidence="low"):
        cursor.execute("""
            INSERT INTO review_needed (entity_type, entity_name, field_name, current_value, problem_reason, suggested_action, source_urls, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (entity_type, entity_name, field_name, str(current_val), reason, action, str(source_urls) if source_urls else None, confidence))
        report.etl_generated_review += 1

    # Load source audit
    audit_file = os.path.join(input_dir, 'source_audit.csv')
    audit_loaded = False
    if os.path.exists(audit_file):
        with open(audit_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                st, err = normalize_enum(row.get('source_type'), "source_type")
                if err:
                    log_review_needed("source_audit", row.get('source_title'), "source_type", row.get('source_type'), err, "Fix source_type enum")
                status, err2 = normalize_enum(row.get('status'), "audit_status")
                erc, err3 = safe_cast(row.get('extracted_records_count'), 'extracted_records_count')
                cursor.execute("""
                    INSERT INTO source_audit (source_title, source_type, domain, extraction_timestamp, extracted_records_count, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (row.get('source_title'), st, row.get('domain'), row.get('extraction_timestamp'), erc, status))
                audit_loaded = True
                
    # PRE-PROCESS products for missing independent bottlers and audit sources
    products_file = os.path.join(input_dir, 'whisky_products.csv')
    auto_bottlers = set()
    auto_datasets = set()
    
    if os.path.exists(products_file):
        with open(products_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = map_row(raw_row)
                bottler = row.get('bottler_name')
                
                # Default unknown types to 'independent' if they have a non-official bottler, otherwise let downstream decide
                b_type_raw = row.get('bottling_type')
                
                if bottler:
                    bot_lower = bottler.lower()
                    if bot_lower not in {"official", "ob", "null", "unknown", ""}:
                        if b_type_raw and b_type_raw.lower() != "official":
                            auto_bottlers.add(bottler)
                        elif not b_type_raw:
                            auto_bottlers.add(bottler)
                        
                # Check auto dataset
                ds = row.get('source_dataset')
                if ds:
                    auto_datasets.add(ds)

    # Insert auto datasets if audit wasn't loaded
    if not audit_loaded:
        if not auto_datasets:
            auto_datasets.add("Default Audit")
        for ds in auto_datasets:
            cursor.execute("""
                INSERT INTO source_audit (source_title, source_type, domain, extraction_timestamp, extracted_records_count, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ds, 'bulk', 'localhost', datetime.now().isoformat(), 0, 'success'))

    # Load distilleries
    distilleries_file = os.path.join(input_dir, 'distilleries.csv')
    if os.path.exists(distilleries_file):
        with open(distilleries_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                
                name = row.get('name') or row.get('distillery_name')
                if not name:
                    report.failed_rows += 1
                    continue
                
                country_id = get_or_create_country(row.get('country'))
                region_id = get_or_create_region(row.get('region'), country_id)
                
                cap, err1 = safe_cast(row.get('production_capacity_lpa'), 'production_capacity_lpa')
                if err1: log_review_needed("distillery", name, "production_capacity_lpa", row.get('production_capacity_lpa'), err1, "Fix numerical value")
                
                stills, err2 = safe_cast(row.get('number_of_stills'), 'number_of_stills')
                if err2: log_review_needed("distillery", name, "number_of_stills", row.get('number_of_stills'), err2, "Fix numerical value")
                
                status, err3 = normalize_enum(row.get('status'), "status")
                conf, err4 = normalize_enum(row.get('confidence_score'), "confidence_score")
                if conf == "low": report.low_confidence_count += 1
                
                orig_dist_id = row.get('original_distillery_id')
                
                try:
                    cursor.execute("""
                        INSERT INTO distilleries (original_distillery_id, name, country_id, region_id, status, production_capacity_lpa, number_of_stills, official_website, confidence_score, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (orig_dist_id, name, country_id, region_id, status, cap, stills, row.get('official_website'), conf, row.get('notes')))
                    report.inserted_distilleries += 1
                except sqlite3.IntegrityError:
                    log_review_needed("distillery", name, "name", name, "Duplicate distillery name or ID", "Merge or rename")

    # Insert auto derived bottlers
    for bot_name in auto_bottlers:
        cursor.execute("SELECT id FROM independent_bottlers WHERE name = ?", (bot_name,))
        if not cursor.fetchone():
            try:
                cursor.execute("""
                    INSERT INTO independent_bottlers (name, country_id, official_website, confidence_score, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (bot_name, None, None, "medium", "Auto-derived from whisky_products.bottler"))
                report.inserted_independent_bottlers += 1
            except sqlite3.IntegrityError:
                pass

    # Load independent bottlers (explicit file, if exists)
    bottlers_file = os.path.join(input_dir, 'independent_bottlers.csv')
    if os.path.exists(bottlers_file):
        with open(bottlers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                name = row.get('bottler_name')
                if not name:
                    report.failed_rows += 1
                    continue
                if name.lower() in {"official", "ob", "null", "unknown", ""}:
                    continue
                
                country_id = get_or_create_country(row.get('country'))
                conf, err = normalize_enum(row.get('confidence_score'), "confidence_score")
                if conf == "low": report.low_confidence_count += 1
                
                try:
                    cursor.execute("""
                        INSERT INTO independent_bottlers (name, country_id, official_website, confidence_score, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (name, country_id, row.get('official_website'), conf, row.get('notes')))
                    report.inserted_independent_bottlers += 1
                except sqlite3.IntegrityError:
                    pass

    # Load app filter tags into memory
    filter_tags_by_id = {}
    filter_tags_by_name = {}
    tags_file = os.path.join(input_dir, 'app_filter_tags.csv')
    if os.path.exists(tags_file):
        with open(tags_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                w_id = row.get('original_whisky_id')
                pname = row.get('name')
                
                if w_id:
                    filter_tags_by_id[w_id] = row
                if pname:
                    filter_tags_by_name[pname] = row

    # Load whisky products
    if os.path.exists(products_file):
        with open(products_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                
                pname = row.get('name')
                w_id = row.get('original_whisky_id')
                
                if not pname:
                    report.failed_rows += 1
                    continue
                
                # Enrich with app_filter_tags if present
                enrich_data = None
                if w_id and w_id in filter_tags_by_id:
                    enrich_data = filter_tags_by_id[w_id]
                elif pname in filter_tags_by_name:
                    enrich_data = filter_tags_by_name[pname]
                    
                if enrich_data:
                    for k, v in enrich_data.items():
                        if not row.get(k): row[k] = v

                # Map distillery
                dist_id_str = row.get('original_distillery_id')
                distillery_id = None
                
                if dist_id_str:
                    cursor.execute("SELECT id FROM distilleries WHERE original_distillery_id = ?", (dist_id_str,))
                    d_row = cursor.fetchone()
                    if d_row:
                        distillery_id = d_row[0]
                    else:
                        # Fallback to name search if dist_id_str doesn't match original_distillery_id
                        # But we don't have distillery_name!
                        pass
                
                if not distillery_id and row.get('bottler_name'):
                    cursor.execute("SELECT id FROM distilleries WHERE name = ? COLLATE NOCASE", (row.get('bottler_name'),))
                    d_row = cursor.fetchone()
                    if d_row:
                        distillery_id = d_row[0]
                        
                if not distillery_id:
                    cursor.execute("SELECT id, name FROM distilleries")
                    all_dists = cursor.fetchall()
                    all_dists.sort(key=lambda x: len(x[1]), reverse=True)
                    pname_lower = pname.lower()
                    for d_id, d_name in all_dists:
                        if pname_lower.startswith(d_name.lower()):
                            distillery_id = d_id
                            break
                            
                b_type = row.get('bottling_type') or ''
                if not distillery_id and b_type.lower() not in ['blended malt', 'blend']:
                    log_review_needed("whisky_product", pname, "distillery_id", dist_id_str, "Distillery not found by ID or heuristic", "Add distillery or correct ID")
                    report.skipped_products += 1
                    continue

                # Map bottler
                bottler_name = row.get('bottler_name')
                b_type_raw = row.get('bottling_type')
                
                if (b_type_raw and b_type_raw.lower() == 'official') or (bottler_name and bottler_name.lower() in {"official", "ob"}):
                    b_type = 'official'
                    bottler_id = None
                else:
                    if bottler_name and bottler_name.lower() not in {"null", "unknown", ""}:
                        b_type = 'independent'
                        cursor.execute("SELECT id FROM independent_bottlers WHERE name = ?", (bottler_name,))
                        b_row = cursor.fetchone()
                        if b_row:
                            bottler_id = b_row[0]
                        else:
                            log_review_needed("whisky_product", pname, "bottler_name", bottler_name, "Bottler not found", "Add bottler or correct name")
                            report.skipped_products += 1
                            continue
                    else:
                        # Fallback to official if no bottler provided, or flag as review?
                        # User said: "independent olup bottler_id eşleşmesini bu otomatik türetilmiş listeyle yap. Böylece independent gereksiz yere review_needed'a düşmesini azalt."
                        # If bottler name is empty, and b_type is independent...
                        if b_type_raw and b_type_raw.lower() == 'independent':
                            log_review_needed("whisky_product", pname, "bottler_name", None, "Independent product missing bottler", "Assign bottler")
                            report.skipped_products += 1
                            continue
                        else:
                            b_type = 'official'
                            bottler_id = None

                # Safecast numerics
                age, e_age = safe_cast(row.get('age_statement'), 'age_statement')
                if e_age: log_review_needed("whisky_product", pname, "age_statement", row.get('age_statement'), e_age, "Fix number")
                
                vintage, e_vin = safe_cast(row.get('vintage_year'), 'vintage_year')
                if e_vin: log_review_needed("whisky_product", pname, "vintage_year", row.get('vintage_year'), e_vin, "Fix number")
                
                bot_yr, e_by = safe_cast(row.get('bottling_year'), 'bottling_year')
                if e_by: log_review_needed("whisky_product", pname, "bottling_year", row.get('bottling_year'), e_by, "Fix number")
                
                rel_yr, e_ry = safe_cast(row.get('release_year'), 'release_year')
                if e_ry: log_review_needed("whisky_product", pname, "release_year", row.get('release_year'), e_ry, "Fix number")
                
                num_bot, e_nb = safe_cast(row.get('number_of_bottles'), 'number_of_bottles')
                if e_nb: log_review_needed("whisky_product", pname, "number_of_bottles", row.get('number_of_bottles'), e_nb, "Fix number")
                
                abv, e_abv = safe_cast(row.get('abv'), 'abv')
                if e_abv: log_review_needed("whisky_product", pname, "abv", row.get('abv'), e_abv, "Fix number")
                
                price, e_price = safe_cast(row.get('price_original'), 'price_original')
                if e_price: log_review_needed("whisky_product", pname, "price_original", row.get('price_original'), e_price, "Fix number")
                
                conf, err_c = normalize_enum(row.get('confidence_score'), "confidence_score")
                if conf == "low": report.low_confidence_count += 1
                
                # Check duplicate NULL safe
                cursor.execute("""
                    SELECT id FROM whisky_products 
                    WHERE name = ? 
                      AND distillery_id IS ?
                      AND bottler_id IS ?
                      AND bottling_type IS ?
                """, (pname, distillery_id, bottler_id, b_type))
                
                prod_row = cursor.fetchone()
                if prod_row:
                    product_id = prod_row[0]
                    report.duplicate_products_reused += 1
                else:
                    cursor.execute("""
                        INSERT INTO whisky_products (
                            original_whisky_id, name, distillery_id, bottler_id, bottling_type, age_statement, vintage_year, 
                            bottling_year, release_year, number_of_bottles, abv, price_original, price_currency, 
                            product_url, confidence_score, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        w_id, pname, distillery_id, bottler_id, b_type, age, vintage, bot_yr, rel_yr, 
                        num_bot, abv, price, row.get('price_currency'), row.get('product_url'), conf, row.get('notes')
                    ))
                    product_id = cursor.lastrowid
                    report.inserted_whisky_products += 1

                # Source URLs
                s_urls = split_urls(row.get('source_urls'))
                for url in s_urls:
                    cursor.execute("SELECT 1 FROM entity_sources WHERE entity_type=? AND entity_id=? AND source_url=?", ("whisky_product", product_id, url))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO entity_sources (entity_type, entity_id, source_url) VALUES (?, ?, ?)", ("whisky_product", product_id, url))
                        report.source_urls_inserted += 1

                # Cask types
                casks = split_casks(row.get('cask_type'))
                for c in casks:
                    cid = get_or_create_cask_type(c)
                    cursor.execute("SELECT 1 FROM product_cask_types WHERE product_id=? AND cask_type_id=?", (product_id, cid))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO product_cask_types (product_id, cask_type_id) VALUES (?, ?)", (product_id, cid))

                # Flavor tags
                flavors = split_flavors(row.get('flavor_profile_keywords'))
                flavors.extend(split_flavors(row.get('flavor_profile')))
                for f in set(flavors):
                    fid = get_or_create_flavor_tag(f)
                    cursor.execute("SELECT 1 FROM product_flavor_tags WHERE product_id=? AND flavor_tag_id=?", (product_id, fid))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO product_flavor_tags (product_id, flavor_tag_id) VALUES (?, ?)", (product_id, fid))

    # Load rejected matches
    rejected_file = os.path.join(input_dir, 'rejected_matches.csv')
    if os.path.exists(rejected_file):
        with open(rejected_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                pt, err = normalize_enum(row.get('problem_type'), "problem_type")
                cursor.execute("""
                    INSERT INTO rejected_matches (source_title, scraped_product_name, unmatched_field, source_value, database_value, match_attempt_date, problem_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row.get('source_title'), row.get('scraped_product_name'), row.get('unmatched_field'), row.get('source_value'), row.get('database_value'), row.get('match_attempt_date'), pt))
                report.rejected_matches_count += 1

    # Load review_needed
    review_file = os.path.join(input_dir, 'review_needed.csv')
    if os.path.exists(review_file):
        with open(review_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                report.total_rows_read += 1
                row = map_row(raw_row)
                conf, err = normalize_enum(row.get('confidence_score'), "confidence_score")
                cursor.execute("""
                    INSERT INTO review_needed (entity_type, entity_name, field_name, current_value, problem_reason, suggested_action, source_urls, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (row.get('entity_type'), row.get('entity_name'), row.get('field_name'), row.get('current_value'), row.get('problem_reason'), row.get('suggested_action'), row.get('source_urls'), conf))
                report.existing_review_imported += 1

    # Pragma foreign key check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_errors = cursor.fetchall()
    if fk_errors:
        report.database_integrity_status = f"Failed: {len(fk_errors)} FK violations"
        for err in fk_errors:
            log_review_needed("database", err[0], "foreign_key", err[1], "FK Violation", "Fix references")
    else:
        report.database_integrity_status = "Passed"

    conn.commit()
    conn.close()

    # Save report
    report_dict = report.__dict__
    report_path = os.path.join(os.path.dirname(db_path), 'quality_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=4)

    print(json.dumps(report_dict, indent=2))
    print(f"ETL Complete. DB: {db_path}, Report: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Whisky DB ETL')
    parser.add_argument('--input-dir', required=True, help='Directory containing CSVs')
    parser.add_argument('--db', required=True, help='Output DB path')
    parser.add_argument('--reset', action='store_true', help='Reset database')
    args = parser.parse_args()
    
    ingest(args.input_dir, args.db, args.reset)

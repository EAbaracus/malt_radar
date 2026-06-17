import os
import sqlite3
import pytest
import csv
import json
import sys

# Add etl to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from etl.ingest_whisky_database import ingest

@pytest.fixture(scope="module")
def setup_env(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("data")
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "whisky_prod.db"
    
    # 1. distilleries.csv
    with open(input_dir / "distilleries.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["distillery_name", "country", "region", "status", "production_capacity_lpa", "number_of_stills"])
        writer.writerow(["Macallan", "Scotland", "Speyside", "active", "15000000", "36"])
        writer.writerow(["Ardbeg", "Scotland", "Islay", "active", "unknown", "unknown"]) # Testing "unknown" -> null
        writer.writerow(["MissingDistillery", "", "", "", "", ""])

    # 2. independent_bottlers.csv
    with open(input_dir / "independent_bottlers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bottler_name", "country"])
        writer.writerow(["Gordon & MacPhail", "Scotland"])
        writer.writerow(["Official", ""]) # Should be ignored

    # 3. whisky_products.csv
    with open(input_dir / "whisky_products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_name", "distillery_name", "bottler_name", "bottling_type", "age", "cask_type", "source_urls", "flavor_profile"])
        
        # Test 1: Official product (bottler_name is ignored/nullified)
        writer.writerow(["Macallan 12", "Macallan", "Official", "official", "12", "Sherry, Oak", "http://macallan.com | http://whisky.com", "Fruity; Spicy"])
        
        # Test 2: Independent product (must have bottler)
        writer.writerow(["Macallan 15 G&M", "Macallan", "Gordon & MacPhail", "independent", "15", "Bourbon", "http://gm.com", "Vanilla, Oak"])
        
        # Test 3: Independent product missing bottler (should go to review_needed)
        writer.writerow(["Ardbeg Unknown", "Ardbeg", "", "independent", "unknown", "Refill", "", "Smoke"])
        
        # Test 4: Product missing distillery (should go to review_needed)
        writer.writerow(["Ghost Product", "GhostDistillery", "Official", "official", "10", "", "", ""])
        
        # Test 5: Duplicate official product
        writer.writerow(["Macallan 12", "Macallan", "", "official", "12", "Sherry", "", ""])

    # Run the ETL script once for all tests in this module
    ingest(str(input_dir), str(db_path), reset=True)
    
    conn = sqlite3.connect(str(db_path))
    yield conn, db_path
    conn.close()

def test_official_bottler_not_inserted(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM independent_bottlers WHERE name = 'Official'")
    assert cursor.fetchone()[0] == 0

def test_official_product_has_null_bottler_id(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT bottler_id FROM whisky_products WHERE name = 'Macallan 12'")
    assert cursor.fetchone()[0] is None

def test_independent_product_requires_bottler(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM whisky_products WHERE bottling_type = 'independent' AND bottler_id IS NULL")
    assert cursor.fetchone()[0] == 0

def test_unknown_values_become_null(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT production_capacity_lpa, number_of_stills FROM distilleries WHERE name = 'Ardbeg'")
    row = cursor.fetchone()
    assert row[0] is None
    assert row[1] is None

def test_source_urls_split_into_multiple_rows(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM whisky_products WHERE name = 'Macallan 12'")
    prod_id = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM entity_sources WHERE entity_type='whisky_product' AND entity_id=?", (prod_id,))
    assert cursor.fetchone()[0] == 2

def test_duplicate_product_reuses_existing_id(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM whisky_products WHERE name = 'Macallan 12'")
    assert cursor.fetchone()[0] == 1

def test_cask_type_many_to_many_insert(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM whisky_products WHERE name = 'Macallan 12'")
    prod_id = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM product_cask_types WHERE product_id=?", (prod_id,))
    assert cursor.fetchone()[0] == 2 # 'Sherry', 'Oak'

def test_flavor_tags_many_to_many_insert(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM whisky_products WHERE name = 'Macallan 12'")
    prod_id = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM product_flavor_tags WHERE product_id=?", (prod_id,))
    assert cursor.fetchone()[0] == 2 # 'Fruity', 'Spicy'

def test_missing_distillery_goes_to_review_needed(setup_env):
    conn, db_path = setup_env
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM review_needed WHERE entity_name = 'Ghost Product' AND field_name = 'distillery_id'")
    assert cursor.fetchone()[0] == 1
    
    # Additional test for missing bottler going to review_needed
    cursor.execute("SELECT count(*) FROM review_needed WHERE entity_name = 'Ardbeg Unknown' AND field_name = 'bottler_name'")
    assert cursor.fetchone()[0] == 1

def test_foreign_key_check_passes(setup_env):
    conn, db_path = setup_env
    report_path = os.path.join(os.path.dirname(db_path), 'quality_report.json')
    assert os.path.exists(report_path), f"Quality report missing at {report_path}"
    with open(report_path, 'r') as f:
        report = json.load(f)
        assert report['database_integrity_status'] == 'Passed'
        assert report['skipped_products'] == 2 # Ardbeg Unknown, Ghost Product
        assert report['duplicate_products_reused'] == 1 # Macallan 12 dup

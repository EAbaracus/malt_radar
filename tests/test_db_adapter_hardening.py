import os
import sqlite3
import pytest
import sys
from fastapi.testclient import TestClient

# Add backend to path so imports work
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

from app.main import app
from app.providers.sqlite_read_adapter import SqliteReadAdapter

client = TestClient(app)

# A) DB resolver tests
def test_db_resolver_default_path():
    # Ensure env var is unset
    if "MALT_RADAR_DB_PATH" in os.environ:
        del os.environ["MALT_RADAR_DB_PATH"]
    
    adapter = SqliteReadAdapter()
    assert adapter.db_path_source == "default"
    assert "production.db" in adapter.db_path

def test_db_resolver_env_path():
    os.environ["MALT_RADAR_DB_PATH"] = "some_custom_path.db"
    adapter = SqliteReadAdapter()
    assert adapter.db_path_source == "env"
    assert adapter.db_path.endswith("some_custom_path.db")
    del os.environ["MALT_RADAR_DB_PATH"]

def test_db_resolver_invalid_path():
    os.environ["MALT_RADAR_DB_PATH"] = "invalid_nonexistent.db"
    adapter = SqliteReadAdapter()
    health = adapter.get_health()
    assert health["status"] == "error"
    assert health["db_exists"] is False
    del os.environ["MALT_RADAR_DB_PATH"]

# B) Read-only enforcement tests
def test_read_only_enforcement():
    adapter = SqliteReadAdapter()
    # It should connect to default production.db
    conn = adapter._get_connection()
    cursor = conn.cursor()
    # Try an insert on a canonical table (it should fail due to read-only DB)
    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cursor.execute("CREATE TABLE read_only_test (id INT)")
    assert "attempt to write a readonly database" in str(exc_info.value).lower()
    
    with pytest.raises(sqlite3.OperationalError) as exc_info2:
        cursor.execute("INSERT INTO whiskies (whisky_id) VALUES ('123')")
    assert "attempt to write a readonly database" in str(exc_info2.value).lower()
    conn.close()

# C) Endpoint contract tests
def test_health_contract():
    r = client.get("/api/db/health")
    assert r.status_code == 200
    data = r.json()
    assert "db_path" in data
    assert data["read_only"] is True

def test_schema_contract():
    r = client.get("/api/db/schema")
    assert r.status_code == 200
    data = r.json()
    assert data["expected_canonical_table_check"] is True

def test_whiskies_pagination_contract():
    r = client.get("/api/db/whiskies")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) <= 50 # default limit
    
    r2 = client.get("/api/db/whiskies?limit=150")
    assert r2.status_code == 200
    assert len(r2.json()["items"]) <= 100 # clamp to 100
    
    r3 = client.get("/api/db/whiskies?limit=5&offset=2")
    assert r3.status_code == 200
    assert len(r3.json()["items"]) <= 5

def test_whiskies_search_contract():
    # parameterized query check (we can't easily see it's parameterized from the outside, 
    # but we can test SQL injection characters)
    r = client.get("/api/db/whiskies?q=' OR 1=1 --")
    assert r.status_code == 200
    # Should not return all whiskies (it returns nothing or whiskies matching the literal string)
    assert len(r.json()["items"]) < 100

def test_whiskies_detail_contract():
    # Get a valid id
    r = client.get("/api/db/whiskies?limit=1")
    items = r.json().get("items", [])
    if len(items) > 0:
        w_id = items[0]["whisky_id"]
        r2 = client.get(f"/api/db/whiskies/{w_id}")
        assert r2.status_code == 200
        assert r2.json()["whisky_id"] == w_id

    # Invalid ID
    r3 = client.get("/api/db/whiskies/invalid_9999_xyz")
    assert r3.status_code == 404

def test_distilleries_contract():
    r = client.get("/api/db/distilleries")
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) <= 50
    
    if len(items) > 0:
        d_id = items[0]["distillery_id"]
        r2 = client.get(f"/api/db/distilleries/{d_id}")
        assert r2.status_code == 200

def test_related_endpoints_empty_behavior():
    w_id = "invalid_nonexistent_id"
    r = client.get(f"/api/db/whiskies/{w_id}/flavor-profile")
    assert r.status_code == 404 # Empty behavior for FP is 404
    
    r2 = client.get(f"/api/db/whiskies/{w_id}/tasting-notes")
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)
    assert len(r2.json()) == 0 # Empty behavior is []
    
    r3 = client.get(f"/api/db/whiskies/{w_id}/price-history")
    assert r3.status_code == 200
    assert isinstance(r3.json(), list)
    assert len(r3.json()) == 0

# D) Legacy regression tests
def test_legacy_regression():
    r = client.get("/api/whiskies/search?q=glen")
    assert r.status_code == 200
    # Should return List[WhiskySearchItem]
    data = r.json()
    if len(data) > 0:
        assert "name" in data[0]
        assert "external_id" in data[0]

# E) Schema compatibility tests
def test_schema_compatibility():
    adapter = SqliteReadAdapter()
    schema_info = adapter.get_schema()
    for table in adapter.canonical_tables:
        assert table in schema_info["tables"]

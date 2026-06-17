import os
import sqlite3
import pytest
import sys
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

os.environ["DB_API_ENABLED"] = "true"

from app.main import app
from app.services.db_read_service import DbReadService

client = TestClient(app)

def test_db_resolver_default_path():
    if "MALT_RADAR_DB_PATH" in os.environ:
        del os.environ["MALT_RADAR_DB_PATH"]
    service = DbReadService()
    assert "production.db" in service.db_path

def test_db_resolver_env_path():
    os.environ["MALT_RADAR_DB_PATH"] = "some_custom_path.db"
    service = DbReadService()
    assert service.db_path.endswith("some_custom_path.db")
    del os.environ["MALT_RADAR_DB_PATH"]

def test_db_resolver_invalid_path():
    os.environ["MALT_RADAR_DB_PATH"] = "invalid_nonexistent.db"
    service = DbReadService()
    health = service.get_health()
    assert health["db_reachable"] is False
    del os.environ["MALT_RADAR_DB_PATH"]

def test_read_only_enforcement():
    service = DbReadService()
    conn = service._get_connection()
    cursor = conn.cursor()
    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cursor.execute("CREATE TABLE read_only_test (id INT)")
    assert "attempt to write a readonly database" in str(exc_info.value).lower()
    
    with pytest.raises(sqlite3.OperationalError) as exc_info2:
        cursor.execute("INSERT INTO whiskies (whisky_id) VALUES ('123')")
    assert "attempt to write a readonly database" in str(exc_info2.value).lower()
    conn.close()

def test_health_contract():
    r = client.get("/api/db/health")
    assert r.status_code == 200
    data = r.json()
    assert "counts" in data
    assert data["read_only"] is True

def test_schema_contract():
    r = client.get("/api/db/health")
    assert r.status_code == 200
    data = r.json()
    assert "whiskies" in data["counts"]
    assert "distilleries" in data["counts"]

def test_whiskies_pagination_contract():
    r = client.get("/api/db/whiskies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 50
    
    r2 = client.get("/api/db/whiskies?limit=150")
    assert r2.status_code == 200
    assert len(r2.json()) <= 100
    
    r3 = client.get("/api/db/whiskies?limit=5&offset=2")
    assert r3.status_code == 200
    assert len(r3.json()) <= 5

def test_whiskies_search_contract():
    r = client.get("/api/db/search?q=' OR 1=1 --")
    assert r.status_code == 200
    assert len(r.json()) < 100

def test_whiskies_detail_contract():
    r = client.get("/api/db/whiskies?limit=1")
    items = r.json()
    if len(items) > 0:
        w_id = items[0]["whisky_id"]
        r2 = client.get(f"/api/db/whiskies/{w_id}")
        assert r2.status_code == 200
        assert r2.json()["whisky_id"] == w_id

    r3 = client.get("/api/db/whiskies/invalid_9999_xyz")
    assert r3.status_code == 404

def test_distilleries_contract():
    r = client.get("/api/db/distilleries")
    assert r.status_code == 200
    items = r.json()
    assert len(items) <= 50

def test_related_endpoints_empty_behavior():
    w_id = "invalid_nonexistent_id"
    r = client.get(f"/api/db/whiskies/{w_id}/flavor-profile")
    assert r.status_code == 404
    
    r2 = client.get(f"/api/db/whiskies/{w_id}/tasting-notes")
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)
    assert len(r2.json()) == 0
    
    r3 = client.get(f"/api/db/whiskies/{w_id}/price-history")
    assert r3.status_code == 200
    assert isinstance(r3.json(), list)
    assert len(r3.json()) == 0

def test_legacy_regression():
    r = client.get("/api/whiskies/search?q=glen")
    assert r.status_code == 200
    data = r.json()
    if len(data) > 0:
        assert "name" in data[0]
        assert "external_id" in data[0]

def test_schema_compatibility():
    service = DbReadService()
    health = service.get_health()
    counts = health.get("counts", {})
    assert "whiskies" in counts
    assert "distilleries" in counts

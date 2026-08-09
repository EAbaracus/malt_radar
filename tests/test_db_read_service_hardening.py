import os
import sqlite3
import pytest
import sys
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

# API key + feature flags are configured by tests/conftest.py.
from app.main import app
from app.services.db_read_service import DbReadService

client = TestClient(app)
# db_api is per-user bearer-authenticated (no shared X-API-Key). Module-scope
# autouse fixture registers a throwaway user and rewrites DB_HEADERS to carry
# its bearer token, so existing `headers=DB_HEADERS` call sites stay valid.
DB_HEADERS: dict = {}


@pytest.fixture(scope="module", autouse=True)
def _bearer_for_db_tests(tmp_path_factory):
    # (No monkeypatch: function-scoped. Manage os.environ manually.)
    _old_db = os.environ.get("MALT_RADAR_USERS_DB_PATH")
    os.environ["MALT_RADAR_USERS_DB_PATH"] = str(
        tmp_path_factory.mktemp("users") / "users.db"
    )
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = False
    r = client.post(
        "/api/auth/register",
        json={
            "email": "svcharden@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    )
    assert r.status_code == 201, r.text
    DB_HEADERS.clear()
    DB_HEADERS["Authorization"] = f"Bearer {r.json()['token']}"
    yield
    DB_HEADERS.clear()
    if _old_db is None:
        os.environ.pop("MALT_RADAR_USERS_DB_PATH", None)
    else:
        os.environ["MALT_RADAR_USERS_DB_PATH"] = _old_db
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = True

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
    r = client.get("/api/db/health", headers=DB_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "counts" in data
    assert data["read_only"] is True

def test_schema_contract():
    r = client.get("/api/db/health", headers=DB_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "whiskies" in data["counts"]
    assert "distilleries" in data["counts"]

def test_whiskies_pagination_contract():
    r = client.get("/api/db/whiskies", headers=DB_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 50
    
    r2 = client.get("/api/db/whiskies?limit=150", headers=DB_HEADERS)
    assert r2.status_code == 422
    
    r3 = client.get("/api/db/whiskies?limit=5&offset=2", headers=DB_HEADERS)
    assert r3.status_code == 200
    assert len(r3.json()["items"]) <= 5

def test_whiskies_search_contract():
    r = client.get("/api/db/search?q=' OR 1=1 --", headers=DB_HEADERS)
    assert r.status_code == 200
    assert len(r.json()) < 100

def test_whiskies_detail_contract():
    r = client.get("/api/db/whiskies?limit=1", headers=DB_HEADERS)
    payload = r.json()
    items = payload["items"] if isinstance(payload, dict) else payload
    if len(items) > 0:
        w_id = items[0]["whisky_id"]
        r2 = client.get(f"/api/db/whiskies/{w_id}", headers=DB_HEADERS)
        assert r2.status_code == 200
        assert r2.json()["whisky_id"] == w_id
    
    r3 = client.get("/api/db/whiskies/invalid_9999_xyz", headers=DB_HEADERS)
    assert r3.status_code == 404

def test_distilleries_contract():
    r = client.get("/api/db/distilleries", headers=DB_HEADERS)
    assert r.status_code == 200
    payload = r.json()
    items = payload["items"] if isinstance(payload, dict) else payload
    assert len(items) <= 50

def test_related_endpoints_empty_behavior():
    w_id = "invalid_nonexistent_id"
    r = client.get(f"/api/db/whiskies/{w_id}/flavor-profile", headers=DB_HEADERS)
    assert r.status_code == 404
    
    r2 = client.get(f"/api/db/whiskies/{w_id}/tasting-notes", headers=DB_HEADERS)
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)
    assert len(r2.json()) == 0
    
    r3 = client.get(f"/api/db/whiskies/{w_id}/price-history", headers=DB_HEADERS)
    assert r3.status_code == 200
    assert isinstance(r3.json(), list)
    assert len(r3.json()) == 0

def test_legacy_regression(monkeypatch):
    import app.security
    monkeypatch.setattr(app.security, "API_KEY", "testkey")
    r = client.get("/api/whiskies/search?q=glen", headers={"X-API-Key": "testkey"})
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

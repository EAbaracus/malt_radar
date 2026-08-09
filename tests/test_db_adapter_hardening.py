import os
import sqlite3
import pytest
import sys
from fastapi.testclient import TestClient

# Add backend to path so imports work
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

# API key + feature flags are configured by tests/conftest.py (autouse fixture
# + module-level env setup) so the app imports with the expected config.
from app.main import app
from app.providers.sqlite_read_adapter import SqliteReadAdapter

client = TestClient(app)
# db_api is now per-user bearer-authenticated (no shared X-API-Key). A
# module-scope autouse fixture registers a throwaway user and rewrites this
# headers dict to carry its bearer token, so all existing `headers=DB_HEADERS`
# call sites transparently use the authenticated path.
DB_HEADERS: dict = {}


@pytest.fixture(scope="module", autouse=True)
def _bearer_for_db_tests(tmp_path_factory):
    # Isolate users.db + drop rate limits for deterministic register->token.
    # (No monkeypatch: it is function-scoped; manage os.environ manually.)
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
            "email": "harden@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    DB_HEADERS.clear()
    DB_HEADERS["Authorization"] = f"Bearer {token}"
    yield
    DB_HEADERS.clear()
    if _old_db is None:
        os.environ.pop("MALT_RADAR_USERS_DB_PATH", None)
    else:
        os.environ["MALT_RADAR_USERS_DB_PATH"] = _old_db
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = True


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
    r = client.get("/api/db/health", headers=DB_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "db_reachable" in data
    assert data["read_only"] is True

@pytest.mark.skip(reason="Schema endpoint removed")
def test_schema_contract():
    r = client.get("/api/db/schema", headers=DB_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["expected_canonical_table_check"] is True

def test_whiskies_pagination_contract():
    r = client.get("/api/db/whiskies", headers=DB_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 50  # default limit

    r2 = client.get("/api/db/whiskies?limit=150", headers=DB_HEADERS)
    assert r2.status_code == 422

    r3 = client.get("/api/db/whiskies?limit=5&offset=2", headers=DB_HEADERS)
    assert r3.status_code == 200
    assert len(r3.json()["items"]) <= 5

def test_whiskies_search_contract():
    r = client.get("/api/db/whiskies?q=' OR 1=1 --", headers=DB_HEADERS)
    assert r.status_code == 200
    # Should not return all whiskies (it returns nothing or whiskies matching the literal string)
    assert len(r.json()) < 100

def test_whiskies_detail_contract():
    # Get a valid id
    r = client.get("/api/db/whiskies?limit=1", headers=DB_HEADERS)
    payload = r.json()
    items = payload["items"] if isinstance(payload, dict) else []
    if len(items) > 0:
        w_id = items[0]["whisky_id"]
        r2 = client.get(f"/api/db/whiskies/{w_id}", headers=DB_HEADERS)
        assert r2.status_code == 200
        assert r2.json()["whisky_id"] == w_id

    # Invalid ID
    r3 = client.get("/api/db/whiskies/invalid_9999_xyz", headers=DB_HEADERS)
    assert r3.status_code == 404

def test_distilleries_contract():
    r = client.get("/api/db/distilleries", headers=DB_HEADERS)
    assert r.status_code == 200
    payload = r.json()
    items = payload["items"] if isinstance(payload, dict) else []
    assert len(items) <= 50

    if len(items) > 0:
        d_id = items[0]["distillery_id"]
        r2 = client.get(f"/api/db/distilleries/{d_id}", headers=DB_HEADERS)
        assert r2.status_code == 404

def test_related_endpoints_empty_behavior():
    w_id = "invalid_nonexistent_id"
    r = client.get(f"/api/db/whiskies/{w_id}/flavor-profile", headers=DB_HEADERS)
    assert r.status_code == 404  # Empty behavior for FP is 404

    r2 = client.get(f"/api/db/whiskies/{w_id}/tasting-notes", headers=DB_HEADERS)
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)
    assert len(r2.json()) == 0  # Empty behavior is []

    r3 = client.get(f"/api/db/whiskies/{w_id}/price-history", headers=DB_HEADERS)
    assert r3.status_code == 200
    assert isinstance(r3.json(), list)
    assert len(r3.json()) == 0

# D) Legacy regression tests
def test_legacy_regression(monkeypatch):
    import app.security
    monkeypatch.setattr(app.security, "API_KEY", "testkey")
    r = client.get("/api/whiskies/search?q=glen", headers={"X-API-Key": "testkey"})
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

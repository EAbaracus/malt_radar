import os
import sys
import pytest
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

# Catalog reads are per-user bearer-authenticated. /api/auth endpoints stay
# anonymous where required. We register a user to obtain a bearer token.
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_users_db_and_limiter(tmp_path, monkeypatch):
    """Isolate users.db and disable the global rate limiter so register->token
    flows are deterministic across many same-IP testclient calls."""
    monkeypatch.setenv("MALT_RADAR_USERS_DB_PATH", str(tmp_path / "users.db"))
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = False
    yield
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = True


def _register_and_token():
    """Create a throwaway user and return their bearer token."""
    r = client.post(
        "/api/auth/register",
        json={
            "email": "smoke@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["token"]


def _bearer(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_health_check_passes():
    tok = _register_and_token()
    response = client.get("/api/db/health", headers=_bearer(tok))
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "read_only" in data
    assert data["read_only"] is True

def test_get_whiskies_with_limit():
    tok = _register_and_token()
    response = client.get("/api/db/whiskies?limit=10", headers=_bearer(tok))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 10

def test_get_distilleries():
    tok = _register_and_token()
    response = client.get("/api/db/distilleries?limit=5", headers=_bearer(tok))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 5

def test_search_lagavulin():
    tok = _register_and_token()
    response = client.get("/api/db/search?q=lagavulin", headers=_bearer(tok))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_disabled_flag():
    os.environ["DB_API_ENABLED"] = "false"
    try:
        tok = _register_and_token()
        response = client.get("/api/db/health", headers=_bearer(tok))
        assert response.status_code in [403, 404]
    finally:
        os.environ["DB_API_ENABLED"] = "true"

def test_unauthenticated_rejected():
    # No bearer token (and no API key) -> 401, never served.
    assert client.get("/api/db/health").status_code == 401

def test_legacy_api_key_rejected():
    # The old X-API-Key shared-key channel must NOT work anymore.
    tok = _register_and_token()
    ok = client.get("/api/db/health", headers=_bearer(tok))
    assert ok.status_code == 200
    assert client.get("/api/db/health", headers={"X-API-Key": "test-api-key"}).status_code in [401, 403]

def test_invalid_bearer_rejected():
    # A malformed/unknown bearer token must be rejected (401), not served.
    assert client.get("/api/db/health", headers=_bearer("definitely-not-a-real-token")).status_code == 401

def test_all_read_endpoints_authenticated():
    # A valid logged-in user can hit every /api/db read endpoint with bearer.
    tok = _register_and_token()
    for path in [
        "/api/db/health",
        "/api/db/whiskies?limit=5",
        "/api/db/distilleries?limit=5",
        "/api/db/search?q=lagavulin",
    ]:
        assert client.get(path, headers=_bearer(tok)).status_code == 200, f"{path} -> not 200"

"""Test DB API auth behavior: catalog endpoints gated by per-user bearer auth.

Per deploy/README.md: "/api/db is now gated by per-user bearer auth
(get_current_user) — not a shared key". Catalog reads require a valid bearer
token; sync endpoints require auth too. This restores the pre-e71527e
security model (68bb9b4+).
"""
import pytest
import os
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(autouse=True)
def enable_db_api():
    """Enable DB API for all tests in this module."""
    old_val = os.environ.get("DB_API_ENABLED")
    os.environ["DB_API_ENABLED"] = "true"
    yield
    if old_val is None:
        os.environ.pop("DB_API_ENABLED", None)
    else:
        os.environ["DB_API_ENABLED"] = old_val


@pytest.fixture(autouse=True)
def disable_rate_limit():
    """Disable slowapi limits so many same-IP calls in one suite don't 429."""
    from app.main import app
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Return valid auth headers for testing authenticated endpoints."""
    client = TestClient(app)
    email = "test_db_api_auth@example.com"
    password = "TestPassword123!"

    # Register (or re-register after prior cleanup)
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "Test User",
        "age_country": "TR",
        "age_min": 18,
        "privacy_consent": True
    })
    if reg.status_code == 201:
        token = reg.json()["token"]
    else:
        # User exists already — login instead
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        token = login.json()["token"]

    yield {"Authorization": f"Bearer {token}"}


CATALOG_PATHS = [
    "/api/db/whiskies?limit=5",
    "/api/db/distilleries?limit=5",
    "/api/db/filters",
    "/api/db/search?q=macallan",
]


class TestCatalogEndpointsAuthRequired:
    """Catalog GET endpoints REQUIRE auth (per-user bearer gating)."""

    @pytest.mark.parametrize("path", CATALOG_PATHS)
    def test_catalog_unauthenticated_returns_401(self, client, path):
        response = client.get(path)
        assert response.status_code == 401

    def test_whiskies_list_unauthenticated_401(self, client):
        response = client.get("/api/db/whiskies?limit=5")
        assert response.status_code == 401

    def test_whisky_detail_unauthenticated_401(self, client, auth_headers):
        # Get a valid id WITH auth first, then hit without auth
        list_resp = client.get("/api/db/whiskies?limit=1", headers=auth_headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        whisky_id = items[0]["whisky_id"]
        response = client.get(f"/api/db/whiskies/{whisky_id}")
        assert response.status_code == 401

    def test_flavor_profile_unauthenticated_401(self, client, auth_headers):
        list_resp = client.get("/api/db/whiskies?limit=1", headers=auth_headers)
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        response = client.get(f"/api/db/whiskies/{items[0]['whisky_id']}/flavor-profile")
        assert response.status_code == 401

    def test_tasting_notes_unauthenticated_401(self, client, auth_headers):
        list_resp = client.get("/api/db/whiskies?limit=1", headers=auth_headers)
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        response = client.get(f"/api/db/whiskies/{items[0]['whisky_id']}/tasting-notes")
        assert response.status_code == 401

    def test_evidence_unauthenticated_401(self, client, auth_headers):
        list_resp = client.get("/api/db/whiskies?limit=1", headers=auth_headers)
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        response = client.get(f"/api/db/whiskies/{items[0]['whisky_id']}/evidence")
        assert response.status_code == 401


class TestCatalogEndpointsAuthenticated:
    """Catalog GET endpoints succeed with a valid bearer token."""

    def test_whiskies_list_authenticated(self, client, auth_headers):
        response = client.get("/api/db/whiskies?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_search_authenticated(self, client, auth_headers):
        response = client.get("/api/db/search?q=macallan", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_distilleries_authenticated(self, client, auth_headers):
        response = client.get("/api/db/distilleries?limit=5", headers=auth_headers)
        assert response.status_code == 200
        assert "items" in response.json() or "distilleries" in response.json()

    def test_filters_authenticated(self, client, auth_headers):
        response = client.get("/api/db/filters", headers=auth_headers)
        assert response.status_code == 200


class TestSyncEndpointsAuthRequired:
    """Sync endpoints must require authentication."""

    def test_sync_push_unauthenticated_returns_401(self, client):
        response = client.post("/api/auth/sync/push", json={"data": {}})
        assert response.status_code == 401

    def test_sync_pull_unauthenticated_returns_401(self, client):
        response = client.get("/api/auth/sync/pull")
        assert response.status_code == 401

    def test_sync_push_authenticated_succeeds(self, client, auth_headers):
        response = client.post(
            "/api/auth/sync/push",
            json={"data": {"test": "value"}},
            headers=auth_headers
        )
        assert response.status_code != 401
        assert response.status_code in [200, 201, 204]

    def test_sync_pull_authenticated_succeeds(self, client, auth_headers):
        response = client.get("/api/auth/sync/pull", headers=auth_headers)
        assert response.status_code != 401
        assert response.status_code == 200

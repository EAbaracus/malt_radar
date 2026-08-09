"""Test DB API auth behavior: catalog endpoints public, sync endpoints auth-required."""
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


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Return valid auth headers for testing authenticated endpoints."""
    # Register a test user and get token
    client = TestClient(app)
    email = "test_db_api_auth@example.com"
    password = "TestPassword123!"
    
    # Clean up any existing user
    client.request("DELETE", "/api/auth/me", headers={"Authorization": f"Bearer {_get_token(client, email, password)}"})
    
    # Register
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "Test User",
        "age_country": "TR",
        "age_min": 18,
        "privacy_consent": True
    })
    assert reg.status_code == 201
    token = reg.json()["token"]
    
    yield {"Authorization": f"Bearer {token}"}
    
    # Cleanup
    client.request("DELETE", "/api/auth/me", headers={"Authorization": f"Bearer {token}"})


def _get_token(client, email, password):
    """Helper to get auth token."""
    # Try login first
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    if login.status_code == 200:
        return login.json()["token"]
    # If login fails, user doesn't exist yet
    return None


class TestCatalogEndpointsPublic:
    """Catalog GET endpoints should be accessible without auth."""
    
    def test_whiskies_list_unauthenticated(self, client):
        """GET /api/db/whiskies should return 200 without auth."""
        response = client.get("/api/db/whiskies?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_whisky_detail_unauthenticated(self, client):
        """GET /api/db/whiskies/{id} should return 200 without auth."""
        # First get a valid whisky ID
        list_resp = client.get("/api/db/whiskies?limit=1")
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        
        whisky_id = items[0]["whisky_id"]
        response = client.get(f"/api/db/whiskies/{whisky_id}")
        assert response.status_code == 200
        assert response.json()["whisky_id"] == whisky_id
    
    def test_search_unauthenticated(self, client):
        """GET /api/db/search should return 200 without auth."""
        response = client.get("/api/db/search?q=macallan")
        assert response.status_code == 200
        data = response.json()
        # Search returns a list directly
        assert isinstance(data, list)
    
    def test_distilleries_unauthenticated(self, client):
        """GET /api/db/distilleries should return 200 without auth."""
        response = client.get("/api/db/distilleries?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "distilleries" in data
    
    def test_filters_unauthenticated(self, client):
        """GET /api/db/filters should return 200 without auth."""
        response = client.get("/api/db/filters")
        assert response.status_code == 200
    
    def test_flavor_profile_unauthenticated(self, client):
        """GET /api/db/whiskies/{id}/flavor-profile should return 200 without auth."""
        list_resp = client.get("/api/db/whiskies?limit=1")
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        
        whisky_id = items[0]["whisky_id"]
        response = client.get(f"/api/db/whiskies/{whisky_id}/flavor-profile")
        # May return 404 if no flavor profile, but should not return 401
        assert response.status_code in [200, 404]
    
    def test_tasting_notes_unauthenticated(self, client):
        """GET /api/db/whiskies/{id}/tasting-notes should return 200 without auth."""
        list_resp = client.get("/api/db/whiskies?limit=1")
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        
        whisky_id = items[0]["whisky_id"]
        response = client.get(f"/api/db/whiskies/{whisky_id}/tasting-notes")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_evidence_unauthenticated(self, client):
        """GET /api/db/whiskies/{id}/evidence should return 200 without auth."""
        list_resp = client.get("/api/db/whiskies?limit=1")
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        if not items:
            pytest.skip("No whiskies in database")
        
        whisky_id = items[0]["whisky_id"]
        response = client.get(f"/api/db/whiskies/{whisky_id}/evidence")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestSyncEndpointsAuthRequired:
    """Sync endpoints must require authentication."""
    
    def test_sync_push_unauthenticated_returns_401(self, client):
        """POST /api/auth/sync/push should return 401 without auth."""
        response = client.post("/api/auth/sync/push", json={"data": {}})
        assert response.status_code == 401
    
    def test_sync_pull_unauthenticated_returns_401(self, client):
        """GET /api/auth/sync/pull should return 401 without auth."""
        response = client.get("/api/auth/sync/pull")
        assert response.status_code == 401
    
    def test_sync_push_authenticated_succeeds(self, client, auth_headers):
        """POST /api/auth/sync/push should succeed with valid auth."""
        response = client.post(
            "/api/auth/sync/push",
            json={"data": {"test": "value"}},
            headers=auth_headers
        )
        # Should not return 401
        assert response.status_code != 401
        # May return 200 or 201 depending on implementation
        assert response.status_code in [200, 201, 204]
    
    def test_sync_pull_authenticated_succeeds(self, client, auth_headers):
        """GET /api/auth/sync/pull should succeed with valid auth."""
        response = client.get("/api/auth/sync/pull", headers=auth_headers)
        # Should not return 401
        assert response.status_code != 401
        # Should return 200
        assert response.status_code == 200

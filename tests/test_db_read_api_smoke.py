import os
import sys
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

# API key + feature flags are configured by tests/conftest.py (autouse fixture
# + module-level env setup) so the app imports with the expected config.
from app.main import app

client = TestClient(app)
# Matches tests/conftest.TEST_API_KEY
DB_HEADERS = {"X-API-Key": "test-api-key"}


def test_health_check_passes():
    response = client.get("/api/db/health", headers=DB_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "read_only" in data
    assert data["read_only"] is True

def test_get_whiskies_with_limit():
    response = client.get("/api/db/whiskies?limit=10", headers=DB_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 10

def test_get_distilleries():
    response = client.get("/api/db/distilleries?limit=5", headers=DB_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 5

def test_search_lagavulin():
    response = client.get("/api/db/search?q=lagavulin", headers=DB_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_disabled_flag():
    os.environ["DB_API_ENABLED"] = "false"
    try:
        response = client.get("/api/db/health", headers=DB_HEADERS)
        assert response.status_code in [403, 404]
    finally:
        os.environ["DB_API_ENABLED"] = "true"

def test_api_key_required():
    # Without the API key header, all db_api endpoints must reject.
    response = client.get("/api/db/health")
    assert response.status_code == 403

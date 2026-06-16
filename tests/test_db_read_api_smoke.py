import os
import pytest
from fastapi.testclient import TestClient

# Mock environment variables before importing app
os.environ["DB_API_ENABLED"] = "true"
os.environ["MALT_RADAR_DB_PATH"] = "output/import/production.db"

from backend.app.main import app

client = TestClient(app)

def test_health_check_passes():
    response = client.get("/api/db/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "production.db" in data["db_path"]


def test_get_whiskies_with_limit():
    response = client.get("/api/db/whiskies?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 10
    
def test_get_distilleries():
    response = client.get("/api/db/distilleries?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 5

def test_search_lagavulin():
    response = client.get("/api/db/whiskies?q=lagavulin")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 0



def test_api_disabled_flag():
    # Override the flag dynamically for this test
    os.environ["DB_API_ENABLED"] = "false"
    try:
        response = client.get("/api/db/health")
        assert response.status_code == 404
    finally:
        # Restore for other potential tests
        os.environ["DB_API_ENABLED"] = "true"

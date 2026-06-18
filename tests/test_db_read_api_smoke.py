import os
import sys
import pytest
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

os.environ["DB_API_ENABLED"] = "true"
os.environ["MALT_RADAR_DB_PATH"] = "output/import/production.db"

from backend.app.main import app

client = TestClient(app)

def test_health_check_passes():
    response = client.get("/api/db/health")
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "read_only" in data
    assert data["read_only"] is True

def test_get_whiskies_with_limit():
    response = client.get("/api/db/whiskies?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10
    
def test_get_distilleries():
    response = client.get("/api/db/distilleries?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

def test_search_lagavulin():
    response = client.get("/api/db/search?q=lagavulin")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_disabled_flag():
    os.environ["DB_API_ENABLED"] = "false"
    try:
        response = client.get("/api/db/health")
        assert response.status_code in [403, 404]
    finally:
        os.environ["DB_API_ENABLED"] = "true"

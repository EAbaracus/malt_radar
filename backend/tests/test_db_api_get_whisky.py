import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sqlite3
import os

from app.main import app
from app.routers.db_api import get_service
from app.services.db_read_service import DbReadService

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
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True

@pytest.fixture
def auth_headers():
    client = TestClient(app)
    email = "test_get_whisky@example.com"
    password = "TestPassword123!"

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
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        token = login.json()["token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_service():
    service = MagicMock(spec=DbReadService)
    app.dependency_overrides[get_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_service, None)

def test_get_whisky_success(mock_service, auth_headers):
    mock_service.get_whisky.return_value = {"whisky_id": "test_id", "name": "Test Whisky"}
    client = TestClient(app)
    response = client.get("/api/db/whiskies/test_id", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"whisky_id": "test_id", "name": "Test Whisky"}
    mock_service.get_whisky.assert_called_once_with("test_id")

def test_get_whisky_not_found(mock_service, auth_headers):
    mock_service.get_whisky.return_value = None
    client = TestClient(app)
    response = client.get("/api/db/whiskies/not_found_id", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Whisky not found"

def test_get_whisky_db_missing(mock_service, auth_headers):
    mock_service.get_whisky.side_effect = FileNotFoundError()
    client = TestClient(app)
    response = client.get("/api/db/whiskies/test_id", headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["detail"] == "Database file missing"

def test_get_whisky_db_error(mock_service, auth_headers):
    mock_service.get_whisky.side_effect = sqlite3.Error()
    client = TestClient(app)
    response = client.get("/api/db/whiskies/test_id", headers=auth_headers)
    assert response.status_code == 500
    assert response.json()["detail"] == "Database query failed"

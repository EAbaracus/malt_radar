import pytest
import sqlite3
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.routers.db_api import get_service
from app.auth.routes import get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def enable_db_api():
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

def override_get_current_user():
    return {"user_id": "test_user"}

@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

def test_search_file_not_found_error(override_auth):
    mock_service = MagicMock()
    mock_service.search.side_effect = FileNotFoundError("DB not found")

    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.get("/api/db/search?q=macallan")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database file missing"

    app.dependency_overrides.pop(get_service, None)

def test_search_sqlite_error(override_auth):
    mock_service = MagicMock()
    mock_service.search.side_effect = sqlite3.Error("Query failed")

    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.get("/api/db/search?q=macallan")

    assert response.status_code == 500
    assert response.json()["detail"] == "Database query failed"

    app.dependency_overrides.pop(get_service, None)

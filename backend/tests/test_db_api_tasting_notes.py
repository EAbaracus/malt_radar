import pytest
from unittest.mock import MagicMock
import sqlite3
from fastapi.testclient import TestClient
from fastapi import HTTPException
import os

from app.main import app
from app.routers.db_api import get_service, check_db_api_enabled
from app.auth.routes import get_current_user

# Setup client
client = TestClient(app)

@pytest.fixture
def mock_service():
    service = MagicMock()
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: {"id": "test_user"}

    # We also need to enable the DB API
    old_val = os.environ.get("DB_API_ENABLED")
    os.environ["DB_API_ENABLED"] = "true"

    # Disable rate limiter to prevent 429 errors during testing
    app.state.limiter.enabled = False

    yield service

    app.state.limiter.enabled = True
    app.dependency_overrides.clear()
    if old_val is None:
        os.environ.pop("DB_API_ENABLED", None)
    else:
        os.environ["DB_API_ENABLED"] = old_val

def test_get_tasting_notes_success(mock_service):
    mock_service.get_tasting_notes.return_value = [{"note": "smoky", "whisky_id": "123"}]

    response = client.get("/api/db/whiskies/123/tasting-notes")

    assert response.status_code == 200
    assert response.json() == [{"note": "smoky", "whisky_id": "123"}]
    mock_service.get_tasting_notes.assert_called_once_with("123")

def test_get_tasting_notes_file_not_found(mock_service):
    mock_service.get_tasting_notes.side_effect = FileNotFoundError()

    response = client.get("/api/db/whiskies/123/tasting-notes")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database file missing"}

def test_get_tasting_notes_db_error(mock_service):
    mock_service.get_tasting_notes.side_effect = sqlite3.Error()

    response = client.get("/api/db/whiskies/123/tasting-notes")

    assert response.status_code == 500
    assert response.json() == {"detail": "Database query failed"}

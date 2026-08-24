import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.routers.db_api import get_service, check_db_api_enabled
from app.auth.routes import get_current_user

@pytest.fixture
def override_dependencies():
    app.dependency_overrides[check_db_api_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "test_user"}
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client(override_dependencies):
    return TestClient(app)

class MockService:
    def __init__(self, exception=None, return_value=None):
        self.exception = exception
        self.return_value = return_value

    def get_official_source_references(self, whisky_id: str):
        if self.exception:
            raise self.exception
        return self.return_value

def test_get_evidence_success(client):
    expected_data = [{"field_name": "test", "value": "123"}]
    app.dependency_overrides[get_service] = lambda: MockService(return_value=expected_data)

    response = client.get("/api/db/whiskies/123/evidence")
    assert response.status_code == 200
    assert response.json() == expected_data

def test_get_evidence_file_not_found(client):
    app.dependency_overrides[get_service] = lambda: MockService(exception=FileNotFoundError())

    response = client.get("/api/db/whiskies/123/evidence")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database file missing"

def test_get_evidence_sqlite_error(client):
    app.dependency_overrides[get_service] = lambda: MockService(exception=sqlite3.Error("Test DB Error"))

    response = client.get("/api/db/whiskies/123/evidence")
    assert response.status_code == 500
    assert response.json()["detail"] == "Database query failed"

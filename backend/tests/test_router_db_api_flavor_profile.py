import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.routers.db_api import get_service, check_db_api_enabled
from app.auth.routes import get_current_user

class MockDbReadService:
    def __init__(self, return_val=None, exception=None):
        self.return_val = return_val
        self.exception = exception

    def get_flavor_profile(self, whisky_id: str):
        if self.exception:
            raise self.exception
        return self.return_val

client = TestClient(app)

def override_get_current_user():
    return {"user_id": "test_user"}

def override_check_db_api_enabled():
    pass

@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[check_db_api_enabled] = override_check_db_api_enabled
    yield
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def disable_rate_limit():
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True

def test_get_flavor_profile_success():
    def override_get_service():
        return MockDbReadService(return_val={"profile": "sweet and smoky"})
    app.dependency_overrides[get_service] = override_get_service

    response = client.get("/api/db/whiskies/test-id-1/flavor-profile")
    assert response.status_code == 200
    assert response.json() == {"profile": "sweet and smoky"}

def test_get_flavor_profile_not_found():
    def override_get_service():
        return MockDbReadService(return_val=None)
    app.dependency_overrides[get_service] = override_get_service

    response = client.get("/api/db/whiskies/test-id-1/flavor-profile")
    assert response.status_code == 404
    assert response.json() == {"detail": "Flavor profile not found"}

def test_get_flavor_profile_db_missing():
    def override_get_service():
        return MockDbReadService(exception=FileNotFoundError())
    app.dependency_overrides[get_service] = override_get_service

    response = client.get("/api/db/whiskies/test-id-1/flavor-profile")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database file missing"}

def test_get_flavor_profile_db_error():
    def override_get_service():
        return MockDbReadService(exception=sqlite3.Error("Test DB Error"))
    app.dependency_overrides[get_service] = override_get_service

    response = client.get("/api/db/whiskies/test-id-1/flavor-profile")
    assert response.status_code == 500
    assert response.json() == {"detail": "Database query failed"}

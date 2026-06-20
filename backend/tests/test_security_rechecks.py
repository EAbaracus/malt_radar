import os
import sys
import subprocess
import pytest
from fastapi.testclient import TestClient

# Make sure backend is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, verify_api_key
from app.services.review_query_service import ReviewQueryService
from app.providers.sqlite_read_adapter import SqliteReadAdapter
from app.services.db_read_service import DbReadService

client = TestClient(app)

def test_api_key_protection_missing_header():
    # Attempting to access protected endpoint without header should fail
    response = client.get("/api/whiskies/search?q=test")
    assert response.status_code == 403
    assert "API Key" in response.json()["detail"]

def test_api_key_protection_invalid_header():
    response = client.get("/api/whiskies/search?q=test", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

def test_verify_api_key_no_fallback(monkeypatch):
    # Ensure there is no fallback to "mock-secret-key-123"
    import app.main
    monkeypatch.setattr(app.main, "API_KEY", None)
    
    # When API_KEY is None, it should raise 403
    from fastapi import HTTPException
    import asyncio
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_api_key("some-key"))
    assert exc.value.status_code == 403
    assert "not configured" in exc.value.detail

def test_seeder_script_fails_loudly(tmp_path):
    # Run the seeder script in a temp directory where CSVs don't exist
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts/72_production_import_seeder.py'))
    
    # subprocess run
    result = subprocess.run([sys.executable, script_path], cwd=tmp_path, capture_output=True, text=True)
    
    # Expect exit code 1
    assert result.returncode == 1
    # Expect loud error logging
    assert "CRITICAL ERROR: File not found" in result.stdout

def test_review_query_service_path_resolution():
    # Test that constructor injects path correctly
    svc = ReviewQueryService(db_path="test_custom.db")
    
    assert "test_custom.db" in svc._write_path
    assert "file:" in svc.db_path
    assert "?mode=ro" in svc.db_path

def test_sqlite_read_adapter_whitelist(monkeypatch):
    # Create an adapter and verify it rejects non-whitelisted tables
    adapter = SqliteReadAdapter()
    assert "whiskies" in adapter.canonical_tables
    assert "users" not in adapter.canonical_tables # Unsafe table

def test_db_read_service_health_whitelist():
    # Initialize service and check get_health logic
    svc = DbReadService()
    # If the DB doesn't exist, it returns reachable=False, but it shouldn't crash
    health = svc.get_health()
    assert "counts" in health

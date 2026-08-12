import pytest
import sqlite3
from app.services.db_read_service import DbReadService

@pytest.fixture
def service(tmp_path, monkeypatch):
    """Provides a DbReadService pointing to a temporary SQLite database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    # The DbReadService methods expect specific tables to exist.
    conn.execute("CREATE TABLE whiskies (whisky_id TEXT, name TEXT, superseded_by TEXT, distillery_id TEXT, data_confidence TEXT)")
    conn.execute("CREATE TABLE distilleries (distillery_id TEXT, name TEXT)")
    conn.execute("CREATE TABLE flavor_profiles (whisky_id TEXT, flavor_profile TEXT)")

    # Insert some dummy data if needed, or leave empty.
    conn.commit()
    conn.close()

    monkeypatch.setenv("MALT_RADAR_DB_PATH", str(db_path))
    return DbReadService()

def test_get_whisky_invalid_id_returns_none(service):
    """Test that fetching a whisky by an invalid or non-existent ID returns None."""
    result = service.get_whisky("non_existent_whisky_id_123")
    assert result is None

"""Faz C1: WriteGate.restrict_tables runtime enforcement testleri.

Production DB'ye dokunmaz — temp DB üzerinde:
- non-allowed table mutation → RuntimeError (ENFORCEMENT)
- allowed table mutation → commit
- SELECT read → always allowed (restriction sadece mutation'da)
"""
import os
import sys
import sqlite3
import tempfile

import pytest

# backend/ cwd → app paketini görmesin diye sys.path ek (pytest config'de backend var)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.write_guard import (
    WriteGate,
    get_write_connection,
    _extract_target_table,
    WriteGuardReassertError,
)


@pytest.fixture
def temp_db():
    """Temp DB with whiskies + review_actions schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.executescript(
        """
        CREATE TABLE whiskies (whisky_id TEXT PRIMARY KEY, name TEXT, production_price REAL);
        INSERT INTO whiskies VALUES ('W1', 'x', 999.0);
        CREATE TABLE review_actions (id INTEGER PRIMARY KEY, action TEXT);
        """
    )
    conn.commit()
    conn.close()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


class TestExtractTargetTable:
    @pytest.mark.parametrize("stmt,expected", [
        ("INSERT INTO review_actions (action) VALUES ('approve')", "review_actions"),
        ("UPDATE whiskies SET name = 'y' WHERE whisky_id = 'W1'", "whiskies"),
        ("DELETE FROM flavor_evidence WHERE whisky_id = 'W1'", "flavor_evidence"),
        ("REPLACE INTO t VALUES (1)", "t"),
        ("INSERT OR IGNORE INTO logs VALUES ('x')", "logs"),
    ])
    def test_extracts_table(self, stmt, expected):
        assert _extract_target_table(stmt) == expected

    @pytest.mark.parametrize("stmt", [
        "SELECT * FROM whiskies WHERE whisky_id = 'W1'",
        "PRAGMA integrity_check",
        "CREATE TABLE foo (x TEXT)",
        "BEGIN IMMEDIATE TRANSACTION",
        "COMMIT",
        "ALTER TABLE whiskies ADD COLUMN y INT",
        "DROP TABLE IF EXISTS t",
    ])
    def test_non_mutation_returns_none(self, stmt):
        assert _extract_target_table(stmt) is None


class TestRestrictTablesEnforcement:
    def test_insert_into_restricted_table_rejected(self, temp_db):
        """Non-allowed table INSERT → RuntimeError (enforce)."""
        with pytest.raises(RuntimeError, match="ENFORCEMENT"):
            with get_write_connection(
                authorized_context="test_c1",
                restrict_tables=["review_actions"],
                db_path=temp_db,
            ) as conn:
                conn.execute("INSERT INTO whiskies VALUES ('W2', 'leak', 999.0)")

    def test_update_restricted_table_rejected(self, temp_db):
        with pytest.raises(RuntimeError, match="ENFORCEMENT"):
            with get_write_connection("t", ["review_actions"], temp_db) as conn:
                conn.execute("UPDATE whiskies SET name = 'hacked' WHERE whisky_id = 'W1'")

    def test_delete_restricted_table_rejected(self, temp_db):
        with pytest.raises(RuntimeError, match="ENFORCEMENT"):
            with get_write_connection("t", ["review_actions"], temp_db) as conn:
                conn.execute("DELETE FROM whiskies WHERE whisky_id = 'W1'")

    def test_allowed_table_mutation_commits(self, temp_db):
        """review_actions allowed → commit; post_validate Row-aware (no crash)."""
        with get_write_connection("t", ["review_actions"], temp_db) as conn:
            conn.execute("INSERT INTO review_actions (action) VALUES ('approve')")
            conn.execute("INSERT INTO review_actions (action) VALUES ('escalate')")
        c = sqlite3.connect(temp_db)
        count = c.execute("SELECT COUNT(*) FROM review_actions").fetchone()[0]
        c.close()
        assert count == 2

    def test_select_always_allowed_under_restriction(self, temp_db):
        """Read (SELECT) under restrict_tables → never blocked."""
        with get_write_connection("t", ["review_actions"], temp_db) as conn:
            row = conn.execute("SELECT whisky_id FROM whiskies WHERE whisky_id = 'W1'").fetchone()
            assert row[0] == "W1"

    def test_no_restrict_tables_no_enforcement(self, temp_db):
        """restrict_tables=None → no enforcement (backward-compat)."""
        with get_write_connection("t", None, temp_db) as conn:
            conn.execute("INSERT INTO whiskies VALUES ('W2', 'ok', 100.0)")
        c = sqlite3.connect(temp_db)
        assert c.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0] == 2
        c.close()

    def test_enforcement_error_naming(self, temp_db):
        """Error message includes table name + authorized_context."""
        with pytest.raises(RuntimeError, match="whiskies"):
            with get_write_connection("t", ["review_actions"], temp_db) as conn:
                conn.execute("INSERT INTO whiskies VALUES ('WX', 'x', 0)")

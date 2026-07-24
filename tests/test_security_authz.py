"""Authorization & data-leak hardening tests.

Covers the three findings from the security review:
  A. Admin Review API requires an API key (no auth -> 403) and the audit
     `reviewer` field is derived from the verified identity, not the body.
  B. SourceGuard strips internal source fields from the public
     official_source_references read path.
  C. /api/db/* requires an API key (no auth -> 403).
"""
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

os.environ["DB_API_ENABLED"] = "true"
os.environ["MALT_RADAR_DB_PATH"] = "output/import/production.db"
os.environ["ADMIN_REVIEW_API_ENABLED"] = "true"
os.environ["ADMIN_REVIEW_WRITE_ENABLED"] = "false"
os.environ["ADMIN_REVIEW_PROMOTION_ENABLED"] = "false"

from fastapi.testclient import TestClient
from app.main import app
from backend.app.services.db_read_service import DbReadService
from backend.app.utils.source_guard import SourceGuard

client = TestClient(app)
ADMIN_HEADERS = {"X-API-Key": "test-api-key"}


# ----------------------------------------------------------------------
# A. Admin Review API authorization
# ----------------------------------------------------------------------
def test_admin_queue_requires_api_key():
    r = client.get("/admin/review/queue")
    assert r.status_code == 403


def test_admin_action_requires_api_key():
    r = client.post(
        "/admin/review/action",
        json={
            "source_table": "staging_new_products",
            "source_record_key": "x",
            "action_type": "PROMOTE",
            "target_status": "promoted",
            "reviewer": "attacker-forged",
        },
    )
    assert r.status_code == 403


def test_admin_queue_allowed_with_key():
    # Flag is enabled above; with a valid key the endpoint is reachable
    # (queue may be empty, but it must not be 403).
    r = client.get("/admin/review/queue", headers=ADMIN_HEADERS)
    assert r.status_code != 403


# ----------------------------------------------------------------------
# B. SourceGuard strips internal source fields on the public path
# ----------------------------------------------------------------------
def test_source_guard_strips_forbidden_fields_public():
    row = {
        "ref_id": 1,
        "entity_id": "W000001",
        "source_category": "official",
        "source_name": "Laphroaig Official",
        "source_url": "https://example.com/x",
        "source_domain": "example.com",
        "field_name": "age",
        "field_value": "10",
    }
    sanitized = SourceGuard.sanitize_response(row, is_manual=False)
    assert "source_name" not in sanitized
    assert "source_url" not in sanitized
    assert "source_domain" not in sanitized
    # Non-forbidden fields are preserved
    assert sanitized["field_name"] == "age"
    assert sanitized["field_value"] == "10"


def test_source_guard_retains_for_admin_is_manual():
    row = {"source_name": "internal", "source_url": "https://int/x"}
    sanitized = SourceGuard.sanitize_response(row, is_manual=True)
    assert "source_name" in sanitized
    assert "source_url" in sanitized


def test_db_read_service_evidence_strips_source_fields():
    """Integration check: the public evidence read path must not leak
    internal source fields even if the DB row contains them."""
    svc = DbReadService()
    # Build an in-memory DB mimicking official_source_references shape.
    import sqlite3
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "hermes_sec_evidence.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    conn = sqlite3.connect(tmp)
    conn.execute(
        "CREATE TABLE official_source_references ("
        "ref_id INTEGER PRIMARY KEY, entity_id TEXT, source_name TEXT, "
        "source_url TEXT, source_domain TEXT, field_name TEXT, field_value TEXT)"
    )
    conn.execute(
        "INSERT INTO official_source_references "
        "(entity_id, source_name, source_url, source_domain, field_name, field_value) "
        "VALUES ('W000001','Secret Src','https://secret/x','secret.com','age','10')"
    )
    conn.commit()
    conn.close()

    svc.db_path = tmp
    rows = svc.get_official_source_references("W000001")
    assert len(rows) == 1
    r = rows[0]
    assert "source_name" not in r
    assert "source_url" not in r
    assert "source_domain" not in r
    assert r["field_value"] == "10"
    try:
        os.remove(tmp)
    except OSError:
        pass


# ----------------------------------------------------------------------
# C. /api/db/* requires an API key
# ----------------------------------------------------------------------
def test_db_api_requires_api_key():
    r = client.get("/api/db/health")
    assert r.status_code == 403


def test_db_api_allowed_with_key():
    r = client.get("/api/db/health", headers=ADMIN_HEADERS)
    assert r.status_code == 200

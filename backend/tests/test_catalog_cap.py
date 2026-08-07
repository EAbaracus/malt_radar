"""Anti-scrape catalog bounds: page cap + cumulative offset guard (service-level)."""
from __future__ import annotations

import os
import sqlite3

import pytest

from app.services.db_read_service import (
    DbReadService,
    CatalogBoundsError,
    CATALOG_MAX_PAGE,
)


@pytest.fixture()
def service(tmp_path, monkeypatch):
    db = tmp_path / "catalog.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE whiskies (
          whisky_id TEXT PRIMARY KEY,
          name TEXT,
          superseded_by TEXT,
          distillery_id TEXT,
          data_confidence TEXT
        );
        CREATE TABLE distilleries (
          distillery_id TEXT PRIMARY KEY,
          name TEXT
        );
        CREATE TABLE flavor_profiles (
          whisky_id TEXT PRIMARY KEY,
          flavor_profile TEXT
        );
        """
    )
    for i in range(300):
        conn.execute(
            "INSERT INTO whiskies VALUES (?, ?, NULL, 'D1', 'legacy')",
            (f"W-{i:04d}", f"Whisky {i}"),
        )
    conn.execute("INSERT INTO distilleries VALUES ('D1', 'Test Distillery')")
    conn.commit()
    conn.close()

    monkeypatch.setenv("MALT_RADAR_DB_PATH", str(db))
    return DbReadService()


def test_limit_is_clamped_to_max_page(service):
    res = service.get_whiskies(limit=5000)
    assert res["limit"] == CATALOG_MAX_PAGE
    assert len(res["items"]) <= CATALOG_MAX_PAGE


def test_limit_defaults_to_50(service):
    res = service.get_whiskies()
    assert res["limit"] == 50


def test_offset_beyond_browse_limit_rejected(service):
    with pytest.raises(CatalogBoundsError):
        service.get_whiskies(offset=2_000_000_000)


def test_normal_paging_ok(service):
    res = service.get_whiskies(limit=50, offset=50)
    assert res["offset"] == 50
    assert len(res["items"]) <= 50
    # Ordered ascending by name (lexicographic in SQLite), certified GSD first.
    assert all(isinstance(it.get("name"), str) for it in res["items"])
    names = [it["name"] for it in res["items"]]
    assert names == sorted(names)


def test_distilleries_capped_and_guarded(service):
    res = service.get_distilleries(limit=500)
    assert res["limit"] == CATALOG_MAX_PAGE
    with pytest.raises(CatalogBoundsError):
        service.get_distilleries(offset=2_000_000_000)

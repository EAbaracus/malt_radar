import os
import sqlite3
import pytest
from typing import Dict, Any

from app.services.db_read_service import DbReadService

@pytest.fixture()
def service(tmp_path, monkeypatch):
    db = tmp_path / "catalog.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE distilleries (
          distillery_id TEXT PRIMARY KEY,
          name TEXT
        );
        CREATE TABLE whiskies (
          whisky_id TEXT PRIMARY KEY,
          name TEXT,
          distillery_id TEXT,
          superseded_by TEXT,
          FOREIGN KEY (distillery_id) REFERENCES distilleries(distillery_id)
        );
        """
    )

    distilleries_data = [
        ("D1", "A-Distillery"),
        ("D2", "B-Distillery"),
        ("D3", "C-Distillery"),
        ("D4", "Z-ZeroWhisky-Distillery"),
    ]
    conn.executemany("INSERT INTO distilleries VALUES (?, ?)", distilleries_data)

    whiskies_data = [
        ("W1", "A-Whisky 1", "D1", None),
        ("W2", "A-Whisky 2", "D1", None),
        ("W3", "A-Whisky 3", "D1", None),
        ("W4", "B-Whisky 1", "D2", None),
        ("W5", "B-Whisky 2", "D2", None),
        ("W6", "C-Whisky 1", "D3", None),
    ]
    conn.executemany("INSERT INTO whiskies VALUES (?, ?, ?, ?)", whiskies_data)

    conn.commit()
    conn.close()

    monkeypatch.setenv("MALT_RADAR_DB_PATH", str(db))
    return DbReadService()

def test_get_distilleries_happy_path(service):
    res = service.get_distilleries(limit=10, offset=0)

    assert "items" in res
    assert "total_count" in res
    assert res["limit"] == 10
    assert res["offset"] == 0

    items = res["items"]
    assert len(items) == 4

    # We seeded D1 with 3 whiskies, D2 with 2, D3 with 1, D4 with 0.
    # Results should be ordered by name ascending.
    assert items[0]["name"] == "A-Distillery"
    assert items[0]["whisky_count"] == 3

    assert items[1]["name"] == "B-Distillery"
    assert items[1]["whisky_count"] == 2

    assert items[2]["name"] == "C-Distillery"
    assert items[2]["whisky_count"] == 1

def test_get_distilleries_pagination(service):
    # Test offset and limit
    res = service.get_distilleries(limit=2, offset=1)

    assert res["limit"] == 2
    assert res["offset"] == 1

    items = res["items"]
    assert len(items) == 2

    # We skipped "A-Distillery" (offset 1)
    assert items[0]["name"] == "B-Distillery"
    assert items[1]["name"] == "C-Distillery"

def test_get_distilleries_sorting(service):
    res = service.get_distilleries(limit=10, offset=0)
    items = res["items"]
    names = [item["name"] for item in items]

    assert names == sorted(names)

def test_get_distilleries_zero_whiskies(service):
    res = service.get_distilleries(limit=10, offset=0)
    items = res["items"]

    # D4 was inserted with 0 whiskies associated
    # "Z-ZeroWhisky-Distillery" should appear last
    zero_whisky_distillery = [item for item in items if item["name"] == "Z-ZeroWhisky-Distillery"][0]

    assert zero_whisky_distillery is not None
    assert zero_whisky_distillery["whisky_count"] == 0

"""Product Rule regresyon testi — fiyat verisi API yanıtına SIZMAZ (AGENTS.md).

Regresyon: get_flavor_profile SELECT * kullanıyordu -> production_price kolonu
yanıta giriyordu (canlıda 853B yanıtta doğrulandı). Alan filtreleme sonrası
production_price anahtarı hiçbir dönüşte bulunmamalı; radar için zorunlu
flavor_profile alanı korunmalı.

Hermetic: kendi mini-DB'sini kurar (gerçek bir production whisky_id'sine
bağımlı değil), diğer test dosyalarındaki desenle tutarlı.
"""
import sqlite3

import pytest

from app.services.db_read_service import DbReadService

TEST_WHISKY_ID = "W-PRICE-LEAK-TEST"


@pytest.fixture
def service(tmp_path, monkeypatch):
    db = tmp_path / "price_leak.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE flavor_profiles (
          whisky_id TEXT PRIMARY KEY,
          whisky_name TEXT,
          production_bottle_name TEXT,
          match_score INTEGER,
          match_method TEXT,
          flavor_vector TEXT,
          flavor_profile TEXT,
          flavor_tags TEXT,
          flavor_source TEXT,
          flavor_data_confidence TEXT,
          production_price REAL,
          production_rating REAL,
          production_region TEXT,
          notes_for_review TEXT,
          source_count INTEGER DEFAULT 1,
          evidence_count INTEGER DEFAULT 1,
          enrichment_version INTEGER DEFAULT 1
        );
        """
    )
    conn.execute(
        "INSERT INTO flavor_profiles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            TEST_WHISKY_ID,
            "Test Whisky",
            "Test Whisky Batch 1",
            0.9,
            "test",
            None,
            '{"fruity": 5, "sweet": 4}',
            "fruity,sweet",
            "test",
            "high",
            199.99,  # production_price — must never leak into the response
            4.2,
            "Speyside",
            None,
            1,
            1,
            1,
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("MALT_RADAR_DB_PATH", str(db))
    return DbReadService()


def test_flavor_profile_has_no_price(service):
    r = service.get_flavor_profile(TEST_WHISKY_ID)
    assert r is not None
    assert "production_price" not in r


def test_flavor_profile_keeps_radar_fields(service):
    r = service.get_flavor_profile(TEST_WHISKY_ID)
    assert r is not None
    assert "flavor_profile" in r          # radar için zorunlu alan korunur
    assert "flavor_tags" in r
    assert "flavor_source" in r


def test_flavor_profile_missing_whisky_returns_none(service):
    assert service.get_flavor_profile("YOK-BOYLE-BIR-ID") is None

"""Product Rule regresyon testi — fiyat verisi API yanıtına SIZMAZ (AGENTS.md).

Regresyon: get_flavor_profile SELECT * kullanıyordu -> production_price kolonu
yanıta giriyordu (canlıda 853B yanıtta doğrulandı). Alan filtreleme sonrası
production_price anahtarı hiçbir dönüşte bulunmamalı; radar için zorunlu
flavor_profile alanı korunmalı.
"""
import pytest

from app.services.db_read_service import DbReadService


@pytest.fixture
def service():
    return DbReadService()


def test_flavor_profile_has_no_price(service):
    # Canlı veride profile sahip bir viski (W000441 amrut fusion).
    r = service.get_flavor_profile("W000441")
    assert r is not None
    assert "production_price" not in r


def test_flavor_profile_keeps_radar_fields(service):
    r = service.get_flavor_profile("W000441")
    assert r is not None
    assert "flavor_profile" in r          # radar için zorunlu alan korunur
    assert "flavor_tags" in r
    assert "flavor_source" in r


def test_flavor_profile_missing_whisky_returns_none(service):
    assert service.get_flavor_profile("YOK-BOYLE-BIR-ID") is None

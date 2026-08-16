"""SMWS/SYNTH mark-and-hide read-path filter tests (kod fix ön koşulu).

Kapsam: DbReadService'in TÜM canonical read yolları superseded_by IS NULL
filtrelemeli:

  * get_whiskies        — liste/pagination + distillery_id filtreli
  * get_whisky(id)      — tekil (deep-link/URL ile görünür kalmamalı)
  * get_distilleries    — whisky_count superseded satırları saymamalı
  * search              — autocomplete aynı filtreyi uygulamalı
  * get_filters         — quarantined distilleries filtre listesinde olmamalı

Kullanıcı istediği 3 case:
  1. superseded_by dolu kayıt get_whiskies'te dönmüyor
  2. aynı kayıt get_whisky(id) ile direkt sorgulanınca da dönmüyor (None)
  3. superseded_by IS NULL normal kayıtlar hâlâ görünüyor (regresyon yok)
"""
import sqlite3
import pytest

from app.services.db_read_service import DbReadService


@pytest.fixture
def service(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE whiskies (
            whisky_id TEXT, name TEXT, original_name TEXT,
            superseded_by TEXT, distillery_id TEXT, type TEXT, country TEXT,
            region TEXT, brand TEXT, data_confidence TEXT, abv REAL
        );
        CREATE TABLE distilleries (distillery_id TEXT, name TEXT);
        CREATE TABLE flavor_profiles (whisky_id TEXT, flavor_profile TEXT);
        """
    )
    conn.execute(
        # superseded_by: production'da NULL (aktif) veya değer (superseded) —
        # boş string YOK. Fixture bunu birebir yansıtmalı.
        "INSERT INTO whiskies VALUES "
        "('W-ACTIVE-1','Active Single Malt',NULL,NULL,NULL,'Malt','Scotland','Speyside',NULL,NULL,NULL),"
        "('W-QUAR-1','SMWS 1.139 - Test',NULL,'QUARANTINE-2026-08-16','D1389','Malt','Scotland',NULL,NULL,NULL,NULL),"
        "('W-QUAR-2','Akashi Red',NULL,'QUARANTINE-2026-08-16','D1078','Malt','Scotland',NULL,NULL,NULL,NULL),"
        "('W-ACTIVE-2','Active Blend',NULL,NULL,NULL,'Blend','Scotland',NULL,NULL,NULL,NULL)"
    )
    conn.execute(
        "INSERT INTO distilleries VALUES "
        "('D1389','SMWS Distillery'),('D1078','Akashi Distillery'),('D-OK','Good Distillery')"
    )
    conn.execute(
        "INSERT INTO whiskies VALUES "
        "('W-ACTIVE-3','Good Distillery Whisky',NULL,NULL,'D-OK','Malt','Scotland',NULL,NULL,NULL,NULL)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("MALT_RADAR_DB_PATH", str(db_path))
    return DbReadService()


def _ids(rows):
    return {r["whisky_id"] for r in rows}


def test_get_whiskies_excludes_superseded(service):
    """Case 1: superseded_by dolu kayıt liste sorgusunda dönmüyor."""
    res = service.get_whiskies(limit=50, offset=0)
    ids = _ids(res["items"])
    assert "W-ACTIVE-1" in ids
    assert "W-ACTIVE-2" in ids
    assert "W-QUAR-1" not in ids
    assert "W-QUAR-2" not in ids


def test_get_whisky_superseded_returns_none(service):
    """Case 2: superseded kayıt tekil sorguda da dönmüyor (deep-link kapalı)."""
    assert service.get_whisky("W-QUAR-1") is None
    assert service.get_whisky("W-QUAR-2") is None


def test_get_whisky_active_still_visible(service):
    """Case 3 (regresyon): aktif kayıt tekil sorguda hâlâ görünüyor."""
    row = service.get_whisky("W-ACTIVE-1")
    assert row is not None
    assert row["whisky_id"] == "W-ACTIVE-1"


def test_get_whiskies_active_count_unchanged(service):
    """Regresyon: normal kayıtların sayısı/görünürlüğü bozulmadı."""
    res = service.get_whiskies(limit=50, offset=0)
    active = [r for r in res["items"] if r["whisky_id"].startswith("W-ACTIVE")]
    assert len(active) == 3  # W-ACTIVE-1, W-ACTIVE-2, W-ACTIVE-3


def test_search_excludes_superseded(service):
    """Autocomplete/search aynı filtreyi uyguluyor."""
    # 'SMWS' araması quarantined satırı bulmamalı (filtre + superseded).
    assert service.search("SMWS") == []
    # Aktif kayıtlar aranabilir.
    hits = service.search("Active")
    assert any(r["whisky_id"] == "W-ACTIVE-1" for r in hits)


def test_get_distilleries_count_excludes_superseded(service):
    """get_distilleries: whisky_count superseded satırları saymıyor."""
    res = service.get_distilleries(limit=50, offset=0)
    by_id = {r["distillery_id"]: r for r in res["items"]}
    # D1389'un 1 superseded whiskysi var -> count 0 olmalı.
    assert by_id["D1389"]["whisky_count"] == 0
    assert by_id["D-OK"]["whisky_count"] == 1


def test_get_filters_excludes_quarantined_distilleries(service):
    """get_filters: sadece aktif whisky'si olan distilleries listelenir."""
    filters = service.get_filters()
    dist_ids = {d["distillery_id"] for d in filters["distilleries"]}
    assert "D-OK" in dist_ids
    assert "D1389" not in dist_ids  # tüm whiskyleri superseded
    assert "D1078" not in dist_ids  # tüm whiskyleri superseded

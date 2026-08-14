"""Faz B: ProductionReadAdapter price-leak + canonical-table testleri.

Product Rule (AGENTS.md): price bilgisi ASALAPU yanıta girmez.
Bu test adapter'ın universal redaction'unu, SELECT * yapan read'in bile fiyatı
sızdırmayacağını kanıtlar.
"""
import os
import sys
import sqlite3

import pytest

# pytest backend/ cwd'de koştuğunda da production.db bulunmalı.
# tests/ → backend/ → project_root/output/import/production.db
_TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS_ROOT))  # backend/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TESTS_ROOT))  # project root
_PRICE_DB = os.path.join(_PROJECT_ROOT, "output", "import", "production.db")

from app.db.production_read_adapter import ProductionReadAdapter, _PRICE_COLUMN_NAMES


@pytest.fixture(scope="module")
def adapter():
    if not os.path.exists(_PRICE_DB):
        pytest.skip("production.db not available")
    return ProductionReadAdapter()


@pytest.mark.parametrize("table", [
    "whiskies",
    "price_history",
])
def test_price_cols_never_leak_from_query(adapter, table):
    """SELECT * yapan query() fiyat kolonunu redact zorunda."""
    rows = adapter.query(table, limit=5)
    leaked = set()
    for r in rows:
        leaked |= set(r.keys()) & _PRICE_COLUMN_NAMES
    assert leaked == set(), f"price cols leaked from {table}: {leaked}"


def test_whiskies_query_star_no_price(adapter):
    # whiskies tablosunda production_price kolonu YOK (verify: 2026-08-11).
    # Ama gelecekte eklense bile redaction devreye girmeli.
    rows = adapter.query("whiskies", limit=3)
    cols = set()
    for r in rows:
        cols |= set(r.keys())
    assert not (cols & _PRICE_COLUMN_NAMES), f"whiskies leaked: {cols & _PRICE_COLUMN_NAMES}"


def test_non_canonical_table_rejected(adapter):
    """G4: canonical olmayan tablo read'de reject."""
    with pytest.raises(ValueError, match="Non-canonical read table"):
        adapter.query("users_does_not_exist", limit=1)


def test_query_only_mode(adapter):
    """Defense-in-depth: PRAGMA query_only=ON."""
    conn = adapter._get_connection()
    val = conn.execute("PRAGMA query_only").fetchone()[0]
    assert val == 1, "query_only not ON"
    conn.close()


def test_price_history_columns_stripped(adapter):
    """price_history SELECT * redacted: price_value/production_price yok."""
    with adapter._get_connection() as conn:
        rows = adapter.query("price_history", limit=3)
    cols = set()
    for r in rows:
        cols |= set(r.keys())
    # production_price asla yok (whiskies'de yok)
    assert "production_price" not in cols
    # price_value redact edilmeli
    assert "price_value" not in cols


def test_flavor_profile_method(adapter):
    """get_flavor_profile read seam üzerinden, fiyat sızıntısız."""
    fp = adapter.get_flavor_profile("nonexistent_whisky_id")
    assert fp is None  # read düzgün parse, hata vermiyor


def test_adapter_path_matches_db_read_service():
    """Adapter db_path'i production.db path'ine çözülmeli."""
    a = ProductionReadAdapter()
    resolved_abs = os.path.abspath(a.db_path)
    assert resolved_abs.endswith(os.path.join("output", "import", "production.db")), resolved_abs

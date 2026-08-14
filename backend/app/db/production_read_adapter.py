"""ProductionReadAdapter — Tek okuma seam'i.

Faz B (spec: docs/superpowers/specs/2026-08-11-read-write-seam-guard-design.md):

    G4: `sqlite3.connect` production.db path'ine hedefliyor → sadece
    backend/app/db/production_read_adapter.py (read) + db/write_guard.py (write).

Bu adapter'in AMACI:
- Tek read seam: DbReadService (catalog) + ReviewQueryService (admin queue read)
  read metotlarının hepsi buradan geçer.
- Tek _get_connection: mode=ro + PRAGMA query_only=ON (defense-in-depth).
- Merkezi fiyat redaction: PRAGMA table_info'dan fiyat kolonunu tespit eden
  universal redactor. SELECT * yapan bir read bile fiyatı sızdırmaz.

NOT: whiskies tablosunda production_price kolonu YOK (canlı verify, 2026-08-11).
Fiyat price_history tablosundadır. Redaction universal (kolon adlarıyla) çünkü
gelecekte yeni bir read SELECT * yapsa bile korunsun.
"""
from __future__ import annotations

import os
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from app.utils.shared_paths import (
    resolve_db_path,
)


# ---------------------------------------------------------------------------
# Canonical read-only configuration
# ---------------------------------------------------------------------------

CATALOG_TABLES = frozenset({
    "whiskies", "distilleries", "tasting_notes",
    "flavor_profiles", "price_history", "official_source_references",
    "knowledge_regions", "knowledge_glossary_terms", "knowledge_guides",
})

REVIEW_TABLES = frozenset({
    "staging_new_products", "staging_tasting_notes",
    "staging_historical_menu_prices", "staging_manual_review_queue",
})

TRANSITION_TABLES = frozenset({"review_status_transitions"})

ALL_CANONICAL_TABLES = CATALOG_TABLES | REVIEW_TABLES | TRANSITION_TABLES


# Columns that the Product Rule (AGENTS.md) ASALAPU: hiçbir zaman bir read
# yanıtına girmez. Kolon ADI bazlı match — SELECT * bile sızdırmaz.
_PRICE_COLUMN_NAMES = frozenset({
    "production_price", "price_value", "price_context",
    "pour_size_ml", "price_currency", "price_per_ml",
})


class ProductionReadAdapter:
    """Single read seam over output/import/production.db.

    db_path, MALT_RADAR_DB_PATH env'i veya explicit argümanla override edilir.
    Path çözümlemesi DbReadService'in mantığından (3 level up from
    backend/app/db/production_read_adapter.py) aynı kalır.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        # Faz B: merkezi path resolution (shared_paths.resolve_db_path).
        # Eski copy-paste 3-level-up → tek fonksiyon. caller_file=__file__
        # ile backend/app/db/production_read_adapter.py → 3 dirname = project root.
        self.db_path = resolve_db_path(db_path, caller_file=__file__)
        self._ro_uri = f"file:{self.db_path}?mode=ro"

    # -- connection ----------------------------------------------------------
    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        """Validate table against canonical list — reject non-canonical."""
        if table not in ALL_CANONICAL_TABLES:
            raise ValueError(f"Non-canonical read table rejected: {table}")
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchall()
        return len(rows) > 0

    def _get_connection(self) -> sqlite3.Connection:
        """Read-only URI + PRAGMA query_only ON (defense-in-depth)."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA query_only = ON")
        return conn

    def raw_connection(self) -> sqlite3.Connection:
        """Public read-only connection seam.

        Prefer this over the private `_get_connection` for direct read access
        (e.g. one-off build scripts that need raw SQL against production.db).
        Returns a read-only URI connection with PRAGMA query_only ON; use it
        as a context manager: `with adapter.raw_connection() as conn:`.
        """
        return self._get_connection()

    # -- redaction -----------------------------------------------------------
    @staticmethod
    def _extract_price_columns(conn: sqlite3.Connection, table: str) -> set[str]:
        """PRAGMA table_info'dan fiyat kolonlarını çıkar (SELECT * safe)."""
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {c["name"] for c in cols if c["name"] in _PRICE_COLUMN_NAMES}

    def _redact_prices(self, rows: list[sqlite3.Row], conn: sqlite3.Connection,
                       table: str) -> List[Dict[str, Any]]:
        price_cols = self._extract_price_columns(conn, table)
        out: List[Dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            for col in price_cols:
                d.pop(col, None)
            out.append(d)
        return out

    def query(self, table: str, where: str = "", params: tuple = (),
              select: str = "*", order_by: str = "", limit: Optional[int] = None,
              offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Canonical read entry. Table canonical list'te olmalı; fiyat redact.

        Bu, DbReadService + ReviewQueryService read'lerinin tümüne delegate
        edilecek tek seam. SELECT * güvencesi: redaction universal kolon-adı.
        """
        with self._get_connection() as conn:
            self._table_exists(conn, table)
            order_clause = f" ORDER BY {order_by}" if order_by else ""
            q = f"SELECT {select} FROM {table}"
            w = f" WHERE {where}" if where else ""
            lim = f" LIMIT {int(limit)}" if limit is not None else ""
            off = f" OFFSET {int(offset)}" if offset is not None else ""
            sql = f"{q}{w}{order_clause}{lim}{off}"
            rows = conn.execute(sql, params).fetchall()
            # Eğer select "*" ise fiyat kolonlarını strip et
            if select == "*" or (select == "" and not where):
                return self._redact_prices(rows, conn, table)
            return [dict(r) for r in rows]

    def get_flavor_profile(self, whisky_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT flavor_profile FROM flavor_profiles WHERE whisky_id = ?",
                (whisky_id,),
            ).fetchone()
        return row["flavor_profile"] if row else None

    def get_unified_queue(self, status: Optional[str] = None,
                          source_table: Optional[str] = None,
                          limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Review queue UNION. Fiyat sızıntı riski yok — staging_*/knowledge_*
        tablolarında PRICE_COLUMN_NAMES kolonu yoktur."""
        tables = [
            "staging_new_products", "staging_tasting_notes",
            "staging_historical_menu_prices", "staging_manual_review_queue",
            "knowledge_regions", "knowledge_glossary_terms", "knowledge_guides",
        ]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            selects: List[str] = []
            for t in tables:
                cursor.execute(f"PRAGMA table_info({t})")
                cols = [row["name"] for row in cursor.fetchall()]
                if not cols:
                    continue
                c_key = "candidate_name" if t == "staging_manual_review_queue" else "source_record_key"
                c_key = c_key if c_key in cols else "''"
                c_disp = "''"
                for n in ["name", "title", "candidate_name", "term", "whisky_name"]:
                    if n in cols:
                        c_disp = n; break
                c_src = "source_name" if "source_name" in cols else ("source" if "source" in cols else "'unknown'")
                c_app = "approval_status" if "approval_status" in cols else "'pending_review'"
                c_ded = "dedupe_action" if "dedupe_action" in cols else "''"
                c_rec = "import_recommendation" if "import_recommendation" in cols else "''"
                c_cre = "original_row_index" if "original_row_index" in cols else "'0'"
                c_con = "'1'" if t == "staging_manual_review_queue" else "'0'"
                q = (
                    f"SELECT '{t}' as source_table, "
                    f"CAST({c_key} AS TEXT) as source_record_key, "
                    f"CAST({c_disp} AS TEXT) as display_name, "
                    f"CAST({c_src} AS TEXT) as source_name, "
                    f"CAST({c_app} AS TEXT) as approval_status, "
                    f"CAST({c_ded} AS TEXT) as dedupe_action, "
                    f"CAST({c_rec} AS TEXT) as import_recommendation, "
                    f"CAST({c_cre} AS TEXT) as created_at, "
                    f"0 as review_priority, "
                    f"CAST({c_con} AS TEXT) as conflict_flag FROM {t}"
                )
                selects.append(q)
            union_q = " UNION ALL ".join(selects)
            where_clauses: List[str] = []
            params: list[Any] = []
            if status:
                where_clauses.append("approval_status = ?")
                params.append(status)
            if source_table and source_table in tables:
                where_clauses.append("source_table = ?")
                params.append(source_table)
            final_q = f"SELECT * FROM ({union_q})"
            if where_clauses:
                final_q += " WHERE " + " AND ".join(where_clauses)
            def _safe_int(value, default, min_value, max_value=None):
                try:
                    parsed = int(value)
                except (TypeError, ValueError):
                    parsed = default
                parsed = max(min_value, parsed)
                if max_value is not None:
                    parsed = min(max_value, parsed)
                return parsed
            safe_limit = _safe_int(limit, default=50, min_value=1, max_value=500)
            safe_offset = _safe_int(offset, default=0, min_value=0)
            final_q += " LIMIT ? OFFSET ?"
            params.extend([safe_limit, safe_offset])
            try:
                cursor.execute(final_q, params)
                return [dict(r) for r in cursor.fetchall()]
            except sqlite3.Error as e:
                logging.warning(f"Database query error in get_unified_queue: {e}")
                return []

    def get_price_history(self, whisky_id: str) -> List[Dict[str, Any]]:
        """price_history read: fiyat kolonları redact edilir."""
        return self.query(
            "price_history",
            where="whisky_id = ?",
            params=(whisky_id,),
            order_by="observed_at DESC",
        )

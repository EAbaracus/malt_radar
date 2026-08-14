import os
import sqlite3
from typing import List, Dict, Any, Optional

class SqliteReadAdapter:
    def __init__(self):
        # Resolve path
        self.db_path_source = "env" if "MALT_RADAR_DB_PATH" in os.environ else "default"
        db_path = os.getenv("MALT_RADAR_DB_PATH", "output/import/production.db")
        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.db_path = os.path.abspath(os.path.join(base_dir, db_path))
        else:
            self.db_path = db_path
            
        self.canonical_tables = [
            "distilleries", "whiskies", "tasting_notes", "flavor_profiles", "price_history",
            "staging_new_products", "staging_tasting_notes", "staging_historical_menu_prices",
            "staging_manual_review_queue", "knowledge_regions", "knowledge_glossary_terms",
            "knowledge_guides", "review_actions", "promotion_audit_log", "review_conflict_log",
            "review_status_transitions"
        ]

    def _get_connection(self):
        # Read-only explicitly
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def get_health(self) -> Dict[str, Any]:
        exists = os.path.exists(self.db_path)
        tables = []
        table_counts = {}
        missing_tables = self.canonical_tables.copy()
        
        ALLOWED_TABLES = set(self.canonical_tables)
        
        if exists:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row["name"] for row in cursor.fetchall()]
                    
                    for t in tables:
                        if t not in ALLOWED_TABLES:
                            continue
                        if t in missing_tables:
                            missing_tables.remove(t)
                        cursor.execute(f"SELECT COUNT(*) as c FROM {t};")
                        table_counts[t] = cursor.fetchone()["c"]
            except Exception:
                pass
                
        is_canonical = len(missing_tables) == 0 and exists
        
        return {
            "status": "ok" if exists else "error",
            "db_path": self.db_path,
            "db_path_source": self.db_path_source,
            "read_only": True,
            "db_exists": exists,
            "expected_tables_present": [t for t in self.canonical_tables if t not in missing_tables],
            "missing_tables": missing_tables,
            "table_counts": table_counts,
            "canonical": is_canonical
        }

    def get_schema(self) -> Dict[str, Any]:
        schema = {}
        ALLOWED_TABLES = set(self.canonical_tables)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
            for row in cursor.fetchall():
                tname = row["name"]
                if tname not in ALLOWED_TABLES:
                    continue
                sql = row["sql"]
                cursor.execute(f"PRAGMA table_info({tname});")
                cols = [{"cid": c["cid"], "name": c["name"], "type": c["type"]} for c in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) as c FROM {tname};")
                count = cursor.fetchone()["c"]
                schema[tname] = {
                    "sql": sql,
                    "columns": cols,
                    "row_count": count
                }
        
        canonical_check = all(t in schema for t in self.canonical_tables)
        return {
            "tables": list(schema.keys()),
            "schema": schema,
            "expected_canonical_table_check": canonical_check
        }

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: Optional[str] = None) -> Dict[str, Any]:
        limit = min(max(1, limit), 100)
        offset = max(0, offset)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if q and len(q.strip()) > 0:
                # SQLite LIKE is case-insensitive for ASCII but not reliably for
                # Unicode. Normalize only the comparison side; never mutate display data.
                search = q.strip()
                pattern = f"%{search}%"
                count_query = "SELECT COUNT(*) as c FROM whiskies WHERE LOWER(name) LIKE LOWER(?) OR LOWER(COALESCE(original_name, '')) LIKE LOWER(?)"
                cursor.execute(count_query, (pattern, pattern))
                total = cursor.fetchone()["c"]
                
                query = "SELECT * FROM whiskies WHERE LOWER(name) LIKE LOWER(?) OR LOWER(COALESCE(original_name, '')) LIKE LOWER(?) LIMIT ? OFFSET ?"
                cursor.execute(query, (pattern, pattern, limit, offset))
            else:
                count_query = "SELECT COUNT(*) as c FROM whiskies"
                cursor.execute(count_query)
                total = cursor.fetchone()["c"]
                
                query = "SELECT * FROM whiskies LIMIT ? OFFSET ?"
                cursor.execute(query, (limit, offset))
                
            items = [dict(row) for row in cursor.fetchall()]
            return {
                "items": items,
                "total_count": total,
                "limit": limit,
                "offset": offset
            }

    def get_whisky(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM whiskies WHERE whisky_id = ?", (whisky_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_distilleries(self, limit: int = 50, offset: int = 0, q: Optional[str] = None) -> Dict[str, Any]:
        limit = min(max(1, limit), 100)
        offset = max(0, offset)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if q and len(q.strip()) > 0:
                count_query = "SELECT COUNT(*) as c FROM distilleries WHERE name LIKE ?"
                cursor.execute(count_query, (f"%{q.strip()}%",))
                total = cursor.fetchone()["c"]
                
                query = "SELECT * FROM distilleries WHERE name LIKE ? LIMIT ? OFFSET ?"
                cursor.execute(query, (f"%{q.strip()}%", limit, offset))
            else:
                count_query = "SELECT COUNT(*) as c FROM distilleries"
                cursor.execute(count_query)
                total = cursor.fetchone()["c"]
                
                query = "SELECT * FROM distilleries LIMIT ? OFFSET ?"
                cursor.execute(query, (limit, offset))
                
            items = [dict(row) for row in cursor.fetchall()]
            return {
                "items": items,
                "total_count": total,
                "limit": limit,
                "offset": offset
            }

    def get_distillery(self, distillery_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM distilleries WHERE distillery_id = ?", (distillery_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_flavor_profile(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM flavor_profiles WHERE whisky_id = ?", (whisky_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tasting_notes(self, whisky_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasting_notes WHERE whisky_id = ?", (whisky_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_price_history(self, whisky_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_history WHERE whisky_id = ?", (whisky_id,))
            return [dict(row) for row in cursor.fetchall()]

import os
import sqlite3
from typing import List, Dict, Any, Optional

class DbReadService:
    def __init__(self):
        # Default to output/import/production.db relative to the project root
        default_db = "output/import/production.db"
        env_db = os.getenv("MALT_RADAR_DB_PATH", default_db)
        
        # Resolve to absolute path if necessary
        if not os.path.isabs(env_db):
            # Assume project root is 3 levels up from this file (backend/app/services/db_read_service.py)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.db_path = os.path.abspath(os.path.join(base_dir, env_db))
        else:
            self.db_path = env_db

    def _get_connection(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Read-only explicitly
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_health(self) -> Dict[str, Any]:
        exists = os.path.exists(self.db_path)
        tables = ["distilleries", "whiskies", "tasting_notes", "flavor_profiles", "price_history"]
        counts = {}
        
        if exists:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    for t in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) as c FROM {t}")
                            counts[t] = cursor.fetchone()["c"]
                        except sqlite3.OperationalError:
                            counts[t] = 0
            except FileNotFoundError:
                exists = False
                
        return {
            "db_reachable": exists,
            "read_only": True,
            "counts": counts
        }

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: Optional[str] = None, distillery_id: Optional[str] = None) -> List[Dict[str, Any]]:
        limit = min(max(1, limit), 100)
        offset = max(0, offset)
        
        query = """
            SELECT w.*, d.name as distillery_name
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            WHERE 1=1
        """
        params = []
        
        if q and len(q.strip()) >= 2:
            query += " AND w.name LIKE ?"
            params.append(f"%{q.strip()}%")
            
        if distillery_id:
            query += " AND w.distillery_id = ?"
            params.append(distillery_id)
            
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_whisky(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT w.*, d.name as distillery_name
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            WHERE w.whisky_id = ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (whisky_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_distilleries(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        limit = min(max(1, limit), 100)
        offset = max(0, offset)
        
        query = """
            SELECT d.distillery_id, d.name, COUNT(w.whisky_id) as whisky_count
            FROM distilleries d
            LEFT JOIN whiskies w ON d.distillery_id = w.distillery_id
            GROUP BY d.distillery_id
            ORDER BY d.name ASC
            LIMIT ? OFFSET ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def search(self, q: str) -> List[Dict[str, Any]]:
        if not q or len(q.strip()) < 2:
            return []
            
        query = """
            SELECT w.*, d.name as distillery_name
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            WHERE w.name LIKE ? OR d.name LIKE ?
            LIMIT 50
        """
        term = f"%{q.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (term, term))
            return [dict(row) for row in cursor.fetchall()]

    def get_filters(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT distillery_id, name FROM distilleries ORDER BY name ASC")
            distilleries = [dict(row) for row in cursor.fetchall()]
            
            return {
                "distilleries": distilleries,
                "regions": "not_available",
                "countries": "not_available",
                "categories": "not_available"
            }

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

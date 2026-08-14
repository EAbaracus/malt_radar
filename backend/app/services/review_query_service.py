import os
from typing import List, Dict, Any

from app.utils.source_guard import SourceGuard
from app.db.production_read_adapter import ProductionReadAdapter  # Faz B: tek read seam
from app.db.review_action_writer import ReviewActionWriter  # Faz B: write ayrıldı
from app.utils.shared_paths import ALLOWED_TABLES as ALLOWED_TABLES_REVIEW  # review tabloları

class ReviewQueryService:
    # Class-level cache for table columns to avoid repeated PRAGMA queries
    # Format: { db_path: { table_name: [columns] } }
    _schema_cache: Dict[str, Dict[str, List[str]]] = {}

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv("MALT_RADAR_DB_PATH", "output/import/production.db")
        self._write_path = db_path  # ReviewActionWriter (write) bu path'i kullanır
        self._adapter = ProductionReadAdapter(db_path=db_path)  # Faz B: tek read seam
        self._writer = ReviewActionWriter(db_path=db_path)  # Faz B: write ayrıldı

    def _get_connection(self):
        """Faz B — okuma adapter'a delege. Bu metod kalıcı mıdır? (legacy read)
        DbReadService de aynı pattern'i izler; bir sonraki turda kaldırılabilir.
        """
        raise DeprecationWarning("Faz B: read okunuyor, bu metod kullanımdan kalkıyor.")

    def get_unified_queue(self, status: str = None, source_table: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return self._adapter.get_unified_queue(status=status, source_table=source_table, limit=limit, offset=offset)

    def get_item_details(self, source_table: str, source_record_key: str) -> Dict[str, Any]:
        """Admin review read — source fields retained (is_manual=True)."""
        safe_table = ALLOWED_TABLES_REVIEW.get(source_table)
        if not safe_table:
            return None
        key_col = "queue_id" if safe_table == "staging_manual_review_queue" else "source_record_key"
        with self._adapter._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({safe_table})")
            cols = [r["name"] for r in cursor.fetchall()]
            if key_col not in cols:
                return None
            cursor.execute(f"SELECT * FROM {safe_table} WHERE {key_col} = ?", (source_record_key,))
            row = cursor.fetchone()
        if row:
            item = {k: str(row[k]) if row[k] is not None else "" for k in row.keys()}
            return SourceGuard.sanitize_response(item, is_manual=True)
        return None

    def get_allowed_actions(self, current_status: str) -> List[Dict[str, Any]]:
        return self._adapter.query("review_status_transitions", where="from_status = ? AND allowed = 1", params=(current_status,), select="from_status, to_status, action_type, requires_note, allowed")

    def execute_action(self, source_table: str, source_record_key: str, target_status: str, action_type: str, reviewer: str, reviewer_note: str, previous_status: str):
        """Faz B — write ReviewActionWriter'a delegate (guard-backed, G2 SHA audit)."""
        return self._writer.execute_action(
            source_table=source_table,
            source_record_key=source_record_key,
            target_status=target_status,
            action_type=action_type,
            reviewer=reviewer,
            reviewer_note=reviewer_note,
            previous_status=previous_status,
        )

import sqlite3
import os
import logging
from typing import List, Dict, Any

class ReviewQueryService:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv("MALT_RADAR_DB_PATH", "output/import/production.db")
        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            abs_db_path = os.path.abspath(os.path.join(base_dir, db_path))
        else:
            abs_db_path = db_path
            
        self._write_path = abs_db_path
        self.db_path = f"file:{abs_db_path}?mode=ro"
        
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, uri=True)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def get_unified_queue(self, status: str = None, source_table: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Whitelist tables
        tables = [
            'staging_new_products', 'staging_tasting_notes', 'staging_historical_menu_prices', 
            'staging_manual_review_queue', 'knowledge_regions', 'knowledge_glossary_terms', 'knowledge_guides'
        ]
        
        selects = []
        for t in tables:
            try:
                cursor.execute(f"PRAGMA table_info({t})")
                cols = [row['name'] for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                continue
            if not cols:
                continue
                
            c_key = "candidate_name" if t == 'staging_manual_review_queue' else "source_record_key"
            c_key = c_key if c_key in cols else "''"
            
            c_disp = "''"
            for n in ['name', 'title', 'candidate_name', 'term', 'whisky_name']:
                if n in cols:
                    c_disp = n; break
                    
            c_src = "source_name" if "source_name" in cols else ("source" if "source" in cols else "'unknown'")
            c_app = "approval_status" if "approval_status" in cols else "'pending_review'"
            c_ded = "dedupe_action" if "dedupe_action" in cols else "''"
            c_rec = "import_recommendation" if "import_recommendation" in cols else "''"
            c_cre = "original_row_index" if "original_row_index" in cols else "'0'"
            c_con = "'1'" if t == 'staging_manual_review_queue' else "'0'"
            
            q = f"SELECT '{t}' as source_table, CAST({c_key} AS TEXT) as source_record_key, CAST({c_disp} AS TEXT) as display_name, CAST({c_src} AS TEXT) as source_name, CAST({c_app} AS TEXT) as approval_status, CAST({c_ded} AS TEXT) as dedupe_action, CAST({c_rec} AS TEXT) as import_recommendation, CAST({c_cre} AS TEXT) as created_at, 0 as review_priority, CAST({c_con} AS TEXT) as conflict_flag FROM {t}"
            selects.append(q)
            
        union_q = " UNION ALL ".join(selects)
        
        where_clauses = []
        params = []
        
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

        # Parameterize limit and offset to prevent SQL injection
        final_q += " LIMIT ? OFFSET ?"
        params.extend([safe_limit, safe_offset])
        
        try:
            cursor.execute(final_q, params)
            rows = [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.warning(f"Database query error in get_unified_queue: {e}")
            rows = []
        finally:
            conn.close()
            
        return rows

    def get_item_details(self, source_table: str, source_record_key: str) -> Dict[str, Any]:
        ALLOWED_TABLES = {
            'staging_new_products': 'staging_new_products', 
            'staging_tasting_notes': 'staging_tasting_notes', 
            'staging_historical_menu_prices': 'staging_historical_menu_prices', 
            'staging_manual_review_queue': 'staging_manual_review_queue', 
            'knowledge_regions': 'knowledge_regions', 
            'knowledge_glossary_terms': 'knowledge_glossary_terms', 
            'knowledge_guides': 'knowledge_guides'
        }
        safe_table = ALLOWED_TABLES.get(source_table)
        if not safe_table:
            return None
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check column using safe_table
        cursor.execute(f"PRAGMA table_info({safe_table})")
        cols = [r['name'] for r in cursor.fetchall()]
        key_col = "queue_id" if safe_table == 'staging_manual_review_queue' else "source_record_key"
        if key_col not in cols:
            conn.close()
            return None
            
        cursor.execute(f"SELECT * FROM {safe_table} WHERE {key_col} = ?", (source_record_key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Convert all to strings for simple dict
            return {k: str(row[k]) if row[k] is not None else "" for k in row.keys()}
        return None

    def get_allowed_actions(self, current_status: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT from_status, to_status, action_type, requires_note, allowed FROM review_status_transitions WHERE from_status = ? AND allowed = 1", (current_status,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def execute_action(self, source_table: str, source_record_key: str, target_status: str, action_type: str, reviewer: str, reviewer_note: str, previous_status: str):
        ALLOWED_TABLES = {
            'staging_new_products': 'staging_new_products', 
            'staging_tasting_notes': 'staging_tasting_notes', 
            'staging_historical_menu_prices': 'staging_historical_menu_prices', 
            'staging_manual_review_queue': 'staging_manual_review_queue', 
            'knowledge_regions': 'knowledge_regions', 
            'knowledge_glossary_terms': 'knowledge_glossary_terms', 
            'knowledge_guides': 'knowledge_guides'
        }
        safe_table = ALLOWED_TABLES.get(source_table)
        if not safe_table:
            raise Exception("Invalid source table")

        # We must open a writeable connection for this
        conn = sqlite3.connect(self._write_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()
            # Update staging table using safe_table
            key_col = "queue_id" if safe_table == 'staging_manual_review_queue' else "source_record_key"
            cur.execute(f"UPDATE {safe_table} SET approval_status = ? WHERE {key_col} = ?", (target_status, source_record_key))
            
            # Insert log
            cur.execute("""
                INSERT INTO review_actions 
                (source_table, source_record_key, review_status, action_type, reviewer, reviewer_note, previous_status, new_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (source_table, str(source_record_key), target_status, action_type, reviewer, reviewer_note, previous_status, target_status))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise Exception(f"Database write failed: {e}")
        finally:
            conn.close()

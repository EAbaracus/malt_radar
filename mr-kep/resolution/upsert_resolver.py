import json
import logging
import sqlite3
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class UpsertResolver:
    """
    P91.2 Incremental UPSERT Resolution Engine
    Takes fully resolved canonical records and safely merges/upserts them into 
    a target staging database, rather than dropping and recreating tables.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def upsert_whisky(self, whisky_record: Dict[str, Any]):
        """
        Upserts a whisky into the 'whiskies' table using SQL ON CONFLICT rules.
        Assuming whisky_id is the Primary Key.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Prepare standard fields based on schema mapping
            wid = whisky_record.get('gsd_candidate_id')
            name = whisky_record.get('name')
            country = whisky_record.get('country')
            region = whisky_record.get('region')
            abv = whisky_record.get('abv')
            age_stmt = whisky_record.get('age_statement')
            cask = whisky_record.get('cask_type')
            
            # Using SQLite UPSERT (ON CONFLICT DO UPDATE)
            cursor.execute("""
                INSERT INTO whiskies (whisky_id, name, country, region, data_confidence, abv, age_statement, cask_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(whisky_id) DO UPDATE SET
                    name=excluded.name,
                    country=excluded.country,
                    region=excluded.region,
                    data_confidence=excluded.data_confidence,
                    abv=excluded.abv,
                    age_statement=excluded.age_statement,
                    cask_type=excluded.cask_type
            """, (wid, name, country, region, 'certified', abv, age_stmt, cask))
            
            conn.commit()
            logger.info(f"Successfully UPSERTED whisky {wid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert whisky {whisky_record.get('gsd_candidate_id')}: {e}")
            raise e
        finally:
            conn.close()

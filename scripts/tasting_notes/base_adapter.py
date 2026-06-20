import time
import sqlite3
import requests
import logging
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BaseAdapter(ABC):
    def __init__(self, db_path='output/import/production.db', request_delay=1.0):
        self.db_path = db_path
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        
    def fetch_html(self, url, timeout=10):
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    @abstractmethod
    def parse(self, url, html):
        """
        Parse HTML and return a dictionary with tasting note fields.
        Must return a dict with:
        - product_name
        - nose
        - palate
        - finish
        - conclusion (optional)
        - source_verified (0 or 1)
        """
        pass

    def run(self, url):
        logging.info(f"Scraping: {url}")
        html = self.fetch_html(url)
        if not html:
            return 'ERROR'
            
        try:
            data = self.parse(url, html)
            if data:
                # Check if it has any actual tasting notes
                has_notes = bool(data.get('nose') or data.get('palate') or data.get('finish') or data.get('conclusion'))
                if not has_notes:
                    logging.warning(f"No tasting notes extracted for {url}")
                    return 'PARSE_EMPTY'
                return self.save_to_db(url, data)
            else:
                logging.warning(f"No data parsed for {url}")
                return 'PARSE_EMPTY'
        except Exception as e:
            logging.error(f"Error parsing {url}: {e}")
            return 'ERROR'

    def save_to_db(self, url, data):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for duplicate source_url
            cursor.execute("SELECT COUNT(*) FROM staging_tasting_notes WHERE source_url = ?", (url,))
            if cursor.fetchone()[0] > 0:
                logging.info(f"Skipping duplicate source_url: {url}")
                return 'DUPLICATE'
                
            # Truncate raw text to prevent huge inputs
            def truncate(text, max_len=2000):
                if text:
                    return text[:max_len]
                return text

            cursor.execute("""
                INSERT INTO staging_tasting_notes (
                    source_system,
                    product_name,
                    source_url,
                    nose,
                    palate,
                    finish,
                    conclusion,
                    source_verified,
                    match_status,
                    approval_status,
                    import_recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.__class__.__name__,
                truncate(data.get('product_name')),
                url,
                truncate(data.get('nose')),
                truncate(data.get('palate')),
                truncate(data.get('finish')),
                truncate(data.get('conclusion')),
                data.get('source_verified', 0),
                'unmatched',
                'pending',
                'review_before_import'
            ))
            conn.commit()
            logging.info(f"Successfully inserted note for {data.get('product_name')} from {url}")
            return 'SUCCESS'
        except Exception as e:
            logging.error(f"DB Error for {url}: {e}")
            if conn:
                conn.rollback()
            return 'ERROR'
        finally:
            if conn:
                conn.close()

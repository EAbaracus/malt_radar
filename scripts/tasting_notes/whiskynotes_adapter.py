from bs4 import BeautifulSoup
from scripts.tasting_notes.base_adapter import BaseAdapter
from scripts.tasting_notes.note_parser import extract_tasting_notes, normalize_palate
import re

class WhiskyNotesAdapter(BaseAdapter):
    def parse(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        
        # product_name
        title_elem = soup.find('h1', class_='entry-title')
        product_name = title_elem.text.strip() if title_elem else 'Unknown Product'
        
        # WhiskyNotes puts notes in standard paragraphs in entry-content
        content_div = soup.find('div', class_='entry-content')
        text = content_div.get_text(separator='\n', strip=True) if content_div else ''
        
        # Pre-process text to normalize 'Mouth' to 'Palate'
        text = normalize_palate(text)
        
        notes = extract_tasting_notes(text)
        notes['product_name'] = product_name
        notes['source_verified'] = 1
        
        # Score is often at the end or in a specific element
        score_match = re.search(r'(?i)Score:\s*(<strong[^>]*>)?\s*(\d{2,3}(?:/\d{2,3})?)', html)
        if score_match:
             # Just extraction, though we don't save score in tasting notes table.
             pass

        return notes

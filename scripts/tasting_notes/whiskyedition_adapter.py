from bs4 import BeautifulSoup
from scripts.tasting_notes.base_adapter import BaseAdapter
from scripts.tasting_notes.note_parser import extract_tasting_notes

class WhiskyEditionAdapter(BaseAdapter):
    def parse(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        
        title_elem = soup.find('h1')
        product_name = title_elem.text.strip() if title_elem else 'Unknown Product'
        
        # Similar logic to general extraction
        content = soup.find('div', class_='entry-content') or soup
        text = content.get_text(separator='\n', strip=True)
        
        notes = extract_tasting_notes(text)
        notes['product_name'] = product_name
        notes['source_verified'] = 1
        
        return notes

from bs4 import BeautifulSoup
from scripts.tasting_notes.base_adapter import BaseAdapter
import re

class MasterOfMaltAdapter(BaseAdapter):
    def parse(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        
        # product_name
        title_elem = soup.find('h1')
        product_name = title_elem.text.strip() if title_elem else 'Unknown Product'
        
        notes = {
            'product_name': product_name,
            'nose': None,
            'palate': None,
            'finish': None,
            'source_verified': 1
        }
        
        # Tasting notes usually under an element with id="TastingNoteUI" or similar, or just paragraphs with bold Nose:
        tasting_note_div = soup.find(id='ContentPlaceHolder1_ctl00_ctl02_TastingNote')
        if not tasting_note_div:
            # Fallback
            tasting_note_div = soup.find('div', class_='product-description')
            
        # We will try to parse the entire visible text first
        text = soup.get_text(separator='\n', strip=True)
        from scripts.tasting_notes.note_parser import extract_tasting_notes
        extracted = extract_tasting_notes(text)
        
        # Next.js sites often hide data in scripts. Let's do a raw regex on html if extracted is empty
        if not extracted['nose'] and not extracted['palate'] and not extracted['finish']:
            # Replace escaped quotes or unicode so regex works better
            clean_html = html.replace('\\u003C', '<').replace('\\u003E', '>').replace('\\"', '"')
            extracted = extract_tasting_notes(clean_html)
            
        if extracted['nose'] or extracted['palate'] or extracted['finish']:
            notes['nose'] = extracted['nose']
            notes['palate'] = extracted['palate']
            notes['finish'] = extracted['finish']

        return notes


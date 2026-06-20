from bs4 import BeautifulSoup
from scripts.tasting_notes.base_adapter import BaseAdapter
from scripts.tasting_notes.note_parser import extract_tasting_notes

class WhiskybaseAdapter(BaseAdapter):
    def parse(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        
        title_elem = soup.find('h1')
        if title_elem:
            # Usually format is "Distillery Name Product Name"
            product_name = title_elem.text.strip()
            # Clean up excessive whitespace
            product_name = ' '.join(product_name.split())
        else:
            product_name = 'Unknown Product'
            
        # Whiskybase has user notes block: id="wb-tastingnotes"
        notes_div = soup.find(id='wb-tastingnotes')
        
        notes = {
            'product_name': product_name,
            'nose': None,
            'palate': None,
            'finish': None,
            'source_verified': 0 # Crowd-sourced
        }
        
        if notes_div:
            # We will just grab the first available well-formatted note
            text = notes_div.get_text(separator='\n', strip=True)
            extracted = extract_tasting_notes(text)
            
            # If we found at least something
            if extracted['nose'] or extracted['palate'] or extracted['finish']:
                notes['nose'] = extracted['nose']
                notes['palate'] = extracted['palate']
                notes['finish'] = extracted['finish']
            else:
                # Fallback: maybe they just wrote text without labels
                # We can't cleanly separate nose/palate/finish, so we might store as conclusion
                notes['conclusion'] = text[:1000]

        return notes

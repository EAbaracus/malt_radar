import re

def normalize_palate(text):
    if not text:
        return text
    # Convert 'mouth' to 'palate' if it's acting as a label.
    text = re.sub(r'(?i)\bmouth\b', 'palate', text)
    return text.strip()

def extract_tasting_notes(text):
    """
    Generic tasting note extractor from a block of text.
    Returns a dict with 'nose', 'palate', 'finish', 'conclusion'.
    """
    notes = {
        'nose': None,
        'palate': None,
        'finish': None,
        'conclusion': None
    }
    
    # We will build simple regex to find sections. This assumes standard format "Nose: ... Palate: ... Finish: ..."
    # Many sites use strong/b tags or simple text colons.
    
    # More robust logic to find headers with or without colons, considering newlines
    patterns = {
        'nose': r'(?im)^(?:nose|aroma)s?\s*[:\-]?\s*(.*?)(?=^(?:palate|mouth|taste|finish|conclusion)s?\s*[:\-]?|\Z)',
        'palate': r'(?im)^(?:palate|mouth|taste)s?\s*[:\-]?\s*(.*?)(?=^(?:nose|aroma|finish|conclusion)s?\s*[:\-]?|\Z)',
        'finish': r'(?im)^(?:finish)es?\s*[:\-]?\s*(.*?)(?=^(?:nose|aroma|palate|mouth|taste|conclusion)s?\s*[:\-]?|\Z)',
        'conclusion': r'(?im)^(?:conclusion|overall)\s*[:\-]?\s*(.*?)(?=^(?:nose|aroma|palate|mouth|taste|finish)s?\s*[:\-]?|\Z)'
    }
    
    # Try line-based regex first
    found_any = False
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            extracted = re.sub(r'<[^>]+>', '', extracted).strip()
            if extracted:
                notes[key] = extracted
                found_any = True
                
    if not found_any:
        # Fallback to inline colon-based regex (original)
        inline_patterns = {
            'nose': r'(?i)(?:nose|aroma)s?\s*:\s*(.*?)(?=(?:palate|mouth|taste|finish|conclusion)\s*:|$)',
            'palate': r'(?i)(?:palate|mouth|taste)s?\s*:\s*(.*?)(?=(?:nose|aroma|finish|conclusion)\s*:|$)',
            'finish': r'(?i)(?:finish)es?\s*:\s*(.*?)(?=(?:nose|aroma|palate|mouth|taste|conclusion)\s*:|$)',
            'conclusion': r'(?i)(?:conclusion|overall)\s*:\s*(.*?)(?=(?:nose|aroma|palate|mouth|taste|finish)\s*:|$)'
        }
        for key, pattern in inline_patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                extracted = re.sub(r'<[^>]+>', '', extracted).strip()
                if extracted:
                    notes[key] = extracted
                
    return notes

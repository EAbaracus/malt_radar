import difflib

class NERResolver:
    def __init__(self, lexicon):
        self.lexicon = lexicon
        
    def resolve(self, entity_key):
        k = entity_key.lower().strip()
        
        # 1. Exact Match
        if k in self.lexicon:
            return self.lexicon[k], "exact_match"
            
        # 2. Fuzzy Match (simple containment or difflib)
        matches = difflib.get_close_matches(k, self.lexicon.keys(), n=1, cutoff=0.85)
        if matches:
            return self.lexicon[matches[0]], "fuzzy_match"
            
        return None, "unresolved"

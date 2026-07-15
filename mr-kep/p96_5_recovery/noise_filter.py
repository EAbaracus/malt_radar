class NoiseFilter:
    def __init__(self):
        self.noise_words = {
            "flavor", "quality", "whiskiesrated", "power", "highproof", "taste", "finish", 
            "nose", "palate", "color", "colour", "index", "contents", "introduction",
            "at the peak of", "whisky", "distillery", "cask"
        }
        
    def is_noise(self, text):
        t = text.lower().strip()
        if len(t) < 4: return True
        if t in self.noise_words: return True
        # Simple heuristic for OCR noise (too many non-alphas)
        non_alpha = sum(1 for c in t if not c.isalpha() and not c.isspace())
        if len(t) > 0 and (non_alpha / len(t)) > 0.3: return True
        return False

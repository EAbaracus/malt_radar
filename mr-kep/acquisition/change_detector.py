import hashlib

class ChangeDetector:
    def __init__(self):
        self.history = {}
        
    def compute_hash(self, content):
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
        
    def is_changed(self, url, content):
        h = self.compute_hash(content)
        if url in self.history and self.history[url] == h:
            return False
        self.history[url] = h
        return True

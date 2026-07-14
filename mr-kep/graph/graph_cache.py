import json
class GraphCache:
    def __init__(self):
        self.resolutions = {}
        
    def get_resolution(self, raw_name):
        return self.resolutions.get(raw_name)
        
    def set_resolution(self, raw_name, canonical_id):
        self.resolutions[raw_name] = canonical_id

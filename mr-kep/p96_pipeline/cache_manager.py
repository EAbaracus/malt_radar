import hashlib

class CacheManager:
    def __init__(self):
        self.cache = {}
        
    def get_key(self, doc_hash, chunk_hash, prompt_v, schema_v, model_id):
        raw = f"{doc_hash}_{chunk_hash}_{prompt_v}_{schema_v}_{model_id}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

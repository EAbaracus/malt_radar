class EntityResolver:
    def __init__(self, deduplicator, cache, fusion):
        self.deduplicator = deduplicator
        self.cache = cache
        self.fusion = fusion
        
    def resolve(self, new_entity):
        # 1. Check cache
        cached_id = self.cache.get_resolution(new_entity["name"])
        if cached_id:
            return cached_id, True # returned from cache
            
        # 2. Check deduplicator
        dup = self.deduplicator.check_duplicate(new_entity)
        if dup:
            target_id = dup["merge_recommendation"]
            self.fusion.merge_evidence(target_id, new_entity)
            self.cache.set_resolution(new_entity["name"], target_id)
            return target_id, False
            
        # 3. New entity
        return new_entity["entity_id"], False

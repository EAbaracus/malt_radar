import time

class RateLimiter:
    def __init__(self, registry):
        self.registry = registry
        self.last_requests = {}
        
    def can_request(self, source_id):
        # Mock logic
        now = time.time()
        if source_id in self.last_requests:
            if now - self.last_requests[source_id] < 1.0: # simplified 1s wait
                return False
        self.last_requests[source_id] = now
        return True

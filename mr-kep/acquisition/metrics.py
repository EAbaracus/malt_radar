import json
class Metrics:
    def __init__(self):
        self.stats = {
            "discovered_pages": 0,
            "changed_pages": 0,
            "skipped_pages": 0,
            "extracted_evidence": 0,
            "duplicate_evidence": 0,
            "cached_requests": 0,
            "token_savings": 0,
            "crawl_duration": 0,
            "review_queue_additions": 0
        }
    def record_skip(self, tokens_saved):
        self.stats["skipped_pages"] += 1
        self.stats["token_savings"] += tokens_saved
        self.stats["cached_requests"] += 1
    def save(self, file_path):
        with open(file_path, "w") as f:
            json.dump(self.stats, f, indent=2)

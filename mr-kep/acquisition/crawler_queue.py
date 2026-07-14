import json
import os
from datetime import datetime, timezone

class CrawlerQueue:
    def __init__(self, queue_file="crawl_queue.jsonl"):
        self.queue_file = queue_file
        
    def enqueue(self, source_id, url, priority=1):
        item = {
            "source_id": source_id,
            "url": url,
            "priority": priority,
            "state": "pending",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0
        }
        with open(self.queue_file, "a") as f:
            f.write(json.dumps(item) + "\n")
            
    def get_pending(self):
        items = []
        if os.path.exists(self.queue_file):
            with open(self.queue_file, "r") as f:
                for line in f:
                    data = json.loads(line)
                    if data["state"] == "pending":
                        items.append(data)
        return sorted(items, key=lambda x: x["priority"], reverse=True)

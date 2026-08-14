import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HumanReviewQueue:
    """
    P91.3 Human Review Queue
    A persistent file-backed queue (JSONL) where the Knowledge Acquisition Platform 
    can send ambiguous merge conflicts, structural schema mismatches, or low-confidence
    extractions for manual review by an admin or agent.
    """
    
    def __init__(self, queue_path: str = "output/human_review_queue.jsonl"):
        self.queue_path = queue_path
        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        
    def enqueue_conflict(self, entity_id: str, conflict_type: str, details: Dict[str, Any]):
        """
        Adds a conflict to the queue.
        conflict_type examples: 'schema_drift', 'low_confidence_merge', 'entity_duplication'
        """
        item = {
            "entity_id": entity_id,
            "conflict_type": conflict_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending_review"
        }
        
        with open(self.queue_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item) + "\n")
            
        logger.info(f"Enqueued {conflict_type} for {entity_id} to {self.queue_path}")
        
    def pop_pending_reviews(self, limit: int = 10) -> list:
        """
        Reads pending reviews from the queue (in a real system, would mark them as 'in_progress' in a DB).
        Here we just read the JSONL for reporting/CLI.
        """
        if not os.path.exists(self.queue_path):
            return []
            
        pending = []
        with open(self.queue_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                if item.get("status") == "pending_review":
                    pending.append(item)
                    if len(pending) >= limit:
                        break
        return pending

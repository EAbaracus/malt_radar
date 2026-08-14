import json
class GraphMetrics:
    def __init__(self):
        self.stats = {
            "total_nodes": 0,
            "total_edges": 0,
            "duplicates_resolved": 0,
            "tokens_saved": 0,
            "evidence_fusions": 0
        }
    def save(self, file_path):
        with open(file_path, "w") as f:
            json.dump(self.stats, f, indent=2)

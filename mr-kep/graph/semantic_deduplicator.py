class SemanticDeduplicator:
    def __init__(self, graph):
        self.graph = graph
        
    def calculate_duplicate_score(self, entity_a, entity_b):
        score = 0.0
        # Normalize names
        name_a = entity_a.get("name", "").lower().replace("years", "").replace("old", "").replace("yo", "").strip()
        name_b = entity_b.get("name", "").lower().replace("years", "").replace("old", "").replace("yo", "").strip()
        
        # Check alias equality logic (e.g. "ardbeg ten" vs "ardbeg 10")
        if name_a.replace("ten", "10") == name_b.replace("ten", "10"):
            score += 0.8
            
        if entity_a.get("abv") == entity_b.get("abv") and entity_a.get("abv") is not None:
            score += 0.2
            
        return score
        
    def check_duplicate(self, new_entity):
        for node_id, node in self.graph.nodes.items():
            if node["label"] == "Whisky":
                score = self.calculate_duplicate_score(new_entity, node["properties"])
                if score > 0.9:
                    return {"duplicate_score": score, "merge_recommendation": node_id, "confidence": score}
        return None

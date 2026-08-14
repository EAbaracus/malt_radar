class EvidenceFusion:
    def __init__(self, graph):
        self.graph = graph
        
    def merge_evidence(self, target_node_id, new_entity):
        target = self.graph.get_node(target_node_id)
        if "evidence" not in target["properties"]:
            target["properties"]["evidence"] = []
            
        new_ev = new_entity.get("evidence", [])
        for ev in new_ev:
            # check for exact duplicate evidence
            if not any(e["field_value"] == ev["field_value"] for e in target["properties"]["evidence"]):
                target["properties"]["evidence"].append(ev)

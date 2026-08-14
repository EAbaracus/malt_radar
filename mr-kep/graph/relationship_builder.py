class RelationshipBuilder:
    def __init__(self, graph):
        self.graph = graph
        
    def build_from_entity(self, entity):
        # e.g., create DISTILLERY node, BRAND node, and relationships
        node_id = entity["entity_id"]
        self.graph.add_node(node_id, "Whisky", entity)
        if "distillery" in entity:
            dist_id = f"DIST_{entity['distillery'].replace(' ', '_').upper()}"
            self.graph.add_node(dist_id, "Distillery", {"name": entity["distillery"]})
            self.graph.add_edge(node_id, dist_id, "DISTILLED_AT")

import json

class KnowledgeGraph:
    def __init__(self, db_path="graph_db.json"):
        self.db_path = db_path
        self.nodes = {}
        self.edges = []
        
    def add_node(self, node_id, label, properties):
        if node_id not in self.nodes:
            self.nodes[node_id] = {"label": label, "properties": properties}
        else:
            self.nodes[node_id]["properties"].update(properties)
            
    def add_edge(self, source_id, target_id, relation_type, properties=None):
        edge = {"source": source_id, "target": target_id, "type": relation_type, "properties": properties or {}}
        self.edges.append(edge)
        
    def get_node(self, node_id):
        return self.nodes.get(node_id)

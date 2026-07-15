import hashlib

class EvidenceGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        
    def add_node(self, node_id, n_type, data):
        self.nodes[node_id] = {"type": n_type, "data": data}
        
    def add_edge(self, src, dst, rel):
        self.edges.append({"source": src, "target": dst, "relationship": rel})

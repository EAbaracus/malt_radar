import json
import hashlib

def hash_id(*args):
    return hashlib.sha256("_".join(map(str, args)).encode('utf-8')).hexdigest()[:12]

class EvidenceGraphBuilder:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        
    def add_node(self, node_id, n_type, data):
        self.nodes[node_id] = {"type": n_type, "data": data}
        
    def add_edge(self, src, dst, rel):
        self.edges.append({"source": src, "target": dst, "relationship": rel})

def run_prototype():
    print("--- P96-R3 EVIDENCE GRAPH PROTOTYPE EXECUTION ---\\n")
    graph = EvidenceGraphBuilder()
    
    # 1. Base Nodes
    book_id = "BK_JACKSON_01"
    citation_id = "chunk999"
    graph.add_node(book_id, "Book", {"title": "Malt Whisky Companion"})
    graph.add_node(citation_id, "Citation", {"page": 142, "paragraph": 2})
    graph.add_edge(book_id, citation_id, "HAS_CITATION")
    
    # 2. Immutable Evidence Node
    evidence_id = "EV-" + hash_id(citation_id, "peat", "positive")
    evidence_data = {
        "evidence_id": evidence_id,
        "quoted_text": "intense medicinal peat",
        "extracted_value": {"descriptor": "Peat", "category": "Palate"},
        "extraction_confidence": 0.99,
        "authority_tier": "T3"
    }
    graph.add_node(evidence_id, "Evidence", evidence_data)
    graph.add_edge(citation_id, evidence_id, "PROVIDES_EVIDENCE")
    
    # 3. Extracted Fact Node
    fact_id = "FACT-" + hash_id("Peat", "Palate")
    graph.add_node(fact_id, "Extracted Fact", {"descriptor": "Peat", "intensity": 5})
    graph.add_edge(evidence_id, fact_id, "SUPPORTS_FACT")
    
    # 4. Consensus Node (Simulating a merge)
    consensus_id = "CONS-" + hash_id(fact_id)
    consensus_data = {
        "consensus_rationale": "Strong single-source agreement",
        "supporting_evidence": [evidence_id],
        "conflicting_evidence": [],
        "weighted_confidence": 0.99
    }
    graph.add_node(consensus_id, "Consensus", consensus_data)
    graph.add_edge(fact_id, consensus_id, "MERGED_INTO")
    
    # 5. Entity & Canonical Axis
    entity_id = "GSD-CAND-0082"
    graph.add_node(entity_id, "Whisky Entity", {"name": "Lagavulin 16"})
    graph.add_edge(consensus_id, entity_id, "APPLIES_TO")
    
    print(f"Graph Nodes Generated: {len(graph.nodes)}")
    print(f"Graph Edges Generated: {len(graph.edges)}\\n")
    
    # Explainability Trace
    print("--- EXPLAINABILITY TRACE FOR CONSENSUS ---")
    print(f"Querying Consensus Node: {consensus_id}")
    cons_node = graph.nodes[consensus_id]
    print(f"Rationale: {cons_node['data']['consensus_rationale']}")
    print(f"Supporting Evidence:")
    for ev_id in cons_node['data']['supporting_evidence']:
        ev_node = graph.nodes[ev_id]
        print(f"  -> Evidence ID: {ev_id}")
        print(f"  -> Quoted Text: '{ev_node['data']['quoted_text']}'")
        print(f"  -> Extraction Confidence: {ev_node['data']['extraction_confidence']}")
        print(f"  -> Authority Tier: {ev_node['data']['authority_tier']}")
    
    print("\\nPrototype deterministic graph execution complete.")

if __name__ == "__main__":
    run_prototype()

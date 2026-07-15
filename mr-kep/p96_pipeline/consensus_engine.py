class ConsensusEngine:
    def build_consensus(self, graph, entity_id, fact_id, evidence_id):
        consensus_id = f"CONS_{fact_id}"
        if consensus_id not in graph.nodes:
            graph.add_node(consensus_id, "Consensus", {
                "rationale": "High confidence single source extraction.",
                "supporting_evidence": [evidence_id],
                "conflicting_evidence": [],
                "weight": 0.95
            })
            graph.add_edge(fact_id, consensus_id, "MERGED_INTO")
            graph.add_edge(consensus_id, entity_id, "APPLIES_TO")
        return consensus_id

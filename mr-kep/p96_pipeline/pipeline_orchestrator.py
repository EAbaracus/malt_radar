import json, hashlib
from cache_manager import CacheManager
from chunking_engine import ChunkingEngine
from llm_extractor import LLMExtractor
from entity_resolver import EntityResolver
from evidence_graph import EvidenceGraph
from consensus_engine import ConsensusEngine

class Orchestrator:
    def __init__(self):
        self.cache = CacheManager()
        self.chunker = ChunkingEngine()
        self.extractor = LLMExtractor()
        self.resolver = EntityResolver()
        self.graph = EvidenceGraph()
        self.consensus = ConsensusEngine()
        
    def run(self, book_id, page_num, text):
        # A. Semantic Chunking
        chunk = self.chunker.generate_chunk(book_id, page_num, text)
        self.graph.add_node(book_id, "Book", {})
        self.graph.add_node(chunk["chunk_id"], "Citation", {"page": page_num})
        self.graph.add_edge(book_id, chunk["chunk_id"], "HAS_CITATION")
        
        # B. Cache Check
        c_key = self.cache.get_key(chunk["doc_hash"], chunk["chunk_id"], self.extractor.prompt_v, self.extractor.schema_v, self.extractor.model_id)
        
        # C. LLM Extraction
        extracted = self.extractor.extract(chunk)
        if not extracted: return
        
        # D. Entity Resolution
        resolved = self.resolver.resolve(extracted["whisky_name"])
        
        # E. Evidence Graph Generation
        ev_id = "EV_" + c_key
        self.graph.add_node(ev_id, "Evidence", {
            "quoted_text": chunk["text"],
            "extraction_confidence": 0.95,
            "authority_tier": "T3"
        })
        self.graph.add_edge(chunk["chunk_id"], ev_id, "PROVIDES_EVIDENCE")
        
        fact_data = extracted["descriptors"][0]
        fact_id = "FACT_" + hashlib.sha256(f"{fact_data['descriptor']}".encode()).hexdigest()[:8]
        self.graph.add_node(fact_id, "Extracted Fact", fact_data)
        self.graph.add_edge(ev_id, fact_id, "SUPPORTS_FACT")
        
        if resolved["entity_id"]:
            self.graph.add_node(resolved["entity_id"], "Whisky Entity", {"name": resolved["canonical_name"]})
            self.consensus.build_consensus(self.graph, resolved["entity_id"], fact_id, ev_id)

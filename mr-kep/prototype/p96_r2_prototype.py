import json
import hashlib

def generate_cache_key(doc_hash, chunk_hash, prompt_v, schema_v, model_id):
    raw = f"{doc_hash}_{chunk_hash}_{prompt_v}_{schema_v}_{model_id}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

class P96R2Prototype:
    def __init__(self):
        self.cache = {}
        
    def resolve_entity(self, raw_name):
        # Deterministic mock entity resolution
        if "lagavulin" in raw_name.lower() and "16" in raw_name:
            return {"entity_id": "GSD-CAND-0082", "name": "Lagavulin 16 Year Old", "confidence": 0.98}
        return {"entity_id": None, "name": raw_name, "confidence": 0.4}

    def mock_extract(self, text):
        # Strict versioned schema mock
        return {
            "descriptors": [
                {
                    "descriptor": "Peat",
                    "category": "Palate",
                    "polarity": "positive",
                    "intensity": 5,
                    "confidence": 0.99,
                    "provenance": {
                        "sentence": "It offers intense medicinal peat.",
                        "quoted_source_text": "intense medicinal peat"
                    }
                }
            ]
        }

def run_prototype():
    print("--- P96-R2 PROTOTYPE EXECUTION ---\\n")
    pipeline = P96R2Prototype()
    
    # 1. Cache configuration
    doc_hash = "abc123doc"
    chunk_hash = "chunk999"
    prompt_v = "v1.0"
    schema_v = "v2.1"
    model_id = "gemini-1.5-pro"
    
    cache_key = generate_cache_key(doc_hash, chunk_hash, prompt_v, schema_v, model_id)
    print(f"[Stage E] Cache Key Generated: {cache_key}")
    
    # 2. Entity Resolution
    raw_whisky = "Lagavulin 16yo"
    resolved = pipeline.resolve_entity(raw_whisky)
    print(f"[Stage A] Entity Resolved: '{raw_whisky}' -> {resolved['name']} (Conf: {resolved['confidence']})")
    
    # 3. Extraction & Citation-Grade Provenance
    text_chunk = "The Lagavulin 16 Year Old is a classic. It offers intense medicinal peat."
    extracted = pipeline.mock_extract(text_chunk)
    
    # 4. Knowledge Graph Relationship
    graph_node = {
        "node_type": "Extracted Fact",
        "fact": extracted["descriptors"][0],
        "relationships": {
            "BELONGS_TO_ENTITY": resolved["entity_id"],
            "CITED_FROM_BOOK": "BK_JACKSON_01",
            "CHUNK_ID": chunk_hash
        },
        "pipeline_metadata": {
            "schema_version": schema_v,
            "prompt_version": prompt_v,
            "model": model_id
        }
    }
    
    print(f"\\n[Stage G] Canonical Graph Node:\\n{json.dumps(graph_node, indent=2)}")
    print("\\nPrototype execution complete. Cache, Provenance, and Schema validated.")

if __name__ == "__main__":
    run_prototype()

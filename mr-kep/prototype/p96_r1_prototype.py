import json
import hashlib

def generate_chunk_id(book_id, page_num, text_chunk):
    return hashlib.sha256(f"{book_id}_{page_num}_{text_chunk}".encode('utf-8')).hexdigest()[:12]

class MockLLMExtractor:
    def extract(self, text_chunk):
        # In a real implementation, this calls an LLM with a strict JSON schema.
        # Here we return deterministic mock data based on the text.
        if "Lagavulin 16" in text_chunk:
            return {
                "whisky_identity": "Lagavulin 16 Year Old",
                "distillery": "Lagavulin",
                "abv": 43.0,
                "descriptors": {
                    "peat": ["intense", "medicinal"],
                    "smoke": ["bonfire"],
                    "maritime": ["iodine", "seaweed"]
                },
                "confidence": 0.95
            }
        return None

def run_prototype():
    print("--- P96-R1 PROTOTYPE EXECUTION ---")
    
    book_metadata = {"book_id": "BK_JACKSON_01", "title": "Malt Whisky Companion"}
    raw_page_text = "The Lagavulin 16 Year Old is a classic. Bottled at 43%, it offers intense medicinal peat and bonfire smoke, with distinct iodine and seaweed maritime notes."
    
    # Stage B: Semantic Chunking
    chunk_id = generate_chunk_id(book_metadata['book_id'], 142, raw_page_text)
    print(f"[Stage B] Generated Chunk ID: {chunk_id}")
    
    # Stage C: LLM Extraction
    extractor = MockLLMExtractor()
    extracted_json = extractor.extract(raw_page_text)
    print(f"[Stage C] Extracted Knowledge: {json.dumps(extracted_json, indent=2)}")
    
    # Stage D: Provenance Model
    provenance_fact = {
        "fact_type": "sensory_profile",
        "value": extracted_json["descriptors"],
        "provenance": {
            "book_id": book_metadata['book_id'],
            "page": 142,
            "chunk_id": chunk_id,
            "source_text": raw_page_text,
            "extraction_confidence": extracted_json["confidence"]
        }
    }
    
    print(f"\\n[Stage D] Provenance Object Created:\\n{json.dumps(provenance_fact, indent=2)}")
    print("\\nPrototype deterministic execution complete. No production mutation occurred.")

if __name__ == "__main__":
    run_prototype()

class LLMExtractor:
    def __init__(self):
        self.prompt_v = "v1.0"
        self.schema_v = "v2.1"
        self.model_id = "gemini-1.5-pro"
        
    def extract(self, chunk):
        # Mocking LLM extraction
        if "Springbank" in chunk["text"]:
            return {
                "whisky_name": "Springbank 10",
                "descriptors": [
                    {"descriptor": "Smoke", "category": "Palate", "polarity": "positive", "intensity": 4, "confidence": 0.95}
                ]
            }
        return None

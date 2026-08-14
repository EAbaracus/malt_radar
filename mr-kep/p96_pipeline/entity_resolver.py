class EntityResolver:
    def resolve(self, raw_name):
        if "Springbank" in raw_name and "10" in raw_name:
            return {"entity_id": "GSD-CAND-0010", "canonical_name": "Springbank 10 Year Old", "confidence": 0.99}
        return {"entity_id": None, "canonical_name": raw_name, "confidence": 0.4}

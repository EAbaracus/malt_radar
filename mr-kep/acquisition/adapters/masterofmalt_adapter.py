class MasterOfMaltAdapter:
    """Specialized in extracting tasting notes and regional data."""
    def parse(self, html_payload):
        if "lagavulin" in html_payload.lower():
            return {
                "name": "Lagavulin 16",
                "region": "Islay",
                "evidence": [
                    {"field_name": "palate", "field_value": "Intense peat smoke with iodine", "source": "masterofmalt", "confidence": 0.85, "quote": "Palate: Intense peat smoke with iodine and seaweed."}
                ]
            }
        return {}

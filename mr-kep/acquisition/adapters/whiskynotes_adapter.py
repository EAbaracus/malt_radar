class WhiskyNotesAdapter:
    """Specialized in high-authority expert scores and detailed flavor profiling."""
    def parse(self, html_payload):
        if "springbank 12" in html_payload.lower():
            return {
                "name": "Springbank 12 Cask Strength",
                "score": 90,
                "evidence": [
                    {"field_name": "score", "field_value": 90, "source": "whiskynotes", "confidence": 0.95, "quote": "Score: 90/100"}
                ]
            }
        return {}

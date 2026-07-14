class WhiskybaseAdapter:
    """Specialized in extracting official specs: ABV, cask details, maturation, release year."""
    def parse(self, html_payload):
        # Mock logic
        if "springbank 12" in html_payload.lower():
            return {
                "name": "Springbank 12 Cask Strength",
                "abv": 54.1,
                "cask_type": "Bourbon & Sherry",
                "release_year": 2023,
                "evidence": [
                    {"field_name": "abv", "field_value": 54.1, "source": "whiskybase", "confidence": 1.0, "quote": "Strength: 54.1 % Vol."},
                    {"field_name": "cask_type", "field_value": "Bourbon & Sherry", "source": "whiskybase", "confidence": 1.0, "quote": "Casktype: Bourbon/Sherry"}
                ]
            }
        return {}

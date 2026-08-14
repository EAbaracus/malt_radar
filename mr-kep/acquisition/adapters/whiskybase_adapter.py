"""
Whiskybase adapter — parses Hound MCP markdown output into structured evidence.

Hound's mcp_smart_fetch returns clean markdown of the page. Whiskybase pages
follow a consistent structure with labeled spec fields.
"""

import re
from typing import Any, Dict, List, Optional


class WhiskybaseAdapter:
    """Extract official specs from Whiskybase whisky pages."""

    # Field extraction patterns — match common Whiskybase labels
    PATTERNS = {
        "abv": [
            r"Strength[:\s]+([\d.]+)\s*[%]",
            r"ABV[:\s]+([\d.]+)\s*[%]",
            r"Alcohol[:\s]+([\d.]+)\s*[%]",
        ],
        "age_statement": [
            r"Age[:\s]+(\d+)\s*(?:year|yr)",
            r"(\d+)\s*(?:year|yr)\s*old",
        ],
        "cask_type": [
            r"Cask[:\s]+([^\n]+)",
            r"Cask\s*type[:\s]+([^\n]+)",
            r"Maturation[:\s]+([^\n]+)",
        ],
        "region": [
            r"Region[:\s]+([^\n]+)",
            r"Origin[:\s]+([^\n]+)",
        ],
        "country": [
            r"Country[:\s]+([^\n]+)",
        ],
        "distillery_name": [
            r"Distillery[:\s]+([^\n]+)",
        ],
        "bottler": [
            r"Bottler[:\s]+([^\n]+)",
        ],
        "bottling_series": [
            r"Series[:\s]+([^\n]+)",
        ],
        "release_year": [
            r"Released[:\s]+(\d{4})",
            r"Release\s*year[:\s]+(\d{4})",
        ],
        "bottle_size": [
            r"Bottle\s*size[:\s]+([\d.]+)\s*(?:cl|ml|l)",
        ],
    }

    def parse(self, markdown: str) -> Dict[str, Any]:
        """Parse Whiskybase markdown into structured evidence dict.

        Returns dict with keys:
          - name: whisky name (from H1 or title)
          - evidence: list of {field_name, field_value, source, confidence, quote}
        """
        if not markdown:
            return {}

        evidence: List[Dict[str, Any]] = []

        # Extract whisky name from first heading
        name_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else "unknown"

        # Extract key specs
        for field, patterns in self.PATTERNS.items():
            value = self._extract_first(markdown, patterns)
            if value is not None:
                evidence.append(
                    {
                        "field_name": field,
                        "field_value": value,
                        "source": "whiskybase",
                        "confidence": 0.95,
                        "quote": f"{field}: {value}",
                    }
                )

        return {"name": name, "evidence": evidence}

    @staticmethod
    def _extract_first(text: str, patterns: List[str]) -> Optional[str]:
        """Return first non-None capture group match."""
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                # Return first capture group if exists, else full match
                return m.group(1) if m.lastindex else m.group(0)
        return None


# Module-level helper for quick testing
if __name__ == "__main__":
    import sys

    with open(sys.argv[1], "r") as f:
        md = f.read()
    ad = WhiskybaseAdapter()
    result = ad.parse(md)
    import json

    print(json.dumps(result, indent=2, ensure_ascii=False))
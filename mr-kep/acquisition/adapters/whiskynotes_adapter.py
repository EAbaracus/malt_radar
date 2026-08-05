"""WhiskyNotes acquisition adapter — real review → 7-axis + score extraction.

Input : markdown produced by Hound mcp_smart_fetch (or any markdown
        page text from whiskynotes.com).
Output: {name: str, evidence: [ {field_name, field_value, source,
                                confidence, quote}, ... ]}

Canonical 7-axis contract (domain_adapter.CANONICAL_AXES):
    smoky, peaty, fruity, sweet, spicy, maritime, sherry
All flavor axis values are normalized to [0.0, 1.0].

Design rules (P96 completion):
- REAL parse: no hardcoded brand/dummy fallbacks.
- Deterministic: same markdown in -> same evidence out.
- Raw review prose is NEVER emitted; only mapped axis values plus
  short verbatim quote excerpts (provenance, not raw dump).
- Score (0-100, T2 expert) is extracted when present and carried
  as a separate `score` field (field_rules.yaml: scored_assessment).
- Malformed / empty / no-tasting input -> {} (explicit, not silent fake).
- Reuses FlavorMapper as the single authoritative descriptor->axis lexicon.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from d4_reducer.flavor_mapper import FlavorMapper
except ImportError:  # pragma: no cover - defensive import shim
    import sys
    from pathlib import Path
    _root = Path(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from d4_reducer.flavor_mapper import FlavorMapper

_MAPPER = FlavorMapper()

# Canonical 7-axis (mirror of domain_adapter.CANONICAL_AXES)
CANONICAL_AXES = _MAPPER.CANONICAL_AXES

# Intensity model (deterministic, [0,1]):
#   base 0.40 + 0.15 per mapped descriptor on that axis, clamped to 1.0.
_AXIS_BASE = 0.40
_AXIS_PER_DESCRIPTOR = 0.15
_CONF_BASE = 0.60
_CONF_PER_DESCRIPTOR = 0.10

# Real section headings that OPEN a tasting block. NOTE: 'nose:'/
# 'palate:'/'finish:' are PROSE lines (they carry the actual notes),
# NOT section headings — so they must NOT be treated as section breaks.
_TASTING_SECTION_RE = re.compile(
    r"(?:^|\n)#?\s*(?:tasting\s*notes?|the\s*spirit|taste\s*notes?|"
    r"flavour|flavor|notes?)\b",
    re.IGNORECASE,
)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN_SPLIT = re.compile(r"[^a-zA-Z'+-]+")
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "from", "by", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "not", "no", "very", "some", "this", "that",
    "these", "those", "it", "its", "all", "each", "long", "short", "more",
    "most", "less", "much", "many", "you", "your", "our", "we", "they",
    "their", "there", "here", "what", "which", "who", "how", "why",
})
_AMBIGUOUS = frozenset({
    "rich", "complex", "smooth", "balanced", "intense", "nice", "good",
    "great", "excellent", "fine", "mellow", "soft", "bold", "big",
    "classic", "wonderful", "lovely", "delicious", "rounded",
})
_SCORE_RE = re.compile(r"score\s*[:\-]?\s*(\d{1,3})\s*(?:/\s*100)?", re.IGNORECASE)


def _extract_name(markdown: str) -> str:
    """Pull the whisky name from the first markdown heading or title."""
    m = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^title:\s*(.+)$", markdown, re.MULTILINE | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return "unknown"


def _collect_tasting_prose(markdown: str) -> str:
    """Extract tasting-related prose blocks from the markdown.

    Heuristic: take any line/paragraph that follows a tasting-section
    heading, plus any standalone sentence containing a known flavor
    descriptor. Stops at a new non-tasting section heading.
    """
    lines = markdown.splitlines()
    prose_parts: List[str] = []
    in_tasting = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _TASTING_SECTION_RE.search(stripped):
            in_tasting = True
            continue
        if in_tasting and re.match(r"^#{1,3}\s+\S", stripped):
            in_tasting = False
        if in_tasting:
            prose_parts.append(stripped)
        else:
            low = stripped.lower()
            if any(tok in low for tok in (
                "smok", "peat", "sherr", "fruit", "sweet", "spic",
                "maritim", "salt", "sea", "oak", "vanilla", "chocolate",
                "citrus", "spice", "iodine", "medicinal",
            )):
                prose_parts.append(stripped)
    return " ".join(prose_parts)


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t]


def _build_axis_evidence(prose: str) -> Tuple[List[Dict[str, Any]], int]:
    """Map tasting prose to canonical 7-axis evidence.

    Returns (evidence_list, mapped_descriptor_count).
    """
    tokens = _tokenize(prose)
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]

    axis_hits: Dict[str, List[str]] = defaultdict(list)  # axis -> [quote excerpts]
    mapped = 0
    for bg in bigrams:
        if bg in _AMBIGUOUS or bg in _STOPWORDS:
            continue
        axis = _MAPPER.get_axis(bg)
        if axis:
            axis_hits[axis].append(bg)
            mapped += 1
    for tok in tokens:
        if tok in _AMBIGUOUS or tok in _STOPWORDS:
            continue
        if any(tok in v for v in axis_hits.values()):
            continue  # already captured via bigram
        axis = _MAPPER.get_axis(tok)
        if axis:
            axis_hits[axis].append(tok)
            mapped += 1

    evidence: List[Dict[str, Any]] = []
    for axis in CANONICAL_AXES:
        hits = axis_hits.get(axis)
        if not hits:
            continue
        n = len(hits)
        value = min(1.0, _AXIS_BASE + _AXIS_PER_DESCRIPTOR * n)
        value = round(value, 4)
        confidence = min(1.0, _CONF_BASE + _CONF_PER_DESCRIPTOR * n)
        confidence = round(confidence, 4)
        quote = ", ".join(sorted(set(hits)))
        evidence.append({
            "field_name": axis,
            "field_value": value,
            "source": "whiskynotes",
            "confidence": confidence,
            "quote": f"{axis}: {quote}",
        })
    return evidence, mapped


def _extract_score(markdown: str) -> Optional[Dict[str, Any]]:
    """Extract a 0-100 expert score if present (field_rules: scored_assessment)."""
    m = _SCORE_RE.search(markdown)
    if not m:
        return None
    try:
        val = int(m.group(1))
    except ValueError:
        return None
    if val < 0 or val > 100:
        return None
    return {
        "field_name": "score",
        "field_value": val,
        "source": "whiskynotes",
        "confidence": 0.95,
        "quote": f"Score: {val}/100",
    }


class WhiskyNotesAdapter:
    """Extracts canonical 7-axis flavor vectors + expert score from WhiskyNotes."""

    SOURCE = "whiskynotes"

    def parse(self, markdown: str) -> Dict[str, Any]:
        """Parse WhiskyNotes markdown into {name, evidence:[...]}.

        Returns {} when input is empty or carries no mappable flavor/score.
        """
        if not markdown or not markdown.strip():
            return {}

        name = _extract_name(markdown)
        prose = _collect_tasting_prose(markdown)
        evidence, mapped = _build_axis_evidence(prose)

        # Score is a separate assessment field (T2 expert, scale 0-100).
        score_ev = _extract_score(markdown)
        if score_ev:
            evidence.append(score_ev)
            mapped += 1

        if not evidence:
            logger.debug(f"WhiskyNotes adapter: no mappable flavor/score in {name!r}")
            return {}

        return {"name": name, "evidence": evidence}


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            md = f.read()
        print(json.dumps(WhiskyNotesAdapter().parse(md), indent=2, ensure_ascii=False))

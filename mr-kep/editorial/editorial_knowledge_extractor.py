"""P201 — Shared LLM Knowledge Extractor (production-safe, offline-capable).

Turns an ArticleParse (raw extracted fields) into a canonical EditorialReview
conforming to editorial_review.schema.json.

Design:
- An `LLMExtractor` protocol is the authority for identity / score / 7-axis flavor.
- A deterministic HEURISTIC extractor is the built-in default (no network, no API key,
  FREE per cost policy). It is a real fallback, not a stub: regex for score, keyword
  density for the 7 canonical axes, section markers for nose/palate/finish.
- A real LLM can be injected (e.g. an OpenAI/Anthropic client) to improve accuracy;
  the pipeline never requires it and never fabricates when it is absent.

NO production.db access. Returns a plain dict (the canonical schema). Idempotent:
evidence_id is derived from source_url + content_hash, so re-runs are stable.
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol

from .adapters.editorial_base_adapter import ArticleParse, CANONICAL_AXES

# Authority-tier weights (T2_expert default for editorial).
TIER_WEIGHT = {"T1_authoritative": 0.95, "T2_expert": 0.85, "T3_community": 0.55}

# Canonical 7-axis keyword lexicon (deterministic fallback estimator).
AXIS_KEYWORDS: Dict[str, List[str]] = {
    "smoky": ["smoke", "smoky", "bonfire", "charred", "ash", "campfire", "smolder"],
    "peaty": ["peat", "peaty", "medicinal", "iodine", "phenolic", "earthy", "moss"],
    "fruity": ["apple", "pear", "citrus", "lemon", "orange", "tropical", "berry",
               "banana", "peach", "apricot", "fruit"],
    "sweet": ["honey", "vanilla", "caramel", "toffee", "sugar", "syrup", "cake",
              "butter", "cream", "confection"],
    "spicy": ["cinnamon", "pepper", "clove", "ginger", "nutmeg", "chili", "spice",
              "oak spice", "cardamom"],
    "maritime": ["salt", "brine", "seaweed", "coastal", "sea spray", "marine",
                 "salty", "ocean", "kippery"],
    "sherry": ["sherry", "raisin", "dried fruit", "oloroso", "px", "nutty", "fig",
               "date", "walnut", "almond"],
}


class LLMExtractor(Protocol):
    """Authority for soft fields. Implement with a real client if desired."""
    def __call__(self, article: ArticleParse, html: str) -> Dict:
        """Return dict with optional keys: whisky_identity, score{value,scale_max},
        nose, palate, finish, flavor_vector{7 axes 0..1}, metadata{}."""
        ...


def _sha16(source_url: str, content_hash: str) -> str:
    h = hashlib.sha256((source_url + "|" + content_hash).encode("utf-8")).hexdigest()
    return "EDR-" + h[:16]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _detect_score(text: str) -> Optional[Dict]:
    # "Score: 89/100", "89 points", "8.5/10", "Rating: 92"
    m = re.search(r"(?i)(?:score|rating)[:\s]+(\d{1,3})(?:[/\s]*(\d{2,3}))?", text)
    if not m:
        return None
    val = float(m.group(1))
    scale = float(m.group(2)) if m.group(2) else (100.0 if val > 10 else 10.0)
    if val > scale:
        scale = 100.0
    return {"value": val, "scale_max": scale,
            "normalized": max(0.0, min(1.0, val / scale))}


def _detect_metadata(text: str) -> Dict:
    meta: Dict[str, object] = {}
    abv = re.search(r"(\d{2}(?:\.\d)?)\s*%", text)
    if abv:
        meta["abv"] = float(abv.group(1))
    age = re.search(r"\b(\d{1,2})\s*y(?:ears?)?\s*o(?:ld)?\b", text)
    if age:
        meta["age_statement"] = f"{age.group(1)} YO"
    cask = re.search(r"(?i)(sherry|bourbon|oak|port|wine|rum|ex-[\w]+)\s*(?:cask|barrel|butt)", text)
    if cask:
        meta["cask_type"] = cask.group(1).capitalize()
    return meta


def _section_split(text: str) -> Dict[str, Optional[str]]:
    """Heuristic nose/palate/finish split by common markers."""
    out: Dict[str, Optional[str]] = {"nose": None, "palate": None, "finish": None}
    low = text.lower()
    def grab(marker: str) -> Optional[str]:
        i = low.find(marker)
        if i < 0:
            return None
        seg = text[i+len(marker):]
        # cut at next known marker
        for nxt in ["nose", "palate", "finish", "conclusion", "overall", "comment"]:
            j = seg.lower().find(nxt)
            if j > 0:
                seg = seg[:j]
                break
        return _norm(seg)[:1000] or None
    out["nose"] = grab("nose")
    out["palate"] = grab("palate")
    out["finish"] = grab("finish")
    return out


def _flavor_vector(text: str) -> Dict[str, float]:
    low = _norm(text)
    vec = {ax: 0.0 for ax in CANONICAL_AXES}
    for ax, kws in AXIS_KEYWORDS.items():
        hits = sum(low.count(k) for k in kws)
        vec[ax] = max(0.0, min(1.0, hits / 6.0))  # ~6 hits => saturated
    return vec


def heuristic_extract(article: ArticleParse, html: str = "") -> Dict:
    """Deterministic, offline extraction (the default authority)."""
    body = article.conclusion or ""
    score = _detect_score(body) or _detect_score(article.title or "")
    meta = _detect_metadata(body)
    sections = _section_split(body)
    vec = _flavor_vector(body)
    return {
        "whisky_identity": {"raw_name": article.raw_name},
        "score": score,
        "nose": sections["nose"],
        "palate": sections["palate"],
        "finish": sections["finish"],
        "flavor_vector": vec,
        "metadata": meta,
    }


@dataclass
class ExtractorResult:
    record: Dict
    evidence_confidence: float


def extract(
    article: ArticleParse,
    source_id: str,
    source_url: str,
    content_hash: str,
    authority_tier: str = "T2_expert",
    author: Optional[str] = None,
    published_date: Optional[str] = None,
    llm: Optional[LLMExtractor] = None,
) -> ExtractorResult:
    """Produce a canonical EditorialReview dict (editorial_review.schema.json)."""
    base = heuristic_extract(article)
    if llm is not None:
        try:
            aug = llm(article, "")
            if isinstance(aug, dict):
                # LLM may override soft fields; heuristic remains the provenance floor.
                for k in ("whisky_identity", "score", "nose", "palate", "finish",
                          "flavor_vector", "metadata"):
                    if k in aug and aug[k] is not None:
                        base[k] = aug[k]
        except Exception:
            pass  # fall back to heuristic; never fabricate

    norm_name = _norm(article.raw_name)
    identity = base.get("whisky_identity", {})
    identity.setdefault("raw_name", article.raw_name)
    identity["normalized_name"] = norm_name
    identity.setdefault("match_status", "unmatched")
    identity.setdefault("matched_master_whisky_id", None)

    score_obj = base.get("score") or {"value": None, "scale_max": None, "normalized": None}

    # evidence confidence = tier weight x extraction quality (have we got notes + vector?)
    quality = 0.4
    if base.get("nose") or base.get("palate") or base.get("finish"):
        quality += 0.3
    if any(v > 0 for v in base.get("flavor_vector", {}).values()):
        quality += 0.3
    evidence_confidence = round(TIER_WEIGHT.get(authority_tier, 0.85) * min(1.0, quality), 3)

    record = {
        "schema_version": "editorial-review/1.0",
        "evidence_id": _sha16(source_url, content_hash),
        "source": {
            "source_id": source_id,
            "source_type": "editorial",
            "authority_tier": authority_tier,
            "url": source_url,
            "title": article.title,
            "author": author or article.author,
            "published_date": published_date,
            "license": "copyright-attribution-required",
            "content_hash_sha256": content_hash,
        },
        "whisky_identity": identity,
        "metadata": base.get("metadata", {}),
        "score": score_obj,
        "tasting_notes": {
            "nose": base.get("nose"),
            "palate": base.get("palate"),
            "finish": base.get("finish"),
            "conclusion": article.conclusion,
        },
        "flavor_vector": base.get("flavor_vector", {ax: 0.0 for ax in CANONICAL_AXES}),
        "evidence": {
            "confidence": evidence_confidence,
            "extraction_method": "llm" if llm is not None else "heuristic",
            "quotes": [],
            "provenance_state": "staging_unverified",
            "ingested_by": "p201_pipeline",
        },
    }
    return ExtractorResult(record=record, evidence_confidence=evidence_confidence)


__all__ = ["extract", "ExtractorResult", "heuristic_extract", "LLMExtractor", "CANONICAL_AXES"]

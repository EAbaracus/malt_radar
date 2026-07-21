"""P201 — Editorial Base Adapter (skeleton, production-safe).

Design contract (read-only-first, no production.db writes):
- Every concrete adapter implements `discover_listing(url)` and `parse_article(html, url)`.
- `discover_listing` returns a list of article URLs (follows per-source pagination:
  `rel="next"` or numeric `page/N`, capped by max_pages).
- `parse_article` returns a dict that the Extractor normalizes into editorial_review.schema.json.
- Adapters NEVER open production.db. Staging writes go only to the separate
  staging_editorial.db via the ingest tool. This file performs NO network calls and
  NO database writes by itself — it is importable, deterministic, unit-testable.

The reference adapters in this repo (mr-kep/acquisition/adapters/*) are hardcoded
mocks; this skeleton is the real structural contract. Actual HTML selectors per
source MUST be implemented + fixture-tested before any live run (post-approval).
"""
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from urllib.parse import urljoin

# Canonical 7 axes — single source of truth (memory/flavor-system.md).
CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]


@dataclass
class ListingResult:
    article_urls: List[str]
    next_page: Optional[str] = None


@dataclass
class ArticleParse:
    raw_name: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    title: Optional[str] = None
    score_value: Optional[float] = None
    score_scale_max: Optional[float] = None
    nose: Optional[str] = None
    palate: Optional[str] = None
    finish: Optional[str] = None
    conclusion: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)
    quotes: List[Dict] = field(default_factory=list)


class EditorialBaseAdapter(ABC):
    # Set in subclass
    source_id: str = ""
    authority_tier: str = "T2_expert"   # editorial critics default to T2
    license: str = "copyright-attribution-required"
    max_pages: int = 20                 # safety cap on listing pagination

    @abstractmethod
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        """Given the HTML of a listing page, return article URLs + next-page URL."""
        raise NotImplementedError

    @abstractmethod
    def parse_article(self, url: str, html: str) -> ArticleParse:
        """Given article HTML, return structured fields (NOT yet normalized to schema)."""
        raise NotImplementedError

    # ---- shared helpers (no IO) ----

    def next_page_url(self, base: str, html: str) -> Optional[str]:
        """Default: detect rel=next or page/N patterns. Override per source if needed."""
        m = re.search(r'<link[^>]+rel=["\']next["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        if m:
            return urljoin(base, m.group(1))
        m = re.search(r'href=["\']([^"\']*page/\d+[^"\']*)["\']', html, re.I)
        if m:
            return urljoin(base, m.group(1))
        return None

    @staticmethod
    def normalize_score(value: Optional[float], scale_max: Optional[float]) -> Optional[float]:
        if value is None or not scale_max:
            return None
        return max(0.0, min(1.0, value / scale_max))

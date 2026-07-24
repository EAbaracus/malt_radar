"""LA Whiskey Society editorial adapter — canonical MR-KEP.

Grounded in the existing declarations (no parallel path):
  - sources/lawhiskeysociety/source_profile.yaml (tier T2_expert)
  - editorial/adapters/editorial_base_adapter.py (EditorialBaseAdapter contract)
  - d4_reducer/flavor_mapper.py (canonical 7-axis descriptor lexicon)
  - editorial/adapters/breakingbourbon_adapter.py (reference implementation)

LAWS content structure (learned live, audit_5):
  - Header metadata in a markdown table: "Age: 7 yrs", "ABV: 45.00 %",
    "Vintage: 2006", "Bottler:", "Price:", "Type:", "Subtype:", "Region:".
  - Tasting note is a SINGLE PROSE paragraph where nose/palate/finish appear
    as inline words (NOT section headers like WhiskyFun's "Nose:").
    Example: "...The nose has a very strong rye component... The palate has
    some bourbon sweetness... That malty note dominates the finish as well..."
  - Score is a LETTER GRADE image (bminus_thumb.jpg -> map to /100).

Design:
  - discover_listing: targeted (supplied profile URL). max_pages = 1.
  - parse_article: strip noise, isolate the member-notes prose, split into
    nose/palate/finish segments by the inline keyword boundaries, extract
    header metadata (age/abv/vintage), map letter grade -> score/100.
  - derive_axes(): deterministic FlavorMapper tally over the real prose.
  - T2 ceiling: identity fields NOT certified; only sensory + score + metadata.
  - Integrates via EditorialPromotionWriter / staging_editorial_reviews.
    NO production.db writes, NO network calls by itself.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from editorial_base_adapter import (
    EditorialBaseAdapter,
    ArticleParse,
    ListingResult,
    CANONICAL_AXES,
)

# Canonical 7-axis lexicon from the single authoritative mapper.
_D4 = Path(__file__).resolve().parent.parent.parent / "d4_reducer"
import sys
if str(_D4) not in sys.path:
    sys.path.insert(0, str(_D4))
from flavor_mapper import FlavorMapper  # noqa: E402

_FM = FlavorMapper()

# Letter-grade -> /100 (LAWS uses A+..F image grades; conservative midpoint map)
_GRADE_MAP = {
    "aplus": 96, "a": 93, "aminus": 90,
    "bplus": 87, "b": 84, "bminus": 80,
    "cplus": 77, "c": 74, "cminus": 70,
    "dplus": 67, "d": 64, "dminus": 60,
    "f": 50,
}


class LAWhiskeySocietyAdapter(EditorialBaseAdapter):
    source_id = "lawhiskeysociety"
    authority_tier = "T2_expert"
    license = "copyright-attribution-required"
    max_pages = 1  # acquisition is targeted (manifest URLs), not listing-crawl

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        return ListingResult(article_urls=[start_url], next_page=None)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean(html: str) -> str:
        h = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
        h = re.sub(r"<style.*?</style>", "", h, flags=re.S | re.I)
        return h

    @staticmethod
    def _member_notes(md: str) -> Optional[str]:
        """Extract the member tasting-note prose (after 'Member Ratings and Notes')."""
        i = md.lower().find("member ratings and notes")
        if i == -1:
            return None
        tail = md[i + len("member ratings and notes"):]
        # Flatten markdown tables: turn pipe delimiters into spaces (keeps cell text)
        tail = tail.replace("|", " ")
        # Remove images / links residues
        tail = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", tail)
        tail = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", tail)
        tail = re.sub(r"`{1,3}[^`]*`{1,3}", " ", tail)
        # Drop table separator rows
        tail = re.sub(r"[-]{3,}", " ", tail)
        tail = re.sub(r"\s+", " ", tail).strip()
        return tail or None

    @staticmethod
    def _segment(prose: str, label: str) -> Optional[str]:
        """Return the sentence(s) around an inline label (nose/palate/finish).

        Handles both full-word labels ("nose:", "the nose is...") and the
        short member-note markers ("n:", "p:", "f:") used on
        multi-reviewer LAWS pages.
        """
        # 1) full-word label
        rx = re.compile(rf"\b{label}\b\s*(.*?)(?=\s*\b(?:nose|palate|mouth|finish)\b\s|$)", re.I | re.S)
        m = rx.search(prose)
        if m and m.group(1).strip():
            txt = m.group(1).strip()
            txt = re.sub(r"^(has|have|is|are|with|on|in|the|a|an)\s+", "", txt, flags=re.I)
            return txt or None
        # 2) short member marker (n: / p: / f:)
        short = {"nose": "n", "palate": "p", "mouth": "p", "finish": "f"}.get(label.lower())
        if short:
            rxs = re.compile(rf"(?:\b|^){short}\s*:\s*(.*?)(?=\s+(?:[npf])\s*:|$)", re.I | re.S)
            ms = rxs.search(prose)
            if ms and ms.group(1).strip():
                return ms.group(1).strip()
        return None

    @staticmethod
    def _grade(md: str) -> Optional[float]:
        m = re.search(r"/images/letters/([a-z]+(?:plus|minus)?)_thumb", md, re.I)
        if m:
            return float(_GRADE_MAP.get(m.group(1).lower(), 0))
        return None

    def parse_article(self, url: str, html: str,
                      expression_identity: str = "", anchor: str = "") -> ArticleParse:
        # Firecrawl returns markdown (clean text with | tables). Parsing markdown
        # through an HTML parser (BS4) destroys table-cell content (the n:/p:/f:
        # member notes), so use the markdown text directly when no real HTML tags
        # are present. Fall back to BS4 only for genuine HTML input.
        is_markdown = ("<" not in html[:200]) or ("|" in html)
        if is_markdown:
            md = re.sub(r"\s+", " ", html)
            md = md.replace("|", " ")  # flatten tables so Age:/ABV: cells parse
            soup = None
        else:
            clean = self._clean(html)
            soup = BeautifulSoup(clean, "html.parser")
            md = soup.get_text("\n")
            md = re.sub(r"\s+", " ", md)
            md = md.replace("|", " ")

        # Title: prefer the profile slug's name; else first heading
        title = expression_identity or ""
        m = re.search(r"/whiskey-profile/\d+/([^)\s]+)", url)
        if m:
            title = m.group(1).replace("-", " ").strip().title()
        if not title:
            h = soup.find(["h1", "h2"]) if soup is not None else None
            title = h.get_text(strip=True) if h else url

        notes = self._member_notes(md)
        prose = notes or ""
        nose = self._segment(prose, "nose")
        palate = self._segment(prose, "palate") or self._segment(prose, "mouth")
        finish = self._segment(prose, "finish")

        # structured metadata from header table
        metadata = {}
        am = re.search(r"Age:\s*(\d+)\s*yrs?", md, re.I)
        if am:
            try: metadata["age_statement"] = int(am.group(1))
            except ValueError: pass
        ab = re.search(r"ABV:\s*([\d.]+)\s*%", md, re.I)
        if ab:
            try: metadata["abv"] = float(ab.group(1))
            except ValueError: pass
        vi = re.search(r"Vintage:\s*(\d{4})", md, re.I)
        if vi:
            metadata["vintage"] = vi.group(1)

        grade = self._grade(md)
        return ArticleParse(
            raw_name=title,
            author="LA Whiskey Society",
            published_date=None,
            title=title,
            score_value=grade,
            score_scale_max=100.0 if grade is not None else None,
            nose=nose,
            palate=palate,
            finish=finish,
            conclusion=(nose or "") + " + " + (palate or "") + " + " + (finish or ""),
            metadata=metadata,
            quotes=[],
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def derive_axes(parse: ArticleParse) -> dict:
        prose = " ".join(p for p in (parse.nose, parse.palate, parse.finish) if p).lower()
        counts = {ax: 0 for ax in CANONICAL_AXES}
        if prose:
            tokens = re.findall(r"[a-z]+(?:['-][a-z]+)*", prose)
            for tk in tokens:
                ax = _FM.get_axis(tk)
                if ax:
                    counts[ax] += 1
        mx = max(counts.values()) if any(counts.values()) else 0
        return {ax: round(counts[ax] / mx, 4) if mx > 0 else 0.0 for ax in CANONICAL_AXES}


def build_staging_row(whisky_id: str, url: str, content_hash: str,
                      parse: ArticleParse, axes: dict, evidence_id: str,
                      match_status: str = "exact") -> dict:
    """Convenience: build a staging_editorial_reviews-compatible row dict."""
    return {
        "evidence_id": evidence_id,
        "source_id": "lawhiskeysociety",
        "source_url": url,
        "authority_tier": "T2_expert",
        "author": parse.author or "LA Whiskey Society",
        "published_date": parse.published_date,
        "content_hash": content_hash,
        "raw_name": parse.raw_name or "",
        "normalized_name": (parse.raw_name or "").lower().strip(),
        "matched_master_whisky_id": whisky_id,
        "match_status": match_status,
        "match_confidence": 1.0,
        "score_value": parse.score_value,
        "score_scale_max": parse.score_scale_max,
        "score_normalized": (round(parse.score_value / 100.0, 4)
                             if parse.score_value is not None else None),
        "nose": parse.nose,
        "palate": parse.palate,
        "finish": parse.finish,
        "conclusion": parse.conclusion,
        "flavor_vector_json": __import__("json").dumps(axes),
        "metadata_json": __import__("json").dumps(parse.metadata or {}),
        "evidence_confidence": 1.0,
        "extraction_method": "heuristic",
        "provenance_state": "staging_unverified",
    }


__all__ = ["LAWhiskeySocietyAdapter", "build_staging_row"]

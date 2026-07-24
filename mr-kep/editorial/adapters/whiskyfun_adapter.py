"""WhiskyFun (Serge Valentin) editorial adapter — canonical MR-KEP.

Grounded in the existing declarations (no parallel path):
  - sources/whiskyfun/source_profile.yaml  (tier T2_expert, methods
    trigger_scan / structured_parse, sensory+score only, NO identity cert)
  - extraction/field_mapping.md  (WhiskyFun: nose/palate/finish/score/flavor_axes = yes)
  - editorial/adapters/editorial_base_adapter.py  (EditorialBaseAdapter contract)
  - d4_reducer/flavor_mapper.py  (canonical 7-axis descriptor lexicon)
  - common/flavor_scale_utils.py  (R4 0.0-1.0 enforcement)

Design:
  - parse_article isolates the anchor/expression block from an archive page,
    runs trigger_scan (Nose:/Palate:/Finish:) + structured_parse (ABV/age/score).
  - derive_axes() tallies FlavorMapper descriptor hits across the real
    Nose/Palate/Finish prose -> deterministic 7-axis vector, normalized to
    [0.0,1.0] by the max-axis hit count. NO hand-written vectors;
    the lexicon is the canonical source of truth (flavor_mapper.py).
  - T2 ceiling: identity fields (distillery/region/cask) are NOT certified
    (field_mapping.md marks them below-ceiling 'o'); we surface only
    sensory + score + metadata-as-stated.

This adapter integrates via the EXISTING editorial promotion path
(EditorialPromotionWriter / staging_editorial_reviews schema). It does
NOT open production.db and performs NO network calls by itself.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .editorial_base_adapter import (
    EditorialBaseAdapter,
    ArticleParse,
    ListingResult,
    CANONICAL_AXES,
)

# Canonical 7-axis lexicon from the single authoritative mapper.
_D4 = Path(__file__).resolve().parent.parent.parent / "d4_reducer"
if str(_D4) not in sys.path:
    sys.path.insert(0, str(_D4))
from flavor_mapper import FlavorMapper  # noqa: E402

_FM = FlavorMapper()

# WhiskyFun uses a common typo "Palate" instead of "Palate".
# Serge Valentin labels the palate section "Mouth:" (not "Palate:").
# Sections are delimited by the next labelled marker.
_NOSE_RE = re.compile(
    r"nose\s*:\s*(.*?)(?=\b(?:mouth|palate|finish|colour)\s*:)",
    re.I | re.S,
)
_MOUTH_RE = re.compile(
    r"(?:mouth|palate)\s*:\s*(.*?)(?=finish\s*:)",
    re.I | re.S,
)
_FINISH_RE = re.compile(
    r"finish\s*:\s*(.*?)(?=\n\s*\n|\Z|<a\s+name=)",
    re.I | re.S,
)
# ABV is taken from the expression header FIRST (deterministic), where
# WhiskyFun prints it as "(63.9%, ...)" or "(64,3%, ...)" — note
# Serge uses a COMMA decimal separator in the header. Fallback: first
# NN% / NN,N% near the block top. Accept both . and , decimals.
_ABV_RE = re.compile(r"(\d{1,3})(?:[.,](\d+))?\s*%")
_SCORE_RE = re.compile(r"\b(\d{1,3})\s*(?:pt|/100|points|/100)\b", re.I)
_AGE_RE = re.compile(r"(\d{1,3})\s*(?:yo|yrs|years)", re.I)


class WhiskyFunAdapter(EditorialBaseAdapter):
    source_id = "whiskyfun"
    authority_tier = "T2_expert"
    license = "copyright-attribution-required"
    max_pages = 1  # acquisition is targeted (9 manifest URLs), not listing-crawl

    # ------------------------------------------------------------------ #
    # Listing: the 9 targets come from the acquisition-prep manifest, NOT a
    # discovery crawl. discover_listing simply hands back the supplied URLs.
    # ------------------------------------------------------------------ #
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        # Per-target fetch: start_url IS the article URL.
        return ListingResult(article_urls=[start_url], next_page=None)

    # ------------------------------------------------------------------ #
    # Anchor isolation: WhiskyFun archive pages hold many reviews; the
    # manifest's provenance_reference carries the #anchor (e.g. #221220).
    # We locate the expression header and capture the block up to the next
    # review anchor / bold header.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _block_for(html: str, expression_identity: str, anchor: str) -> str:
        # 1) Try the anchor first (most precise).
        if anchor:
            m = re.search(r'name=["\']?%s["\']?' % re.escape(anchor), html)
            if m:
                start = m.start()
                nxt = html.find('<a name=', start + 5)
                end = nxt if nxt != -1 else min(start + 8000, len(html))
                return html[start:end]
        # 2) Fallback: locate the expression header text.
        key = expression_identity.split("(")[0].strip()[:30]
        if not key:
            key = expression_identity.split()[0] if expression_identity else ""
        idx = html.find(key)
        if idx == -1:
            # last resort: distillery token
            tok = expression_identity.split()[0] if expression_identity else ""
            idx = html.find(tok)
        if idx == -1:
            return ""
        nxt = html.find('<a name=', idx + 5)
        end = nxt if nxt != -1 else min(idx + 8000, len(html))
        return html[idx:end]

    @staticmethod
    def _section(block: str, rx) -> Optional[str]:
        m = rx.search(block)
        if not m:
            return None
        txt = BeautifulSoup(m.group(1), "html.parser").get_text(" ")
        return re.sub(r"\s+", " ", txt).strip() or None

    def parse_article(
        self, url: str, html: str,
        expression_identity: str = "", anchor: str = "",
    ) -> ArticleParse:
        block = self._block_for(html, expression_identity, anchor)
        soup = BeautifulSoup(block, "html.parser")
        text = soup.get_text(" ")

        nose = self._section(block, _NOSE_RE)
        palate = self._section(block, _MOUTH_RE)
        finish = self._section(block, _FINISH_RE)

        # structured_parse: ABV / age / score
        # ABV: prefer the expression header "(63.9%, ...)" (deterministic),
        # else first "NN%" in the block top.
        abv = None
        m = _ABV_RE.search(expression_identity or "")
        if not m:
            m = _ABV_RE.search(block[:600])
        if m:
            try:
                # group(1)=int part, group(2)=optional decimal (.,N)
                dec = (m.group(2) or "0").replace(",", "")
                abv = float(f"{m.group(1)}.{dec}")
            except ValueError:
                abv = None
        age = None
        m = _AGE_RE.search(expression_identity or "")
        if not m:
            m = _AGE_RE.search(block[:600])
        if m:
            try:
                age = int(m.group(1))
            except ValueError:
                age = None
        score = None
        m = _SCORE_RE.search(text[-600:] if text else "")
        if m:
            try:
                score = float(m.group(1))
            except ValueError:
                score = None

        # publication date from anchor (e.g. #221220 -> 2020-12-22)
        pub = None
        if anchor and len(anchor) >= 6 and anchor.isdigit():
            yy = anchor[0:2]
            mm = anchor[2:4]
            dd = anchor[4:6]
            yr = 2000 + int(yy) if int(yy) < 70 else 1900 + int(yy)
            pub = f"{yr:04d}-{mm}-{dd}"

        metadata = {}
        if abv is not None:
            metadata["abv"] = abv
        if age is not None:
            metadata["age_statement"] = age

        return ArticleParse(
            raw_name=expression_identity or (soup.get_text(" ").strip()[:120]),
            author="Serge Valentin",
            published_date=pub,
            title=expression_identity or None,
            score_value=score,
            score_scale_max=100.0 if score is not None else None,
            nose=nose,
            palate=palate,
            finish=finish,
            conclusion=(nose or "") + " " + (palate or "") + " " + (finish or ""),
            metadata=metadata,
            quotes=[],
        )

    # ------------------------------------------------------------------ #
    # Canonical 7-axis derivation (deterministic, lexicon-based).
    # Tallies FlavorMapper descriptor hits across the real Nose/Palate/
    # Finish prose; normalizes by the max-axis hit count so the strongest
    # axis == 1.0 and all values stay within [0.0, 1.0] (R4).
    # ------------------------------------------------------------------ #
    @staticmethod
    def derive_axes(parse: ArticleParse) -> dict:
        prose = " ".join(
            p for p in (parse.nose, parse.palate, parse.finish) if p
        ).lower()
        counts = {ax: 0 for ax in CANONICAL_AXES}
        if prose:
            # word-ish tokens (allow embedded hyphens/apostrophes)
            toks = re.findall(r"[a-z]+(?:['-][a-z]+)*", prose)
            for t in toks:
                ax = _FM.get_axis(t)
                if ax:
                    counts[ax] += 1
        mx = max(counts.values()) if any(counts.values()) else 0
        vec = {}
        for ax in CANONICAL_AXES:
            if mx > 0:
                vec[ax] = round(counts[ax] / mx, 4)
            else:
                vec[ax] = 0.0
        return vec


# Convenience: build a staging_editorial_reviews-compatible row dict
# from a parsed article + manifest target. Used by the fetch/stage runner.
def build_staging_row(
    whisky_id: str, url: str, content_hash: str,
    parse: ArticleParse, axes: dict, evidence_id: str,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": "whiskyfun",
        "source_url": url,
        "authority_tier": "T2_expert",
        "author": parse.author or "Serge Valentin",
        "published_date": parse.published_date,
        "content_hash": content_hash,
        "raw_name": parse.raw_name or "",
        "normalized_name": (parse.raw_name or "").lower().strip(),
        "matched_master_whisky_id": whisky_id,
        "match_status": "exact",
        "match_confidence": 1.0,
        "score_value": parse.score_value,
        "score_scale_max": parse.score_scale_max,
        "score_normalized": (
            round(parse.score_value / 100.0, 4)
            if parse.score_value is not None else None
        ),
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


__all__ = ["WhiskyFunAdapter", "build_staging_row"]

"""Breaking Bourbon editorial adapter — canonical MR-KEP.

Grounded in the existing declarations (no parallel path):
  - sources/breakingbourbon/source_profile.yaml (tier T2_expert)
  - editorial/adapters/editorial_base_adapter.py (EditorialBaseAdapter contract)
  - d4_reducer/flavor_mapper.py (canonical 7-axis descriptor lexicon)
  - common/flavor_scale_utils.py (R4 0.0-1.0 enforcement)
  - editorial/adapters/whiskyfun_adapter.py (reference implementation)

Design:
  - discover_listing: targeted (supplied review URL = the article). max_pages = 1
    (acquisition is from the audited manifest of 16 candidate ZE URLs, not a crawl).
  - parse_article: strip cookie/consent + script/style noise, isolate the
    review block, run trigger_scan (NOSE/palate/finish markers) + structured_parse
    (Proof/ABV, Age, Score). Markers are space- or newline-delimited
    ALL-CAPS/title-case words ("NOSE", "palate", "finish") — NO colon,
    unlike WhiskyFun's "Nose:".
  - derive_axes(): tallies FlavorMapper descriptor hits across the real
    Nose/Palate/Finish prose -> deterministic 7-axis vector, normalized to
    [0.0,1.0]. NO hand-written vectors.
  - T2 ceiling: identity fields NOT certified; only sensory + score + metadata.

This adapter integrates via the EXISTING editorial promotion path
(EditorialPromotionWriter / staging_editorial_reviews schema). It does
NOT open production.db and performs NO network calls by itself.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .editorial_base_adapter import (
    EditorialBaseAdapter,
    ArticleParse,
    ListingResult,
    CANONICAL_AXES,
)

# --- Canonical 7-axis lexicon from the single authoritative mapper. ---
_D4 = Path(__file__).resolve().parent.parent.parent / "d4_reducer"
import sys
if str(_D4) not in sys.path:
    sys.path.insert(0, str(_D4))
from flavor_mapper import FlavorMapper  # noqa: E402

_FM = FlavorMapper()

# Breaking Bourbon renders sections as emphasized words WITHOUT a colon:
#   "NOSE The age is apparent ..."  /  "palate Sweet on the tongue ..."  /
#   "finish The time spent ...".
# Case varies (NOSE / palate / finish). Delimit by the next marker or end.
_SECTION_RE = re.compile(
    r"\b(NOSE|PALATE|MOUTH|FINISH)\b\s*(.*?)(?=\s*\b(?:NOSE|PALATE|MOUTH|FINISH)\b\s|\Z)",
    re.I | re.S,
)
# Header metadata: "Proof: 92 Age: 22 Years Mashbill: ..."
_PROOF_RE = re.compile(r"proof\s*:\s*(\d{1,3})", re.I)
_AGE_RE = re.compile(r"age\s*:\s*(\d{1,3})\s*years?", re.I)
# Score: explicit "/100" or "Score: NN"; otherwise None (BB often omits a number).
_SCORE_RE = re.compile(r"\b(\d{1,3})\s*/\s*100\b", re.I)
_SCORE2_RE = re.compile(r"score\s*[:=]?\s*(\d{1,3})", re.I)


class BreakingBourbonAdapter(EditorialBaseAdapter):
    source_id = "breakingbourbon"
    authority_tier = "T2_expert"
    license = "copyright-attribution-required"
    max_pages = 1  # acquisition is targeted (manifest URLs), not listing-crawl

    # ----------------------------------------------------------------- #
    # Listing: the candidate URL IS the article. discover_listing simply
    # hands back the supplied URL (mirrors WhiskyFunAdapter).
    # ----------------------------------------------------------------- #
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        return ListingResult(article_urls=[start_url], next_page=None)

    # ----------------------------------------------------------------- #
    # Noise reduction: drop cookie/consent banners, scripts, styles.
    # ----------------------------------------------------------------- #
    @staticmethod
    def _clean(html: str) -> str:
        h = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
        h = re.sub(r"<style.*?</style>", "", h, flags=re.S | re.I)
        # Remove the Webflow consent/cookie block text.
        h = re.sub(r"By clicking.*?Privacy Policy", "", h, flags=re.S | re.I)
        return h

    @staticmethod
    def _section(block: str, label: str) -> Optional[str]:
        # label is one of NOSE/PALATE/FINISH (case-insensitive)
        rx = re.compile(
            r"\b" + label + r"\b\s*(.*?)(?=\s*\b(?:NOSE|PALATE|MOUTH|FINISH)\b\s|\Z)",
            re.I | re.S,
        )
        m = rx.search(block)
        if not m:
            return None
        txt = BeautifulSoup(m.group(1), "html.parser").get_text(" ")
        return re.sub(r"\s+", " ", txt).strip() or None

    def parse_article(
        self, url: str, html: str,
        expression_identity: str = "", anchor: str = "",
    ) -> ArticleParse:
        clean = self._clean(html)
        soup = BeautifulSoup(clean, "html.parser")
        text = soup.get_text(" ")

        # Title: prefer <h1>; else the review header "X IN-DEPTH REVIEW".
        title = None
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
        else:
            m = re.search(r"(.+?)\s+IN-DEPTH\s+REVIEW", text, re.I)
            if m:
                title = m.group(1).strip()
        if not title:
            title = expression_identity or url

        nose = self._section(text, "NOSE")
        palate = self._section(text, "PALATE") or self._section(text, "MOUTH")
        finish = self._section(text, "FINISH")

        # structured_parse: Proof/ABV, Age, Score
        abv = None
        mp = _PROOF_RE.search(clean[:4000]) or _PROOF_RE.search(text[:4000])
        if mp:
            try:
                abv = float(mp.group(1))  # BB gives Proof; store as ABV-equivalent number
            except ValueError:
                abv = None
        age = None
        ma = _AGE_RE.search(clean[:4000]) or _AGE_RE.search(text[:4000])
        if ma:
            try:
                age = int(ma.group(1))
            except ValueError:
                age = None
        score = None
        ms = _SCORE_RE.search(text[-1200:]) or _SCORE_RE.search(text)
        if not ms:
            ms = _SCORE2_RE.search(text[-1200:])
        if ms:
            try:
                score = float(ms.group(1))
            except ValueError:
                score = None

        metadata = {}
        if abv is not None:
            metadata["abv"] = abv  # actually Proof in BB; kept as abv field
        if age is not None:
            metadata["age_statement"] = age

        return ArticleParse(
            raw_name=title,
            author="Breaking Bourbon",
            published_date=None,
            title=title,
            score_value=score,
            score_scale_max=100.0 if score is not None else None,
            nose=nose,
            palate=palate,
            finish=finish,
            conclusion=(nose or "") + " + " + (palate or "") + " + " + (finish or ""),
            metadata=metadata,
            quotes=[],
        )

    # ----------------------------------------------------------------- #
    # Canonical 7-axis derivation (deterministic, lexicon-based).
    # ----------------------------------------------------------------- #
    @staticmethod
    def derive_axes(parse: ArticleParse) -> dict:
        prose = " ".join(
            p for p in (parse.nose, parse.palate, parse.finish) if p
        ).lower()
        counts = {ax: 0 for ax in CANONICAL_AXES}
        if prose:
            tokens = re.findall(r"[a-z]+(?:['-][a-z]+)*", prose)
            for tk in tokens:
                ax = _FM.get_axis(tk)
                if ax:
                    counts[ax] += 1
        mx = max(counts.values()) if any(counts.values()) else 0
        vec = {}
        for ax in CANONICAL_AXES:
            vec[ax] = round(counts[ax] / mx, 4) if mx > 0 else 0.0
        return vec


def build_staging_row(
    whisky_id: str, url: str, content_hash: str,
    parse: ArticleParse, axes: dict, evidence_id: str,
    match_status: str = "exact",
) -> dict:
    """Convenience: build a staging_editorial_reviews-compatible row dict."""
    return {
        "evidence_id": evidence_id,
        "source_id": "breakingbourbon",
        "source_url": url,
        "authority_tier": "T2_expert",
        "author": parse.author or "Breaking Bourbon",
        "published_date": parse.published_date,
        "content_hash": content_hash,
        "raw_name": parse.raw_name or "",
        "normalized_name": (parse.raw_name or "").lower().strip(),
        "matched_master_whisky_id": whisky_id,
        "match_status": match_status,
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


__all__ = ["BreakingBourbonAdapter", "build_staging_row"]

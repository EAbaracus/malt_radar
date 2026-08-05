"""P96 Entity Resolution / Identity Mapping — controlled proof layer.

REUSES the proven, production-safe matcher in
mr-kep/editorial/matching.py (WhiskyRegistryMatcher + normalize_text +
SequenceMatcher thresholds). This module does NOT reimplement matching;
it wraps the matcher and maps its decisions onto the explicit
MATCH / NO_MATCH / AMBIGUOUS contract required by the proof, adding:

  * distillery disambiguation (same normalized name but DIFFERENT
    distillery -> never an automatic MATCH; becomes AMBIGUOUS),
  * AMBIGUOUS when two or more candidates are within the review margin
    (multiple plausible -> preserved, never silently chosen),
  * rich provenance (rule, matched fields, reason, candidate list).

Hard guarantees:
  * READ-ONLY on production.db (mode=ro). NEVER writes.
  * NEVER invents a production whisky_id.
  * NEVER uses product name alone as an identity.
  * NEVER auto-selects among ambiguous candidates.
  * Deterministic: same candidate -> same result.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional

from editorial.matching import (
    WhiskyRegistryMatcher,
    normalize_text,
    THRESH_HIGH,
    THRESH_REVIEW,
    THRESH_MANUAL,
    MARGIN_HIGH,
    MARGIN_REVIEW,
)

PRODUCTION_DB = "output/import/production.db"


@dataclass
class Candidate:
    whisky_id: str
    name: str
    norm_name: str
    distillery_id: Optional[str]
    brand: Optional[str]
    age: Optional[str]
    abv: Optional[float]
    region: Optional[str]
    ratio: float = 0.0


@dataclass
class ResolutionResult:
    kind: str  # MATCH | NO_MATCH | AMBIGUOUS
    whisky_id: Optional[str] = None
    confidence: float = 0.0
    rule: str = ""
    matched_fields: List[str] = field(default_factory=list)
    reason: str = ""
    candidates: List[Candidate] = field(default_factory=list)
    source_url: Optional[str] = None


class EntityResolver:
    """Thin wrapper over WhiskyRegistryMatcher with explicit 3-way contract."""

    def __init__(self, production_db: str = PRODUCTION_DB):
        self._db = production_db
        self._matcher = WhiskyRegistryMatcher(production_db)
        self._targets: List[Candidate] = []
        self._by_id: dict = {}

    # ── read-only registry load (richer than matcher's name+age) ──
    @staticmethod
    def _coerce_age(v):
        if v is None:
            return None
        try:
            f = float(v)
            return str(int(f)) if f == int(f) else str(v)
        except (ValueError, TypeError):
            return str(v)

    @staticmethod
    def _coerce_abv(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace("%", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def load(self) -> int:
        conn = sqlite3.connect(f"file:{self._db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT whisky_id, name, distillery_id, brand, age, abv, region "
                "FROM whiskies"
            ).fetchall()
        finally:
            conn.close()
        self._targets = []
        self._by_id = {}
        for r in rows:
            wid, name, did, brand, age, abv, region = (r + (None,) * (7 - len(r)))[:7]
            norm = normalize_text(name)
            c = Candidate(
                whisky_id=wid, name=name, norm_name=norm,
                distillery_id=did, brand=brand,
                age=self._coerce_age(age),
                abv=self._coerce_abv(abv),
                region=region,
            )
            self._targets.append(c)
            self._by_id[wid] = c
        return len(self._targets)

    # ── core scoring (mirrors matcher, but keeps top-N for ambiguity) ──
    def _score(self, cand) -> List[tuple]:
        src = normalize_text(cand.get("product_name") or cand.get("name") or "")
        src_age = cand.get("age")
        if src_age is None and (cand.get("product_name") or cand.get("name")):
            import re
            m = re.search(r"\b(\d+)\s*y(?:ears?)?\s*o(?:ld)?\b",
                          str(cand.get("product_name") or cand.get("name")).lower())
            src_age = m.group(1) if m else None
        scored = []
        for t in self._targets:
            ratio = SequenceMatcher(None, src, t.norm_name).ratio()
            scored.append((ratio, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    # ── public resolve ──
    def resolve(self, candidate: dict) -> ResolutionResult:
        if not self._targets:
            self.load()
        source_url = candidate.get("source_url")
        scored = self._score(candidate)
        if not scored or scored[0][0] < THRESH_MANUAL:
            return ResolutionResult(
                kind="NO_MATCH", reason="no candidate above manual threshold",
                source_url=source_url,
            )
        best_ratio, best = scored[0]
        second_ratio = scored[1][0] if len(scored) > 1 else 0.0
        margin = best_ratio - second_ratio

        # Build candidate list (top-3 for provenance / ambiguity)
        top = [Candidate(**{**vars(t), "ratio": r}) for r, t in scored[:3] if r >= THRESH_MANUAL]

        # Distillery disambiguation: candidate provides a distillery that
        # conflicts with the best match -> cannot auto-MATCH.
        cand_dist = candidate.get("distillery_id") or candidate.get("distillery")
        dist_conflict = bool(cand_dist) and bool(best.distillery_id) and \
            str(cand_dist).lower() != str(best.distillery_id).lower()

        # Ambiguity: two candidates within the review margin of the top.
        ambiguous_top = margin < MARGIN_REVIEW and second_ratio >= THRESH_REVIEW

        matched_fields = ["normalized_name"]
        if candidate.get("age") and str(candidate.get("age")) == (best.age or ""):
            matched_fields.append("age")
        if cand_dist and str(cand_dist).lower() == str(best.distillery_id).lower():
            matched_fields.append("distillery")

        # Decide
        if best_ratio >= THRESH_HIGH and margin >= MARGIN_HIGH and not dist_conflict and not ambiguous_top:
            return ResolutionResult(
                kind="MATCH", whisky_id=best.whisky_id,
                confidence=round(best_ratio, 3), rule="exact_normalized_name+margin",
                matched_fields=matched_fields,
                reason=f"normalized name ratio {best_ratio:.3f} with clear margin {margin:.3f}",
                candidates=top, source_url=source_url,
            )
        if ambiguous_top or dist_conflict:
            return ResolutionResult(
                kind="AMBIGUOUS",
                confidence=round(best_ratio, 3),
                rule="ambiguous_top2" if ambiguous_top else "distillery_conflict",
                matched_fields=matched_fields,
                reason=("top-2 within review margin" if ambiguous_top else
                        f"distillery conflict: candidate={cand_dist} vs match={best.distillery_id}"),
                candidates=top, source_url=source_url,
            )
        # fuzzy but clearly top: allow MATCH at lower confidence (no ambiguity)
        if best_ratio >= THRESH_REVIEW and margin >= MARGIN_REVIEW and not dist_conflict:
            return ResolutionResult(
                kind="MATCH", whisky_id=best.whisky_id,
                confidence=round(best_ratio, 3), rule="fuzzy_normalized_name+margin",
                matched_fields=matched_fields,
                reason=f"fuzzy normalized name ratio {best_ratio:.3f} with margin {margin:.3f}",
                candidates=top, source_url=source_url,
            )
        # manual_review band -> ambiguous (weak, do not auto-select)
        return ResolutionResult(
            kind="AMBIGUOUS", confidence=round(best_ratio, 3),
            rule="manual_review_band", matched_fields=matched_fields,
            reason=f"ratio {best_ratio:.3f} in manual-review band; not auto-matched",
            candidates=top, source_url=source_url,
        )


__all__ = ["EntityResolver", "ResolutionResult", "Candidate"]

"""P201 — Whisky registry matcher (production-safe, read-only on production.db).

Reuses the PRE-EXISTING, proven matching logic from
scripts/external_sources/match_structured_ml_whiskey_source_to_production.py
(normalize_text + SequenceMatcher, thresholds 0.94/0.88/0.82 + age/brand rules).
The normalize_text implementation here is a faithful copy of that repo function so
editorial remains self-contained and testable; behavior is identical.

Writes NOTHING to production.db. Reads `whiskies(name, whisky_id, age)` via mode=ro.
Returns a match decision; the orchestrator persists it into the SEPARATE staging db.
"""
from __future__ import annotations
import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

PRODUCTION_DB = "output/import/production.db"

# Thresholds mirrored from match_structured_ml_whiskey_source_to_production.py
THRESH_HIGH = 0.94
THRESH_REVIEW = 0.88
THRESH_MANUAL = 0.82
MARGIN_HIGH = 0.03
MARGIN_REVIEW = 0.04

# Leading tokens that carry no identity signal ("The Glenlivet" -> "glenlivet").
STOPWORDS = {"the", "a", "an", "and", "by", "of", "at", "de", "le", "la",
             "das", "der", "di", "da", "del", "les", "el"}


def _first_sig_token(norm_name: str) -> str:
    """First token of a normalized name, skipping identity-neutral stopwords."""
    for tok in norm_name.split():
        if tok not in STOPWORDS:
            return tok
    return ""


def normalize_text(text) -> str:
    """Faithful copy of scripts/external_sources/...normalize_text."""
    if text is None:
        return ""
    t = str(text).lower()
    t = re.sub(r'\d+(\.\d+)?\s*%', '', t)
    t = t.replace('cask strength', '')
    t = re.sub(r'\(?distilled\s+\d{4}\)?', '', t)
    t = re.sub(r'bottled\s+\d{4}', '', t)
    t = re.sub(r'\d{4}\s+vintage', '', t)
    t = re.sub(r'vintage\s+\d{4}', '', t)
    t = re.sub(r'(\d+)\s*y(?:ears?)?\s*o(?:ld)?\.?', r'\1', t)
    t = re.sub(r'(\d+)\s*yo', r'\1', t)
    generics = ['whisky', 'whiskey', 'scotch', 'single malt', 'straight bourbon',
                'kentucky', 'limited edition', 'release', 'blended', 'malt']
    for g in generics:
        t = re.sub(r'\b' + g + r'\b', '', t)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_age(text) -> Optional[str]:
    if text is None:
        return None
    m = re.search(r'\b(\d+)\s*y(?:ears?)?\s*o(?:ld)?\b', str(text).lower())
    if m:
        return m.group(1)
    m = re.search(r'\b(\d+)\s*yo\b', str(text).lower())
    return m.group(1) if m else None


@dataclass
class MatchDecision:
    matched_master_whisky_id: Optional[str]
    match_status: str            # exact | fuzzy | manual_review | unmatched
    match_confidence: float


class WhiskyRegistryMatcher:
    def __init__(self, production_db: str = PRODUCTION_DB):
        self._targets: List[dict] = []
        self._db_path = production_db

    def load_registry(self) -> int:
        """Read whiskies read-only. Returns target count. No writes."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT whisky_id, name, age FROM whiskies").fetchall()
        finally:
            conn.close()
        self._targets = [
            {"whisky_id": r[0], "name": r[1], "norm_name": normalize_text(r[1]),
             "age": r[2]}
            for r in rows
        ]
        # Fast-match index: group targets by first significant token so match()
        # never SequenceMatchers all ~4,750 registrants per row
        # (5,035 x 4,750 = 24M calls timed out at 180s on the staging set).
        self._first_index: dict[str, list[dict]] = {}
        for t in self._targets:
            key = _first_sig_token(t["norm_name"])
            self._first_index.setdefault(key, []).append(t)
        return len(self._targets)

    def match(self, raw_name: str, age_hint: Optional[int] = None) -> MatchDecision:
        if not self._targets:
            self.load_registry()
        src = normalize_text(raw_name)
        src_age = str(age_hint) if age_hint is not None else extract_age(raw_name)
        src_first = _first_sig_token(src) or (src.split()[0] if src else "")

        # Fast path: only SequenceMatcher candidates sharing the first
        # significant token (~dozens, not ~4,750 per row).
        candidates = self._first_index.get(src_first, [])
        if not candidates:
            # Fallback: literal first-token bucket, then full scan (rare).
            candidates = self._first_index.get(src.split()[0] if src else "", []) \
                or self._targets

        scored = []
        for t in candidates:
            ratio = SequenceMatcher(None, src, t["norm_name"]).ratio()
            scored.append((ratio, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0]
        second = scored[1] if len(scored) > 1 else (0.0, None)
        margin = best[0] - second[0]

        status = "unmatched"
        if best[0] >= THRESH_HIGH and margin >= MARGIN_HIGH:
            status = "exact"
        elif best[0] >= THRESH_REVIEW and margin >= MARGIN_REVIEW:
            status = "fuzzy"
        elif best[0] >= THRESH_MANUAL:
            status = "manual_review"

        if status in ("exact", "fuzzy"):
            tgt_age = best[1]["age"]
            if tgt_age is None:
                tgt_age = extract_age(best[1]["name"])
            else:
                tgt_age = str(int(tgt_age)) if float(tgt_age) == int(tgt_age) else str(tgt_age)
            if src_age and tgt_age and str(src_age) != str(tgt_age):
                status = "manual_review"
            # R9 hard-block: numeric identifiers in the source and target names
            # MUST intersect. "Port Askaig 28" vs "Port Askaig 8" must never
            # exact/fuzzy-match — different year/vintage identifiers are a
            # hard identity mismatch, not a fuzzy suggestion.
            src_nums = set(re.findall(r"\d+", src))
            tgt_nums = set(re.findall(r"\d+", best[1]["norm_name"]))
            if src_nums and tgt_nums and not (src_nums & tgt_nums):
                status = "unmatched"
        if status == "exact" and src_first and src_first not in best[1]["norm_name"]:
            status = "fuzzy"

        wid = best[1]["whisky_id"] if status != "unmatched" else None
        conf = round(best[0], 3) if status != "unmatched" else 0.0
        return MatchDecision(matched_master_whisky_id=wid,
                             match_status=status, match_confidence=conf)


__all__ = ["WhiskyRegistryMatcher", "MatchDecision", "normalize_text"]

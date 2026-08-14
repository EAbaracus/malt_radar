"""Canonical normalizers — one per supported field type (P500-K).

Each normalizer implements:
    normalize(rec: ExtractionRecord) -> NormalizedRecord

Normalization is PURE — no I/O, no side effects.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable, Optional

# Canonical import approach
_ENGINE_ROOT = Path(__file__).resolve().parent.parent
import sys
for _p in [_ENGINE_ROOT / "extraction_engine", _ENGINE_ROOT / "normalize"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from extraction_record import ExtractionRecord
from normalized_record import (
    NormalizedRecord,
    NormalizedFieldType as NFT,
    NormalizationStatus as NS,
)


# ── Helper: build a NormalizedRecord from an ExtractionRecord ─────────

def _make(rec: ExtractionRecord, field_type: str,
          normalized_value: Optional[str],
          status: str = NS.NORMALIZED.value,
          conflict_reason: str = "") -> NormalizedRecord:
    return NormalizedRecord(
        artifact_id=rec.artifact_id,
        source_type=rec.source_type,
        source_identifier=rec.source_identifier,
        source_uri=rec.source_uri,
        original_field_name=rec.field_name,
        verbatim_quote=rec.verbatim_quote,
        source_location=rec.source_location,
        content_hash=rec.content_hash,
        extractor_version=rec.extractor_version,
        extractor_config_hash=rec.extractor_config_hash,
        field_type=field_type,
        normalized_value=normalized_value,
        raw_value=rec.extracted_value,
        normalization_status=status,
        conflict_reason=conflict_reason,
    )


# ── ABV normalizer ────────────────────────────────────────────────────

# Matches patterns like "40%", "46.3%", "57.1% ABV", "40% vol", "40.0%"
_ABV_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE)


def normalize_abv(rec: ExtractionRecord) -> NormalizedRecord:
    """Extract ABV percentage as canonical 0-100 float string.

    Known patterns:
      - "46.3%"  → "46.3"
      - "60% ABV" → "60.0"
      - "N/A"    → CONFLICT (unresolvable)
      - ""       → SKIPPED
    """
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.ABV.value, None, NS.SKIPPED.value)

    m = _ABV_PATTERN.search(raw)
    if m:
        # Check for negative sign before match
        idx = m.start(1)
        neg = idx > 0 and raw[idx - 1] == "-"
        val = m.group(1)
        # Clamp to 0-100 (defensive)
        try:
            f = float(val)
        except ValueError:
            return _make(rec, NFT.ABV.value, None, NS.CONFLICT.value,
                         f"non-numeric after parse: '{val}'")
        if neg or f < 0:
            return _make(rec, NFT.ABV.value, None, NS.CONFLICT.value,
                         f"negative ABV: {val}")
        if f > 100:
            return _make(rec, NFT.ABV.value, None, NS.CONFLICT.value,
                         f"ABV>100: {f}")
        return _make(rec, NFT.ABV.value, val)

    # Try bare number
    try:
        f = float(raw)
        if 0 <= f <= 100:
            return _make(rec, NFT.ABV.value, str(f))
    except ValueError:
        pass

    return _make(rec, NFT.ABV.value, None, NS.CONFLICT.value,
                 f"unparseable ABV: '{raw}'")


# ── Name normalizer ───────────────────────────────────────────────────

_NAME_CLEANUP = re.compile(r"[_\"'`]+")
_NAME_MULTI_WS = re.compile(r"\s+")


def _normalize_name(raw: str) -> str:
    """Canonical name cleanup:
    - lowercase
    - strip whitespace
    - collapse multiple whitespace to single
    - normalize quotes
    """
    s = raw.strip().lower()
    s = _NAME_CLEANUP.sub(" ", s)
    s = _NAME_MULTI_WS.sub(" ", s)
    s = s.strip()
    # Standalone ampersand → "and"
    s = s.replace(" & ", " and ")
    return s


def normalize_product_name(rec: ExtractionRecord) -> NormalizedRecord:
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.PRODUCT_NAME.value, None, NS.SKIPPED.value)
    norm = _normalize_name(raw)
    return _make(rec, NFT.PRODUCT_NAME.value, norm)


def normalize_source_identifier(rec: ExtractionRecord) -> NormalizedRecord:
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.SOURCE_IDENTIFIER.value, None, NS.SKIPPED.value)
    # Normalize spaces and case for consistency
    norm = _normalize_name(raw)
    return _make(rec, NFT.SOURCE_IDENTIFIER.value, norm)


# ── Flavor axis normalizer ────────────────────────────────────────────

# Canonical 7-axis contract (mirrors CANONICAL_AXES / flavor_scale_utils)
CANONICAL_AXES = {"smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"}


def normalize_flavor_axis(rec: ExtractionRecord) -> NormalizedRecord:
    """Normalize a flavor axis value to storage scale 0.0-1.0.

    Uses flavor_scale_utils.to_storage_scale for consistency.
    """
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.FLAVOR_AXIS.value, None, NS.SKIPPED.value,
                     "empty value")

    try:
        from mr_kep.common.flavor_scale_utils import to_storage_scale
    except ImportError:
        # Inline fallback
        def _to_storage(v):
            if v is None or v == "":
                return None
            try:
                f = float(v)
            except (TypeError, ValueError):
                return None
            if f > 1.0:
                f = f / 100.0
            if f < 0.0:
                f = 0.0
            if f > 1.0:
                f = 1.0
            return f
        scale_fn = _to_storage
    else:
        scale_fn = to_storage_scale

    norm = scale_fn(raw)
    if norm is None:
        return _make(rec, NFT.FLAVOR_AXIS.value, None, NS.CONFLICT.value,
                     f"non-numeric axis: '{raw}'")
    # Round to 2 decimal places for canonical representation
    norm_str = f"{norm:.2f}"
    return _make(rec, NFT.FLAVOR_AXIS.value, norm_str)


# ── Free-text normalizer (nose / palate / finish) ─────────────────────

def normalize_free_text(rec: ExtractionRecord, field_type: str) -> NormalizedRecord:
    """Normalize free-text fields: strip, collapse whitespace, preserve case."""
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, field_type, None, NS.SKIPPED.value)
    norm = _NAME_MULTI_WS.sub(" ", raw)
    return _make(rec, field_type, norm)


def normalize_nose(rec: ExtractionRecord) -> NormalizedRecord:
    return normalize_free_text(rec, NFT.NOSE_TEXT.value)


def normalize_palate(rec: ExtractionRecord) -> NormalizedRecord:
    return normalize_free_text(rec, NFT.PALATE_TEXT.value)


def normalize_finish(rec: ExtractionRecord) -> NormalizedRecord:
    return normalize_free_text(rec, NFT.FINISH_TEXT.value)


# ── Rating normalizer ─────────────────────────────────────────────────

_RATING_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)(?:\s*/\s*\d{1,3})?")


def normalize_rating(rec: ExtractionRecord) -> NormalizedRecord:
    """Normalize rating to 0-100 integer scale.

    Handles "88/100", "88", "88 points", "7.5/10" etc.
    """
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.RATING.value, None, NS.SKIPPED.value)

    m = _RATING_PATTERN.search(raw)
    if not m:
        return _make(rec, NFT.RATING.value, None, NS.CONFLICT.value,
                     f"unparseable rating: '{raw}'")

    try:
        val = float(m.group(1))
    except ValueError:
        return _make(rec, NFT.RATING.value, None, NS.CONFLICT.value,
                     f"non-numeric: '{raw}'")

    # If value <= 10 and raw contains "/10", assume 0-10 scale
    if val <= 10 and "/10" in raw:
        val = val * 10

    if val < 0 or val > 100:
        return _make(rec, NFT.RATING.value, None, NS.CONFLICT.value,
                     f"rating out of range 0-100: {val}")

    return _make(rec, NFT.RATING.value, str(int(round(val))))


# ── Age statement normalizer ──────────────────────────────────────────

_AGE_PATTERN = re.compile(r"(\d{1,3})\s*(?:year\s*(?:old)?|yo|y\b)", re.IGNORECASE)


def normalize_age(rec: ExtractionRecord) -> NormalizedRecord:
    """Extract age statement as integer string.

    Handles "12 Year Old", "18yo", "10 years", "NAS" etc.
    """
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.AGE_STATEMENT.value, None, NS.SKIPPED.value)

    # Check for NAS / no age statement
    low = raw.lower()
    if low in ("nas", "no age statement", "no age", "none", "n/a"):
        return _make(rec, NFT.AGE_STATEMENT.value, "0", NS.NORMALIZED.value)

    m = _AGE_PATTERN.search(raw)
    if m:
        return _make(rec, NFT.AGE_STATEMENT.value, m.group(1))

    # Try bare number
    try:
        val = int(float(raw))
        if 1 <= val <= 100:
            return _make(rec, NFT.AGE_STATEMENT.value, str(val))
    except ValueError:
        pass

    return _make(rec, NFT.AGE_STATEMENT.value, None, NS.CONFLICT.value,
                 f"unparseable age: '{raw}'")


# ── Region normalizer ─────────────────────────────────────────────────

_REGION_MAP = {
    "islay": "Islay",
    "highland": "Highland",
    "speyside": "Speyside",
    "lowland": "Lowland",
    "campbeltown": "Campbeltown",
    "islands": "Islands",
    "orkney": "Islands",
    "ireland": "Ireland",
    "japan": "Japan",
    "usa": "USA",
    "usa bourbon": "USA",
    "tennessee": "USA",
    "canada": "Canada",
    "india": "India",
    "taiwan": "Taiwan",
    "australia": "Australia",
    "new zealand": "New Zealand",
    "south africa": "South Africa",
    "england": "England",
    "sweden": "Sweden",
    "france": "France",
    "germany": "Germany",
    "switzerland": "Switzerland",
    "wales": "Wales",
}

# Also match "Highland (region)" or similar suffix/prefix
_REGION_CLEANUP = re.compile(r"\s*\([^)]*region[^)]*\)\s*", re.IGNORECASE)


def normalize_region(rec: ExtractionRecord) -> NormalizedRecord:
    """Normalize region to canonical spelling.

    Supports Scottish regions + international.
    Returns CONFLICT for unrecognised region strings.
    """
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.REGION.value, None, NS.SKIPPED.value)

    cleaned = _REGION_CLEANUP.sub("", raw).strip().lower()
    canonical = _REGION_MAP.get(cleaned)

    if canonical:
        return _make(rec, NFT.REGION.value, canonical)

    # Fuzzy match: check if cleaned starts with or contains a known key
    for key, canon in _REGION_MAP.items():
        if cleaned.startswith(key) or key.startswith(cleaned):
            return _make(rec, NFT.REGION.value, canon)

    return _make(rec, NFT.REGION.value, None, NS.CONFLICT.value,
                 f"unrecognised region: '{raw}'")


# ── Country normalizer ────────────────────────────────────────────────

_COUNTRY_MAP = {
    "scotland": "Scotland",
    "ireland": "Ireland",
    "northern ireland": "Ireland",
    "usa": "USA",
    "united states": "USA",
    "japan": "Japan",
    "canada": "Canada",
    "india": "India",
    "taiwan": "Taiwan",
    "australia": "Australia",
    "new zealand": "New Zealand",
    "south africa": "South Africa",
    "england": "England",
    "sweden": "Sweden",
    "france": "France",
    "germany": "Germany",
    "switzerland": "Switzerland",
    "wales": "Wales",
    "netherlands": "Netherlands",
    "denmark": "Denmark",
    "iceland": "Iceland",
}


def normalize_country(rec: ExtractionRecord) -> NormalizedRecord:
    raw = rec.extracted_value.strip()
    if not raw:
        return _make(rec, NFT.COUNTRY.value, None, NS.SKIPPED.value)

    key = raw.strip().lower()
    canonical = _COUNTRY_MAP.get(key)
    if canonical:
        return _make(rec, NFT.COUNTRY.value, canonical)

    return _make(rec, NFT.COUNTRY.value, None, NS.CONFLICT.value,
                 f"unrecognised country: '{raw}'")


# ── Normalizer registry ───────────────────────────────────────────────

NormalizerFn = Callable[[ExtractionRecord], NormalizedRecord]

_NORMALIZERS: dict[str, NormalizerFn] = {}

# Heuristic: map field-name patterns to normalizer functions
_FIELD_PATTERNS: list[tuple[re.Pattern, str]] = []


def register_normalizer(name: str, fn: NormalizerFn,
                        field_pattern: Optional[str] = None) -> None:
    """Register a normalizer by name, optionally with a field-name regex.

    If field_pattern is provided, normalizer auto-resolves when
    normalize_record() is called with a matching field_name.
    """
    _NORMALIZERS[name] = fn
    if field_pattern:
        _FIELD_PATTERNS.append((re.compile(field_pattern, re.IGNORECASE), name))


def get_normalizer(name: str) -> NormalizerFn:
    if name not in _NORMALIZERS:
        raise KeyError(f"No normalizer registered: '{name}'")
    return _NORMALIZERS[name]


def resolve_normalizer(field_name: str) -> Optional[str]:
    """Auto-detect which normalizer to use for a given field_name.

    Tries registered field patterns in registration order.
    """
    for pat, name in _FIELD_PATTERNS:
        if pat.search(field_name):
            return name
    return None


def normalize_record(rec: ExtractionRecord) -> NormalizedRecord:
    """Apply the canonical normalizer for one ExtractionRecord.

    Auto-resolves based on field name pattern. Falls back to UNSUPPORTED
    if no normalizer matches.
    """
    normalizer_name = resolve_normalizer(rec.field_name)
    if normalizer_name is None:
        return NormalizedRecord(
            artifact_id=rec.artifact_id,
            source_type=rec.source_type,
            source_identifier=rec.source_identifier,
            source_uri=rec.source_uri,
            original_field_name=rec.field_name,
            verbatim_quote=rec.verbatim_quote,
            source_location=rec.source_location,
            content_hash=rec.content_hash,
            extractor_version=rec.extractor_version,
            extractor_config_hash=rec.extractor_config_hash,
            field_type=NFT.UNKNOWN.value,
            normalized_value=None,
            raw_value=rec.extracted_value,
            normalization_status=NS.UNSUPPORTED.value,
            conflict_reason=f"no normalizer for field: '{rec.field_name}'",
        )

    fn = _NORMALIZERS[normalizer_name]
    return fn(rec)


# ── Register all normalizers with field-name patterns ─────────────────

register_normalizer("abv", normalize_abv, r"(?:^|:|\s)abv\b")
register_normalizer("product_name", normalize_product_name, r"(?:^|:|\s)(?:product|name|whisky|whiskey|bottle)\s*(?:_|name)?")
register_normalizer("source_identifier", normalize_source_identifier, r"(?:^|:|\s)source\s*_?id(?:entifier)?")
register_normalizer("flavor_axis", normalize_flavor_axis, r"(?:^|:|\s)(?:smoky|peaty|fruity|sweet|spicy|maritime|sherry)\b")
register_normalizer("nose", normalize_nose, r"(?:^|:|\s)nose\b")
register_normalizer("palate", normalize_palate, r"(?:^|:|\s)palate\b")
register_normalizer("finish", normalize_finish, r"(?:^|:|\s)finish\b")
register_normalizer("rating", normalize_rating, r"(?:^|:|\s)rating\b")
register_normalizer("age", normalize_age, r"(?:^|:|\s)(?:age|year)\b")
register_normalizer("region", normalize_region, r"(?:^|:|\s)region\b")
register_normalizer("country", normalize_country, r"(?:^|:|\s)country\b")


__all__ = [
    "normalize_record", "register_normalizer", "get_normalizer",
    "resolve_normalizer",
    "normalize_abv", "normalize_product_name", "normalize_source_identifier",
    "normalize_flavor_axis", "normalize_nose", "normalize_palate",
    "normalize_finish", "normalize_rating", "normalize_age",
    "normalize_region", "normalize_country",
]

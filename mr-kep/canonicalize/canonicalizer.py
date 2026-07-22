"""Canonicalizer — canonical CANONICALIZE implementation (P500-L).

Delegates descriptor→axis mapping to the canonical D4 FlavorMapper.
Transforms NormalizedRecord flavor_axis values into 7-axis flavor vectors
on storage scale 0.0–1.0.

Owned by MR-KEP. Does NOT write to any database.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Path setup
_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

for _p in [
    _ENGINE_ROOT / "canonicalize",
    _ENGINE_ROOT / "normalize",
    _ENGINE_ROOT / "extraction_engine",
    _ENGINE_ROOT / "d4_reducer",
    _ENGINE_ROOT / "common",
]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from canonicalized_record import (
    CanonicalFlavorEvidence,
    CanonicalizationResult,
    CanonicalizationStatus,
    AxisSource,
    CANONICAL_AXES,
    CanonicalizationError,
)
from normalized_record import NormalizedRecord, NormalizedFieldType as NFT

# Delegate to D4 FlavorMapper as the SINGLE authoritative descriptor→axis lexicon
try:
    from flavor_mapper import FlavorMapper
except ImportError:
    # Inline fallback — must stay in sync with d4_reducer/flavor_mapper.py
    class FlavorMapper:
        def __init__(self):
            self.mapping = {
                # smoky
                "smoke": "smoky", "smoky": "smoky", "bonfire": "smoky",
                "charred": "smoky", "ash": "smoky", "campfire": "smoky", "smolder": "smoky",
                # peaty
                "peat": "peaty", "peaty": "peaty", "medicinal": "peaty",
                "iodine": "peaty", "phenolic": "peaty", "earthy": "peaty", "moss": "peaty",
                # fruity — include axis name as self-key
                "fruity": "fruity", "apple": "fruity", "pear": "fruity", "citrus": "fruity", "lemon": "fruity",
                "orange": "fruity", "tropical": "fruity", "berry": "fruity", "cherry": "fruity",
                "raisin": "fruity", "banana": "fruity",
                # sweet — include axis name as self-key
                "sweet": "sweet", "honey": "sweet", "vanilla": "sweet", "caramel": "sweet", "toffee": "sweet",
                "sugar": "sweet", "syrup": "sweet", "cake": "sweet", "chocolate": "sweet",
                # spicy — include axis name as self-key
                "spicy": "spicy", "cinnamon": "spicy", "pepper": "spicy", "clove": "spicy", "ginger": "spicy",
                "nutmeg": "spicy", "chili": "spicy", "spice": "spicy",
                # maritime — FIX: include axis name as self-key (was missing)
                "maritime": "maritime", "salt": "maritime", "brine": "maritime", "seaweed": "maritime",
                "coastal": "maritime", "sea": "maritime", "sea spray": "maritime",
                "marine": "maritime", "salty": "maritime", "ocean": "maritime",
                # sherry — include axis name as self-key
                "sherry": "sherry", "oloroso": "sherry", "px": "sherry", "nutty": "sherry",
                "fig": "sherry", "dried fruit": "sherry", "port": "sherry",
            }
        def get_axis(self, descriptor):
            return self.mapping.get((descriptor or "").lower().strip())

from flavor_scale_utils import to_storage_scale


# ── Canonicalizer version ─────────────────────────────────────────────

CANONICALIZE_VERSION = "canonicalize-v1.0.0"


def _canon_config_hash() -> str:
    raw = f"canonicalizer={CANONICALIZE_VERSION}:axes={','.join(CANONICAL_AXES)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Ambiguous descriptor list (mirrors D4 AmbiguityHandler) ───────────
# Descriptors that are too vague to map to any axis.
_AMBIGUOUS_TERMS = frozenset({
    "rich", "complex", "smooth", "balanced", "intense",
    "nice", "good", "great", "excellent", "fine",
    "mellow", "soft", "bold", "big", "classic",
})


def _extract_descriptor(text: str) -> str:
    """Extract a single word descriptor from a text value.

    For flavor axis records with numeric normalized_value, return the
    verbatim_quote as the descriptor for mapping.
    For free-text (nose/palate/finish), tokenize and collect words.
    """
    return text.strip().lower().rstrip(".,;:!?")


# Free-text tokenization: split on non-alpha, keep meaningful single words and bigrams
_TOKEN_SPLIT = re.compile(r"[^a-zA-Z]+")


def _tokenize(text: str) -> list[str]:
    """Tokenize free text into individual word tokens, preserving case."""
    return [t for t in _TOKEN_SPLIT.split(text) if t]


def _get_bigrams(tokens: list[str]) -> list[str]:
    """Build bigrams from a list of tokens."""
    return [f"{tokens[i]} {tokens[i+1]}".lower() for i in range(len(tokens) - 1)]


# ── Core canonicalization function ────────────────────────────────────

# Known words that are NOT flavor descriptors (filters)
_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "from", "by", "is", "are", "was", "were",
    "be", "been", "has", "have", "had", "not", "no", "very", "some",
    "this", "that", "these", "those", "it", "its", "all", "each",
    "long", "short", "more", "most", "less", "much", "many",
})


def canonicalize(
    whisky_id: str,
    whisky_name: str,
    normalized_records: list[NormalizedRecord],
) -> CanonicalizationResult:
    """Canonicalize a set of NormalizedRecords into a 7-axis flavor vector.

    Strategy:
    1. Collect direct flavor_axis records: each has a numeric value and
       a verbatim_quote containing the descriptor.
    2. Collect free-text records (nose/palate/finish) and extract
       descriptor words to map via FlavorMapper.
    3. Aggregate: average all mapped values per axis (storage scale).
    4. Map unmatched descriptors → unmapped list.
    5. Produce CanonicalFlavorEvidence with per-axis provenance.

    Input scale: storage scale 0.0-1.0 (from P500-K normalizer).
    Output scale: 0.0-1.0 (same).
    """
    mapper = FlavorMapper()

    # Per-axis accumulator: list of (value, artifact_id, verbatim)
    axis_values: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    unmapped: set[str] = set()
    source_record_ids: set[str] = set()

    total_mapped_descriptors = 0
    total_unmapped = 0

    for rec in normalized_records:
        if not rec.normalized_value:
            continue
        if rec.field_type == NFT.FLAVOR_AXIS.value:
            # Direct flavor axis record — value is already on storage scale
            descriptor = _extract_descriptor(rec.verbatim_quote)
            axis = None

            # Try direct axis name match
            if descriptor in mapper.mapping:
                axis = mapper.mapping[descriptor]
            else:
                # The normalized_value itself may be numeric (the axis is already
                # identified by the field name like "smoky" or "sherry")
                # Check if the original_field_name contains an axis name
                for ax in CANONICAL_AXES:
                    if ax in rec.original_field_name.lower():
                        axis = ax
                        break

            if axis:
                try:
                    val = float(rec.normalized_value)
                except (TypeError, ValueError):
                    val = 0.0
                # Clamp to [0.0, 1.0]
                val = max(0.0, min(1.0, val))
                axis_values[axis].append((val, rec.artifact_id, rec.verbatim_quote))
                source_record_ids.add(rec.artifact_id)
                total_mapped_descriptors += 1
            else:
                unmapped.add(descriptor)
                total_unmapped += 1
                source_record_ids.add(rec.artifact_id)

        elif rec.field_type in (NFT.NOSE_TEXT.value, NFT.PALATE_TEXT.value, NFT.FINISH_TEXT.value):
            # Free-text record — extract descriptors via FlavorMapper
            raw_text = rec.normalized_value or rec.raw_value
            tokens = _tokenize(raw_text)
            bigrams = _get_bigrams(tokens)

            text_descriptors: list[str] = []
            # Longer bigrams first (more specific), then single words
            matched_in_text: set[str] = set()

            for bg in bigrams:
                bg_lower = bg.lower()
                if bg_lower in _AMBIGUOUS_TERMS or bg_lower in _STOP_WORDS:
                    continue
                axis = mapper.get_axis(bg_lower)
                if axis:
                    text_descriptors.append(bg_lower)
                    matched_in_text.add(bg_lower)

            for token in tokens:
                t_lower = token.lower()
                if t_lower in _AMBIGUOUS_TERMS or t_lower in _STOP_WORDS:
                    continue
                if t_lower in matched_in_text:
                    continue  # already handled by bigram
                axis = mapper.get_axis(t_lower)
                if axis:
                    text_descriptors.append(t_lower)
                    matched_in_text.add(t_lower)

            # For each descriptor found in text, contribute a base intensity
            # to its canonical axis. We use 0.5 as default mid-range intensity
            # since free-text doesn't carry numeric intensity.
            for desc in text_descriptors:
                axis = mapper.get_axis(desc)
                if axis:
                    axis_values[axis].append((0.5, rec.artifact_id, desc))
                    total_mapped_descriptors += 1

            source_record_ids.add(rec.artifact_id)

            # Track any descriptor-like words that were NOT mappable
            for token in tokens:
                t_lower = token.lower()
                if t_lower in _AMBIGUOUS_TERMS or t_lower in _STOP_WORDS:
                    continue
                if t_lower in matched_in_text:
                    continue
                if len(t_lower) > 2 and not mapper.get_axis(t_lower):
                    unmapped.add(t_lower)
                    total_unmapped += 1

        elif rec.field_type == NFT.RATING.value:
            pass  # rating is not a flavor axis
        else:
            pass  # other field types are not flavor-relevant

    # Build 7-axis vector: average all contributed values per axis
    vector: dict[str, float] = {}
    axis_sources: list[AxisSource] = []

    for ax in CANONICAL_AXES:
        vals = axis_values.get(ax, [])
        if vals:
            avg_val = sum(v[0] for v in vals) / len(vals)
            avg_val = max(0.0, min(1.0, avg_val))
            source_ids = tuple(sorted(set(v[1] for v in vals)))
            excerpts = tuple(v[2] for v in vals)
            axis_sources.append(AxisSource(
                axis_name=ax,
                value=avg_val,
                source_record_ids=source_ids,
                verbatim_excerpts=excerpts,
                confidence=min(1.0, len(vals) / 3.0),  # more sources = higher confidence
            ))
            vector[ax] = avg_val
        else:
            vector[ax] = 0.0
            axis_sources.append(AxisSource(
                axis_name=ax,
                value=0.0,
                source_record_ids=(),
                verbatim_excerpts=(),
                confidence=0.0,
            ))

    # Determine status
    has_any_data = any(v > 0.0 for v in vector.values())
    all_resolved = all(v > 0.0 for v in vector.values())
    num_unmapped_list = sorted(unmapped)[:50]

    if total_mapped_descriptors == 0:
        status = CanonicalizationStatus.EMPTY.value
    elif all_resolved and total_unmapped == 0:
        status = CanonicalizationStatus.RESOLVED.value
    elif has_any_data:
        status = CanonicalizationStatus.PARTIAL.value
    else:
        status = CanonicalizationStatus.EMPTY.value

    evidence = CanonicalFlavorEvidence(
        whisky_id=whisky_id,
        whisky_name=whisky_name,
        vector=vector,
        axis_sources=tuple(axis_sources),
        num_source_records=len(source_record_ids),
        num_mapped_descriptors=total_mapped_descriptors,
        num_unmapped_descriptors=len(num_unmapped_list),
        unmapped_descriptors=tuple(num_unmapped_list),
        status=status,
    )

    return CanonicalizationResult(
        whisky_id=whisky_id,
        evidence=evidence,
        status=status,
    )


# ── Batch canonicalization ────────────────────────────────────────────

def canonicalize_batch(
    records_by_whisky: dict[str, tuple[str, list[NormalizedRecord]]],
) -> list[CanonicalizationResult]:
    """Canonicalize multiple whiskies in batch.

    Input: {whisky_id: (whisky_name, [NormalizedRecord, ...])}
    Output: [CanonicalizationResult, ...]
    """
    results: list[CanonicalizationResult] = []
    for wid, (wname, recs) in records_by_whisky.items():
        try:
            result = canonicalize(wid, wname, recs)
            results.append(result)
        except Exception as e:
            results.append(CanonicalizationResult(
                whisky_id=wid,
                evidence=None,
                status=CanonicalizationStatus.CONFLICT.value,
                error_message=str(e),
            ))
    return results


# ── JSONL output ──────────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = str(_ENGINE_ROOT / "canonicalize" / "output")


def write_canonicalized_records(
    results: list[CanonicalizationResult],
    output_dir: Optional[str] = None,
) -> str:
    """Write canonicalized evidence records to JSONL output.

    Returns the output file path.
    """
    out_dir = output_dir or DEFAULT_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"canonicalized_{ts}.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for res in results:
            record = {
                "whisky_id": res.whisky_id,
                "status": res.status,
                "error_message": res.error_message,
            }
            if res.evidence:
                record["evidence"] = res.evidence.to_dict()
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    return out_path


__all__ = [
    "canonicalize", "canonicalize_batch",
    "write_canonicalized_records",
    "CANONICALIZE_VERSION", "_canon_config_hash",
]

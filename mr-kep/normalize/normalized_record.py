"""Normalized record contract — canonical NORMALIZE output (P500-K).

Input:  ExtractionRecord (flat field/value from P500-I)
Output: NormalizedRecord (structured, typed, provenance-preserving)

Each ExtractionRecord becomes one NormalizedRecord.
Records are NOT merged or aggregated — that is CANONICALIZE's job.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Optional


class NormalizedFieldType(enum.Enum):
    """Canonical field-type taxonomy for normalized values."""
    ABV = "abv"
    PRODUCT_NAME = "product_name"
    DISTILLERY_NAME = "distillery_name"
    SOURCE_IDENTIFIER = "source_identifier"
    FLAVOR_AXIS = "flavor_axis"
    NOSE_TEXT = "nose_text"
    PALATE_TEXT = "palate_text"
    FINISH_TEXT = "finish_text"
    RATING = "rating"
    AGE_STATEMENT = "age_statement"
    REGION = "region"
    COUNTRY = "country"
    CATEGORY = "category"
    BATTLING = "bottling"       # single cask, small batch, etc.
    CASK_TYPE = "cask_type"
    UNKNOWN = "unknown"


class NormalizationStatus(enum.Enum):
    NORMALIZED = "normalized"
    CONFLICT = "conflict"           # ambigous / unresolvable → manual review
    UNSUPPORTED = "unsupported"     # no normalizer for this field type
    SKIPPED = "skipped"             # empty / null after normalization


@dataclasses.dataclass(frozen=True)
class NormalizedRecord:
    """One normalized value derived from one ExtractionRecord.

    Provenance is fully preserved — each record carries its source
    artifact_id and the original verbatim quote so CANONICALIZE can
    trace back any decision.
    """

    # Source provenance (forwarded from ExtractionRecord)
    artifact_id: str
    source_type: str
    source_identifier: str
    source_uri: str

    # Original extraction provenance
    original_field_name: str
    verbatim_quote: str
    source_location: str
    content_hash: str
    extractor_version: str
    extractor_config_hash: str

    # Normalized content
    field_type: str                     # NormalizedFieldType value
    normalized_value: Optional[str]     # None = could not normalise
    raw_value: str                      # original extracted_value before normalisation
    normalization_status: str           # NormalizationStatus value
    conflict_reason: str = ""           # human-readable when status=CONFLICT

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "source_uri": self.source_uri,
            "original_field_name": self.original_field_name,
            "verbatim_quote": self.verbatim_quote,
            "source_location": self.source_location,
            "content_hash": self.content_hash,
            "extractor_version": self.extractor_version,
            "extractor_config_hash": self.extractor_config_hash,
            "field_type": self.field_type,
            "normalized_value": self.normalized_value,
            "raw_value": self.raw_value,
            "normalization_status": self.normalization_status,
            "conflict_reason": self.conflict_reason,
        }


@dataclasses.dataclass(frozen=True)
class NormalizationResult:
    """Result of normalizing one artifact's extraction records."""
    artifact_id: str
    records: tuple[NormalizedRecord, ...]
    total: int
    normalized: int
    conflicts: int
    unsupported: int
    skipped: int
    is_blocked: bool                    # True = zero normalized
    error_message: str = ""


class NormalizationError(Exception):
    """Base normalization error."""


class UnsupportedFieldError(NormalizationError):
    """No normalizer registered for this field type."""


__all__ = [
    "NormalizedRecord", "NormalizationResult",
    "NormalizedFieldType", "NormalizationStatus",
    "NormalizationError", "UnsupportedFieldError",
]

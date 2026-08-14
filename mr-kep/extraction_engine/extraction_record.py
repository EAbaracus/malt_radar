"""Extraction record contract — canonical EXTRACT output (P500-I §3).

Each ExtractionRecord represents a single structured field
extracted from a raw acquisition artifact.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
from datetime import datetime, timezone
from typing import Optional


class ExtractionStatus(enum.Enum):
    SUCCESS = "extracted"
    SKIPPED = "skipped"
    FAILED = "failed"


class ExtractorVersion(str, enum.Enum):
    """Canonical extractor version — used for determinism (P500-I §5)."""
    V1_0_0 = "extractor-v1.0.0"


EXTRACTOR_VERSION = ExtractorVersion.V1_0_0


def _extractor_config_hash() -> str:
    """Deterministic hash of extractor version + contract.

    Changes when the extractor logic or schema changes, invalidating
    previous deterministic comparisons.
    """
    raw = f"extractor={EXTRACTOR_VERSION.value}:schema=v1"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclasses.dataclass(frozen=True)
class ExtractionRecord:
    """A single extracted field from a raw artifact (P500-I §3).

    Immutable — created once and never mutated.
    """
    # Source provenance
    artifact_id: str
    source_type: str
    source_identifier: str
    source_uri: str

    # Extraction content
    field_name: str
    extracted_value: str
    verbatim_quote: str
    source_location: str        # page/row/section identifier

    # Integrity
    content_hash: str           # SHA256 of the raw artifact
    extraction_status: str      # "extracted" | "skipped" | "failed"

    # Extractor identity
    extractor_version: str = EXTRACTOR_VERSION.value
    extractor_config_hash: str = ""

    def __post_init__(self):
        if not self.extractor_config_hash:
            object.__setattr__(
                self, "extractor_config_hash", _extractor_config_hash()
            )

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "source_uri": self.source_uri,
            "field_name": self.field_name,
            "extracted_value": self.extracted_value,
            "verbatim_quote": self.verbatim_quote,
            "source_location": self.source_location,
            "content_hash": self.content_hash,
            "extraction_status": self.extraction_status,
            "extractor_version": self.extractor_version,
            "extractor_config_hash": self.extractor_config_hash,
        }


@dataclasses.dataclass(frozen=True)
class ExtractionResult:
    """Result of extracting one artifact.

    Contains all records plus summary statistics.
    """
    artifact_id: str
    artifact_path: str
    records: tuple[ExtractionRecord, ...]
    total_fields: int
    successful_fields: int
    skipped_fields: int
    failed_fields: int
    is_blocked: bool                  # True = zero successful → BLOCKED (P500-I §6)
    error_message: str = ""


class ExtractionError(Exception):
    """Base extraction error."""


class MissingArtifactError(ExtractionError):
    """Artifact file does not exist in the store."""


class InvalidArtifactIdError(ExtractionError):
    """Artifact ID is malformed or cannot be resolved."""


class CorruptArtifactError(ExtractionError):
    """Artifact exists but cannot be read or parsed."""


class UnsupportedFormatError(ExtractionError):
    """Artifact format is not supported by this extractor."""


class ZeroFieldsError(ExtractionError):
    """No fields extracted — total zero successful records."""


__all__ = [
    "ExtractionRecord", "ExtractionResult", "ExtractionStatus",
    "ExtractorVersion", "EXTRACTOR_VERSION", "_extractor_config_hash",
    "ExtractionError", "MissingArtifactError", "InvalidArtifactIdError",
    "CorruptArtifactError", "UnsupportedFormatError", "ZeroFieldsError",
]

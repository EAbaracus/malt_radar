"""Acquisition source contracts (P500-H §1).

Typed input contracts for every supported acquisition source.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Optional


class SourceType(enum.Enum):
    """Canonical source type taxonomy."""
    LOCAL_FILE = "local_file"
    CAPTURED_WEB = "captured_web"
    PDF = "pdf"
    CSV = "csv"
    EPUB = "epub"
    LIVE_WEB = "live_web"  # adapter is pending (P500-H limitation)


class SourceFormat(enum.Enum):
    """File-level format classification."""
    PDF = "application/pdf"
    CSV = "text/csv"
    EPUB = "application/epub+zip"
    HTML = "text/html"
    JSON = "application/json"
    JSONL = "application/jsonl"
    TEXT = "text/plain"
    UNKNOWN = "application/octet-stream"


SUPPORTED_SOURCE_TYPES: set[SourceType] = {
    SourceType.LOCAL_FILE,
    SourceType.CAPTURED_WEB,
    SourceType.PDF,
    SourceType.CSV,
    SourceType.EPUB,
}

SUPPORTED_FORMAT_MAP: dict[str, SourceFormat] = {
    ".pdf": SourceFormat.PDF,
    ".csv": SourceFormat.CSV,
    ".epub": SourceFormat.EPUB,
    ".html": SourceFormat.HTML,
    ".htm": SourceFormat.HTML,
    ".json": SourceFormat.JSON,
    ".jsonl": SourceFormat.JSONL,
    ".txt": SourceFormat.TEXT,
}


def detect_format(path_or_uri: str) -> SourceFormat:
    """Detect SourceFormat from a path or URI extension."""
    lower = path_or_uri.lower().rstrip()
    for ext, fmt in SUPPORTED_FORMAT_MAP.items():
        if lower.endswith(ext):
            return fmt
    return SourceFormat.UNKNOWN


@dataclasses.dataclass(frozen=True)
class SourceArtifact:
    """Immutable metadata about an acquired source (P500-H §2)."""
    artifact_id: str
    source_type: SourceType
    source_identifier: str
    source_uri: str
    sha256: str
    byte_size: int
    acquired_at: str          # ISO-8601 timestamp
    format: SourceFormat
    filename: str
    status: str               # "acquired" | "duplicate" | "rejected"

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "source_type": self.source_type.value,
            "source_identifier": self.source_identifier,
            "source_uri": self.source_uri,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "acquired_at": self.acquired_at,
            "format": self.format.value,
            "filename": self.filename,
            "status": self.status,
        }


@dataclasses.dataclass(frozen=True)
class IngestRequest:
    """Input contract for a single acquisition request (P500-H §1)."""
    source_type: SourceType
    source_identifier: str      # e.g. "whisky-advocate-2024-03"
    source_path: str            # local filesystem path
    source_uri: str = ""        # original URI if applicable
    metadata: Optional[dict] = None


class IngestError(Exception):
    """Base acquisition error."""


class SourceMissingError(IngestError):
    """Source file does not exist."""


class SourceUnreadableError(IngestError):
    """File exists but cannot be read."""


class UnsupportedFormatError(IngestError):
    """Source format is not supported."""


class DuplicateContentError(IngestError):
    """Content hash already exists in store (managed — not a failure per se)."""


class CorruptInputError(IngestError):
    """File is corrupt or has invalid structure."""


class ZeroByteInputError(IngestError):
    """File is zero bytes — rejected."""


__all__ = [
    "SourceType", "SourceFormat", "SourceArtifact", "IngestRequest",
    "SUPPORTED_SOURCE_TYPES", "SUPPORTED_FORMAT_MAP", "detect_format",
    "IngestError", "SourceMissingError", "SourceUnreadableError",
    "UnsupportedFormatError", "DuplicateContentError",
    "CorruptInputError", "ZeroByteInputError",
]

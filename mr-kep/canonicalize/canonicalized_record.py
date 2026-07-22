"""Canonical flavor evidence record — CANONICALIZE output (P500-L).

Each CanonicalFlavorEvidence represents a resolved 7-axis flavor vector
for a single entity (whisky), ready for the EVIDENCE promotion stage.

Storage scale: 0.0–1.0 (canonical for flavor_evidence table).
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Optional


# Canonical 7-axis contract (mirrors CANONICAL_AXES in domain_adapter.py)
CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]


class CanonicalizationStatus(enum.Enum):
    RESOLVED = "resolved"               # complete 7-axis vector
    PARTIAL = "partial"                  # partial vector (some axes missing)
    CONFLICT = "conflict"                # unmappable → manual review
    EMPTY = "empty"                      # no flavor data at all


@dataclasses.dataclass(frozen=True)
class AxisSource:
    """Provenance for one axis value in a canonical vector.

    Traces back to the original extraction and normalization records.
    """
    axis_name: str
    value: float                         # 0.0-1.0 storage scale
    source_record_ids: tuple[str, ...]   # artifact_ids that contributed
    verbatim_excerpts: tuple[str, ...]   # original verbatim text that produced this value
    confidence: float = 1.0              # 0.0-1.0 confidence in this axis value


@dataclasses.dataclass(frozen=True)
class CanonicalFlavorEvidence:
    """Complete 7-axis canonical flavor vector for one entity.

    This is the authoritative CANONICALIZE output that feeds the
    downstream EVIDENCE stage for promotion.
    """

    # Entity identity
    whisky_id: str
    whisky_name: str

    # 7-axis canonical vector (storage scale 0.0-1.0)
    # All 7 axes MUST be present; missing data → 0.0
    vector: dict[str, float]             # axis → 0.0-1.0

    # Provenance per axis
    axis_sources: tuple[AxisSource, ...]

    # Derivation metadata
    num_source_records: int
    num_mapped_descriptors: int
    num_unmapped_descriptors: int
    unmapped_descriptors: tuple[str, ...]

    # Status
    status: str                          # CanonicalizationStatus value
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "whisky_id": self.whisky_id,
            "whisky_name": self.whisky_name,
            "vector": self.vector,
            "axis_sources": [
                {
                    "axis_name": s.axis_name,
                    "value": s.value,
                    "source_record_ids": list(s.source_record_ids),
                    "verbatim_excerpts": list(s.verbatim_excerpts),
                    "confidence": s.confidence,
                }
                for s in self.axis_sources
            ],
            "num_source_records": self.num_source_records,
            "num_mapped_descriptors": self.num_mapped_descriptors,
            "num_unmapped_descriptors": self.num_unmapped_descriptors,
            "unmapped_descriptors": list(self.unmapped_descriptors),
            "status": self.status,
            "error_message": self.error_message,
        }


@dataclasses.dataclass(frozen=True)
class CanonicalizationResult:
    """Result of canonicalizing one entity."""
    whisky_id: str
    evidence: Optional[CanonicalFlavorEvidence]
    status: str
    error_message: str = ""


class CanonicalizationError(Exception):
    """Base canonicalization error."""


__all__ = [
    "CanonicalFlavorEvidence", "CanonicalizationResult",
    "AxisSource", "CANONICAL_AXES",
    "CanonicalizationStatus", "CanonicalizationError",
]

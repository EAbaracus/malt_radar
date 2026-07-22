"""Canonical evidence mapper — converts CanonicalFlavorEvidence (P500-L)
into flavor_evidence row format consumable by the DomainPromotionAdapter
insertion contract (P500-D).

Output row matches the EVIDENCE_INSERT_COLS ordering:
    evidence_id, whisky_id, source, vector_smoky, vector_peaty,
    vector_fruity, vector_sweet, vector_spicy, vector_maritime,
    vector_sherry, vector_rich
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

# Canonical source label for pipeline-produced evidence
EVIDENCE_SOURCE = "pipeline"

# Canonical evidence_id derivation: SHA-256(whisky_id + ":" + source)
def derive_evidence_id(whisky_id: str, source: str = EVIDENCE_SOURCE) -> str:
    """Deterministic evidence ID from (whisky_id, source)."""
    raw = f"{whisky_id}:{source}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def flavor_evidence_to_insert_cols(
    whisky_id: str,
    vector: dict[str, float],
    source: str = EVIDENCE_SOURCE,
) -> list[Any]:
    """Produce a row matching the EVIDENCE_INSERT_COLS contract.

    Order: evidence_id, whisky_id, source,
           vector_smoky, vector_peaty, vector_fruity,
           vector_sweet, vector_spicy, vector_maritime,
           vector_sherry, vector_rich

    vector_rich is set to 0.0 (not a canonical axis).
    """
    eid = derive_evidence_id(whisky_id, source)
    return [
        eid,
        whisky_id,
        source,
        vector.get("smoky", 0.0),
        vector.get("peaty", 0.0),
        vector.get("fruity", 0.0),
        vector.get("sweet", 0.0),
        vector.get("spicy", 0.0),
        vector.get("maritime", 0.0),
        vector.get("sherry", 0.0),
        0.0,  # vector_rich — not canonical
    ]


def evidence_row_to_dict(row: list[Any]) -> dict[str, Any]:
    """Convert an evidence insert row to a human-readable dict."""
    return {
        "evidence_id": row[0],
        "whisky_id": row[1],
        "source": row[2],
        "vector_smoky": row[3],
        "vector_peaty": row[4],
        "vector_fruity": row[5],
        "vector_sweet": row[6],
        "vector_spicy": row[7],
        "vector_maritime": row[8],
        "vector_sherry": row[9],
        "vector_rich": row[10],
    }

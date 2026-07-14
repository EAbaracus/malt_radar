"""
MR-KEP Certification Engine — P63/P65 deterministic certification rules.

Consumes evidence ledger entries + qualification records, applies P63
certification paths A–F, and emits certification decisions per field.

Output: per-field certification_level ∈ {certified, proposed, rejected}
and an aggregate certification_state ∈ {CERTIFIED, HOLD, REJECTED}.

HARD RULES (all frozen Sprint 1 contracts, no modification):
  - certify_min = 0.70 (authority/confidence.yaml)
  - authority ceiling per field (authority/authority_matrix.yaml)
  - certification paths A–F (resolution/certification_paths.md)
  - evidence/evidence_schema.json reused verbatim (read-only reference)
  - NO production.db write
  - NO AI/LLM/OCR/scraping
  - deterministic: same input → same output
"""
import json
import os
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple

# Repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_MRKEP = os.path.dirname(_HERE)

SCHEMA_VERSION = "1.0.0"
CERTIFY_MIN = 0.70

# Field → authority ceiling (from authority/authority_matrix.yaml)
# T1-ceiling: identity + official_bottling
# T2-ceiling: sensory_evaluation + scored_assessment
# T3-ceiling: supporting_evidence_only
FIELD_CEILING = {
    "distillery_name": "T1_authoritative",
    "region": "T1_authoritative",
    "country": "T1_authoritative",
    "abv": "T1_authoritative",
    "age_statement": "T1_authoritative",
    "cask_type": "T1_authoritative",
    "nose": "T2_expert",
    "palate": "T2_expert",
    "finish": "T2_expert",
    "flavor_axes": "T2_expert",
    "score": "T2_expert",
    "community_rating": "T3_community",
}

TIER_ORDER = {"T1_authoritative": 1, "T2_expert": 2, "T3_community": 3}


def _tier_rank(tier: Optional[str]) -> int:
    return TIER_ORDER.get(tier, 99)


def _round_conf(v: float, dp: int = 4) -> float:
    q = 10 ** dp
    return round(v * q) / q


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Certification paths (P63 resolution/certification_paths.md)
# ---------------------------------------------------------------------------
# A: Direct — T1 source for T1-ceiling field, confidence >= 0.70
# B: Corroborated — multiple independent sources agree, confidence >= 0.70
# C: Proposed — authority below ceiling (e.g. T2 for T1 field) but conf >= 0.70
# D: Conflict — unresolved conflicts present
# E: Below-threshold — confidence < 0.70
# F: Uncovered — no evidence for this field


def determine_certification_path(
    evidence_entries: List[Dict[str, Any]],
    field_name: str,
    authority_tier: Optional[str],
    confidence: float,
) -> Tuple[str, str]:
    """Return (certification_level, certification_path).

    certification_level ∈ {certified, proposed, rejected}
    certification_path ∈ {A, B, C, D, E, F}
    """
    ceiling = FIELD_CEILING.get(field_name, "T3_community")

    # Check for conflicts / non-winning evidence that was rejected
    has_conflict = False
    for e in evidence_entries:
        if e.get("merge_strategy") == "reject_on_conflict":
            has_conflict = True
            break

    # Path D: Conflict
    if has_conflict:
        return ("rejected", "D")

    # No evidence at all → Uncovered
    if not evidence_entries or confidence is None or confidence < 0.01:
        return ("rejected", "F")

    # Path E: Below-threshold
    if confidence < CERTIFY_MIN:
        return ("rejected", "E")

    # Authority check
    satisfies_ceiling = (
        authority_tier is not None
        and _tier_rank(authority_tier) <= _tier_rank(ceiling)
    )

    # Count independent sources
    source_names = set(e.get("source_name", "") for e in evidence_entries if e.get("source_name"))
    num_sources = len(source_names)

    if satisfies_ceiling and num_sources >= 1:
        return ("certified", "A")  # Direct
    elif satisfies_ceiling and num_sources == 0:
        return ("certified", "A")
    elif not satisfies_ceiling and confidence >= CERTIFY_MIN:
        return ("proposed", "C")  # Proposed-needs-cert
    else:
        return ("rejected", "E")


# ---------------------------------------------------------------------------
# Aggregate certification (entity-level)
# ---------------------------------------------------------------------------
def aggregate_certification(
    per_field: Dict[str, Dict[str, Any]]
) -> str:
    """Aggregate per-field certifications into one of:
    CERTIFIED — every field with evidence is certified
    HOLD — at least one field is 'proposed' (needs human review)
    REJECTED — at least one field is rejected (below threshold or conflict)
    """
    has_rejected = any(
        v.get("certification_level") == "rejected" for v in per_field.values()
    )
    has_hold = any(
        v.get("certification_level") == "proposed" for v in per_field.values()
    )

    if has_rejected:
        return "REJECTED"
    if has_hold:
        return "HOLD"
    return "CERTIFIED"


# ---------------------------------------------------------------------------
# Evidence helpers
# ---------------------------------------------------------------------------
def _get_field_evidence(
    ledger: List[Dict[str, Any]], field_name: str
) -> List[Dict[str, Any]]:
    """Return evidence ledger entries for a specific field."""
    return [e for e in ledger if e.get("field_name") == field_name]


def _get_source_authority(
    evidence_entries: List[Dict[str, Any]]
) -> Optional[str]:
    """Determine the highest authority tier across evidence entries."""
    tiers = [e.get("authority_tier") for e in evidence_entries if e.get("authority_tier")]
    if not tiers:
        return None
    tiers.sort(key=_tier_rank)
    return tiers[0]  # lowest rank = highest authority


# ---------------------------------------------------------------------------
# Main certification function
# ---------------------------------------------------------------------------
def certify(
    entity_key: str,
    entity_type: str,
    qualification_record: Dict[str, Any],
    evidence_ledger: List[Dict[str, Any]],
    execution_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run deterministic certification over all evidence for one entity.

    Returns a certification record matching schemas/certification.schema.json
    structure (certification.schema.json shape with per-field + audit_status).
    """
    # Collect all field names present in evidence
    field_names = sorted(set(
        e.get("field_name") for e in evidence_ledger
        if e.get("field_name") and e.get("field_value") is not None
    ))

    per_field: Dict[str, Dict[str, Any]] = {}
    all_confidences: List[float] = []

    for fn in field_names:
        field_evidence = _get_field_evidence(evidence_ledger, fn)
        # Get best confidence and authority from evidence
        confs = [e.get("confidence", 0.0) for e in field_evidence if e.get("confidence") is not None]
        confidence = max(confs) if confs else 0.0
        authority = _get_source_authority(field_evidence)

        level, path = determine_certification_path(
            field_evidence, fn, authority, confidence
        )
        all_confidences.append(confidence)

        per_field[fn] = {
            "certification_level": level,
            "certification_path": path,
            "authority_tier": authority,
            "confidence": _round_conf(confidence),
        }

    confidence_min = min(all_confidences) if all_confidences else 0.0
    aggregate = aggregate_certification(per_field)

    # Build the canonical evidence_index (subset of ledger)
    evidence_index = [
        {
            "evidence_id": e.get("evidence_id"),
            "field_name": e.get("field_name"),
            "source_class": e.get("source_class"),
            "source_name": e.get("source_name"),
        }
        for e in evidence_ledger
        if e.get("evidence_id")
    ]

    # Certification state from aggregate
    cert_state = aggregate

    run_id = (
        execution_summary.get("run_id", "sprint2-v1")
        if execution_summary
        else "sprint2-v1"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "certified_at": qualification_record.get("qualified_at", "2026-07-01T00:00:00Z"),
        "whisky_key": entity_key,
        "confidence_min": _round_conf(confidence_min),
        "confidence_overall": _round_conf(confidence_min),
        "fields": {
            fn: {
                "value": None,
                "certification_level": p["certification_level"],
                "certification_path": p["certification_path"],
                "authority_tier": p["authority_tier"],
                "confidence": p["confidence"],
            }
            for fn, p in per_field.items()
        },
        "evidence_index": evidence_index,
        "audit_status": "pending_audit",
        "certification_state": cert_state,
        "run_id": run_id,
    }
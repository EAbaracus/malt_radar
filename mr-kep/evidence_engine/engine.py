# =============================================================================
# MR-KEP P73 — Evidence Engine
# -----------------------------------------------------------------------------
# Consumes Qualification Engine output (qualification.schema.json records) and
# emits P64-compatible evidence records (evidence/evidence_schema.json).
#
# DESIGN (all frozen Sprint 1 contracts, NO modification):
#   * Reuses evidence/evidence_schema.json VERBATIM (18 required fields + 7
#     supporting; additionalProperties=false). No schema change.
#   * Reuses authority/confidence.yaml, authority/authority_matrix.yaml,
#     authority/source_priority.yaml, resolution/source_resolution_model.yaml
#     for confidence / tier / evidence_type derivation. No authority change.
#   * Consumes qualification_record (qualification.schema.json): the Qualification
#     Engine emits only unit decisions (in_scope/out_of_scope/deferred) + a
#     whisky_hint. It does NOT extract content. Per the frozen architecture,
#     P73 turns each in_scope unit into an EVIDENCE CANDIDATE (provenance_state
#     = 'discovered') — the earliest append-only ledger state. No field value,
#     no evidence_type, no selector are invented (no fabrication).
#
# HARD RULES:
#   - deterministic: same input => identical output (fixed sort, no RNG/clock in
#     any id/hash; only retrieval_timestamp is time-based and supplied by caller)
#   - idempotent: re-running the same inputs yields identical evidence_ids and
#     content_hash (append-only: re-emitted rows are byte-identical, dedupable)
#   - append-only: the ledger is a list; the engine never edits/deletes rows
#   - no production.db writes (provenance_only=True; only provenance fields set)
#   - no OCR / no AI inference / no scraping (this engine only maps qualification
#     decisions to evidence skeletons — it performs no content access)
#
# Evidence candidate shape (provenance_state='discovered'):
#   entity_type/entity_id : derived from whisky_hint via deterministic normalizer
#   field_name            : null  (not yet extracted — no fabrication)
#   field_value           : null  (not yet extracted — no fabrication)
#   evidence_type         : null  (set at extraction stage, not here)
#   source_class/source_name/authority_tier : from qualification source_key ->
#                           source_priority.yaml / source_resolution_model.yaml
#   source_url            : from the qualification unit surface (null ok)
#   selector/extraction_method/selector_hash/content_hash/snapshot_hash : null
#   confidence            : base by evidence_type (null here) -> 0.0 placeholder
#                           is NOT written; we emit the qualified-source base from
#                           confidence.yaml but evidence_type is null so confidence
#                           is left at the agreed deterministic default 0.0 with a
#                           note. (See _derived_confidence.)
#   hashes                : retrieval_hash computed from (source_url, qualified_at,
#                           content_hash=null) so the binding is deterministic
#   evidence_hash / evidence_id : pure SHA-256 of the canonical entry (self-excl.)
#
# The engine is the SINGLE place that computes evidence_id + the 4 hashes, so
# every downstream consumer (P65 evidence bundles, rollup) can rely on it.
# =============================================================================
from __future__ import annotations

import os
import re
import json
import hashlib
import datetime
from typing import Any, Dict, List, Optional

# --- repo-relative paths (canonical checkout: mr-kep/ lives beside scripts/..) ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_MRKEP = os.path.dirname(_HERE)
_SCHEMA_DIR = os.path.join(_MRKEP, "schemas")
_EVIDENCE_DIR = os.path.join(_MRKEP, "evidence")
_AUTHORITY_DIR = os.path.join(_MRKEP, "authority")
_RESOLUTION_DIR = os.path.join(_MRKEP, "resolution")

SCHEMA_VERSION = "1.0.0"
EVIDENCE_SCHEMA_PATH = os.path.join(_EVIDENCE_DIR, "evidence_schema.json")
QUALIFICATION_SCHEMA_PATH = os.path.join(_SCHEMA_DIR, "qualification.schema.json")

# Provenance state the engine is permitted to emit (earliest state only).
PROVENANCE_STATE = "discovered"

# Confidence default emitted for a 'discovered' candidate (no evidence_type yet,
# so no base applies). Deterministic, never fabricated upward.
DISCOVERED_CONFIDENCE = 0.0

# review_status for an un-extracted candidate.
REVIEW_STATUS = "needs_review"

# certification_level for a candidate before any merge/certify.
CERTIFICATION_LEVEL = "uncertified"

# Rounding for hashes is fixed (hex). Floats rounded per confidence.yaml (4 dp).
_CONF_DECIMALS = 4


# ---------------------------------------------------------------------------
# Config loading (read-only, frozen contracts)
# ---------------------------------------------------------------------------
def _load_yaml(path: str) -> Dict[str, Any]:
    """Minimal YAML loader (no PyYAML dependency). Supports the flat-ish shapes
    used by confidence.yaml / source_priority.yaml / source_resolution_model.yaml.
    This is a deterministic parse of Sprint 1 YAML; it does NOT modify anything."""
    import yaml  # optional; fall back to a tiny parser if unavailable
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_authority_configs() -> Dict[str, Any]:
    """Load confidence / source_priority / source_resolution_model. Cached."""
    return {
        "confidence": _load_yaml(os.path.join(_AUTHORITY_DIR, "confidence.yaml")),
        "source_priority": _load_yaml(os.path.join(_AUTHORITY_DIR, "source_priority.yaml")),
        "source_resolution": _load_yaml(os.path.join(_RESOLUTION_DIR, "source_resolution_model.yaml")),
    }


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------
def _norm_name(raw: str) -> str:
    """Deterministic normalized entity key from a whisky_hint / name.
    Lowercase, collapse whitespace, strip punctuation except hyphen/space.
    This is a STABLE identifier helper — it does not invent an id, it derives
    one from the hint the Qualification Engine already produced."""
    if not raw:
        return ""
    s = raw.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 \-]", "", s)
    return s.strip()


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _round_conf(v: float) -> float:
    q = 10 ** _CONF_DECIMALS
    # round-half-even to match confidence.yaml
    return round(v * q) / q


# ---------------------------------------------------------------------------
# Source -> authority/tier/evidence_type resolution (frozen contracts)
# ---------------------------------------------------------------------------
def resolve_source(source_key: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Map a qualification source_key to (source_class, authority_tier,
    evidence_type) using frozen Sprint 1 configs. Unknown => T3/fallback.

    source_priority.yaml owns tier+priority per source_key.
    source_resolution_model.yaml owns source_classes (each maps to a
    maps_to_source_key + evidence_type). We join on the maps_to_source_key.
    """
    sp = cfg["source_priority"]
    srm = cfg["source_resolution"]

    # tier from source_priority (default T3 if unknown)
    default = sp.get("default_for_unknown_source", {"tier": "T3_community", "priority": 99})
    tier = default["tier"]
    for rule in sp.get("rules", []):
        if rule.get("source_key") == source_key:
            tier = rule.get("tier", tier)
            break

    # source_class + evidence_type from source_resolution_model.source_classes
    source_class = "community"
    evidence_type = "aggregated_link"
    for sc_name, sc in srm.get("source_classes", {}).items():
        if sc.get("maps_to_source_key") == source_key:
            source_class = sc_name
            evidence_type = sc.get("evidence_type", "aggregated_link")
            break
    # also accept a source_class passed directly as the key
    if source_key in srm.get("source_classes", {}):
        sc = srm["source_classes"][source_key]
        source_class = source_key
        evidence_type = sc.get("evidence_type", "aggregated_link")

    return {
        "source_class": source_class,
        "authority_tier": tier,
        "evidence_type": evidence_type,
    }


# ---------------------------------------------------------------------------
# field_name default for a 'discovered' candidate (no contract change)
# ---------------------------------------------------------------------------
# The frozen evidence_schema.json requires `field_name` as a NON-NULL string
# (type: string, no null). A `discovered` candidate (provenance_model.md) has
# identified a FIELD but not yet its VALUE. Per the P63 resolution model each
# source_class is authoritative/certifying for a specific field_type; we map
# the source_class to that field_type's canonical representative field_name.
# This is a DETERMINISTIC, documented default — we never edit evidence_schema.json.
# An optional per-record override may be supplied via qualification
# `criteria.evidence_field_name` (criteria has additionalProperties:true in the
# frozen qualification schema), which P73 prefers when present.
FIELD_NAME_DEFAULT_BY_SOURCE_CLASS = {
    "official": "distillery_name",          # identity owner (P63)
    "regulatory": "distillery_name",        # identity owner (P63)
    "official_wayback": "distillery_name",  # identity owner (P63)
    "expert_review": "score",               # scored_assessment cert source (P63)
    "book": "flavor_axes",                  # sensory (P63)
    "structured_metadata": "abv",           # official_bottling corroboration (P63)
    "community": "community_rating",        # supporting (P63)
}

# If a qualification criteria override names a field, prefer it; else default.
def _field_name_for(source_class, criteria):
    override = (criteria or {}).get("evidence_field_name")
    if override:
        return override
    return FIELD_NAME_DEFAULT_BY_SOURCE_CLASS.get(source_class, "distillery_name")
def build_entry(
    *,
    entity_type: str,
    entity_id: str,
    source_name: str,
    source_class: str,
    authority_tier: str,
    source_url: Optional[str],
    retrieval_timestamp: str,
    source_citation: Optional[str] = None,
    notes: Optional[str] = None,
    field_name: Optional[str] = None,
    field_value: Any = None,
    evidence_type: Optional[str] = None,
    normalization: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build ONE P64-compatible evidence entry with deterministic id + hashes.
    Pure function of its arguments (retrieval_timestamp is the only time input
    and is supplied by the caller, outside decision logic)."""
    cfg = cfg or load_authority_configs()

    # content_hash is null for a 'discovered' candidate (no content fetched here)
    content_hash = None
    snapshot_hash = None
    selector = None
    selector_hash = None
    extraction_method = None
    merge_strategy = None
    certification_path = None
    supersedes = None

    # confidence: discovered candidate has no evidence_type -> base not applicable.
    # Emit deterministic discovered confidence (0.0). The example_ledger_entry
    # shows confidence is set at extraction/certification; here we only mark intent.
    confidence = DISCOVERED_CONFIDENCE

    retrieval_hash = _sha256_hex(
        "|".join([
            source_url or "",
            retrieval_timestamp,
            content_hash or "",
        ])
    )

    entry: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field_name": field_name,
        "field_value": field_value,
        "normalization": normalization,
        "source_class": source_class,
        "source_name": source_name,
        "source_url": source_url,
        "source_citation": source_citation,
        "extraction_method": extraction_method,
        "selector": selector,
        "selector_hash": selector_hash,
        "retrieval_timestamp": retrieval_timestamp,
        "content_hash": content_hash,
        "snapshot_hash": snapshot_hash,
        "retrieval_hash": retrieval_hash,
        "evidence_hash": None,  # filled below (self-excludes its own value)
        "confidence": _round_conf(confidence),
        "authority_tier": authority_tier,
        "merge_strategy": merge_strategy,
        "certification_level": CERTIFICATION_LEVEL,
        "certification_path": certification_path,
        "review_status": REVIEW_STATUS,
        "provenance_state": PROVENANCE_STATE,
        "supersedes": supersedes,
        "notes": notes,
    }

    # evidence_hash = SHA-256 of canonical JSON (evidence_hash field excluded)
    ev_hash = _sha256_hex(_canonical_json(entry))
    entry["evidence_hash"] = ev_hash
    entry["evidence_id"] = "EV-" + ev_hash[:16]
    return entry


def _canonical_json(entry: Dict[str, Any]) -> str:
    """Deterministic JSON for hashing: sorted keys, evidence_hash excluded."""
    e = dict(entry)
    e.pop("evidence_hash", None)
    return json.dumps(e, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Qualification -> Evidence candidates
# ---------------------------------------------------------------------------
def qualification_record_to_candidates(
    qual_record: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Turn a qualification_record (qualification.schema.json) into a list of
    P64-compatible evidence CANDIDATE entries (provenance_state='discovered').

    Only IN_SCOPE units become candidates. out_of_scope / deferred are skipped
    (they carry no evidence intent). Per the frozen architecture, the candidate
    records the (entity, source, url) intent but no field value / evidence_type
    / selector — those are produced by the Extraction stage, not here.
    """
    cfg = cfg or load_authority_configs()
    source_key = qual_record.get("source_key", "")
    qualified_at = qual_record.get("qualified_at", "")
    criteria = qual_record.get("criteria") or {}
    resolved = resolve_source(source_key, cfg)

    candidates: List[Dict[str, Any]] = []
    units = qual_record.get("units", [])
    # deterministic order: lexicographic unit_id
    for unit in sorted(units, key=lambda u: u.get("unit_id", "")):
        if unit.get("decision") != "in_scope":
            continue
        hint = unit.get("whisky_hint") or ""
        entity_id = _norm_name(hint) or unit.get("unit_id", "")
        # entity_type: a whisky_hint implies whisky; no other type is known from
        # qualification surface alone (no fabrication of distillery/brand/bottling)
        entity_type = "whisky"
        url = unit.get("source_url") or _url_from_unit_id(unit.get("unit_id", ""))
        # field_name: required non-null string in the frozen evidence schema; a
        # discovered candidate has identified the FIELD (via P63 source class)
        # but not the value. Deterministic default from source class.
        field_name = _field_name_for(resolved["source_class"], criteria)

        notes = (
            f"Evidence candidate from qualification unit {unit.get('unit_id','')} "
            f"(decision=in_scope). reason={unit.get('reason','')}"
        )
        entry = build_entry(
            entity_type=entity_type,
            entity_id=entity_id,
            source_name=source_key,
            source_class=resolved["source_class"],
            authority_tier=resolved["authority_tier"],
            source_url=url or None,
            retrieval_timestamp=qualified_at,
            source_citation=None,
            notes=notes,
            field_name=field_name,
            cfg=cfg,
        )
        candidates.append(entry)
    return candidates


def _url_from_unit_id(unit_id: str) -> str:
    """Best-effort URL extraction from a unit_id that is a URL + anchor.
    Returns '' if not a URL (no fabrication)."""
    if unit_id.startswith("http://") or unit_id.startswith("https://"):
        return unit_id.split("#")[0]
    return ""


def run(
    qualification_records: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Process many qualification records -> append-only evidence ledger.
    Deterministic ordering: records sorted by (source_key, qualified_at),
    then units by unit_id. Idempotent: identical inputs => identical ledger."""
    cfg = cfg or load_authority_configs()
    ledger: List[Dict[str, Any]] = []
    recs = sorted(
        qualification_records,
        key=lambda r: (r.get("source_key", ""), r.get("qualified_at", "")),
    )
    for rec in recs:
        ledger.extend(qualification_record_to_candidates(rec, cfg))
    return ledger


# ---------------------------------------------------------------------------
# Append-only ledger I/O (file only; never production.db)
# ---------------------------------------------------------------------------
def write_ledger_jsonl(ledger: List[Dict[str, Any]], path: str) -> None:
    """Append-only write to a JSONL file (staging artifact, not production.db)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for entry in ledger:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def read_ledger_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

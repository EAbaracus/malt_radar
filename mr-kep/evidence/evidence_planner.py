"""Canonical EVIDENCE pipeline (P500-M).

Converts canonicalized flavor evidence (P500-L) into promotion-ready
flavor_evidence rows. Produces a deterministic promotion plan for
downstream QA → PromotionGate.

Read-only: no writes to production.db.
INSERT-only: (whisky_id, source) duplicates are detected and skipped.
Unresolved entities fail closed.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Version ────────────────────────────────────────────────────────────

EVIDENCE_PIPELINE_VERSION = "evidence-v1.0.0"

# Canonical source label for pipeline-produced evidence
EVIDENCE_SOURCE = "pipeline"

# ── Plan record types ─────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class EvidenceInsert:
    """One evidence row ready for insertion."""
    whisky_id: str
    evidence_id: str
    source: str
    insert_row: list[Any]          # matches EVIDENCE_INSERT_COLS order
    vector: dict[str, float]       # canonical 7-axis
    provenance_json: str           # serialized AxisSource provenance
    confidence: float

    def to_dict(self) -> dict:
        return {
            "whisky_id": self.whisky_id,
            "evidence_id": self.evidence_id,
            "source": self.source,
            "insert_row": self.insert_row,
            "vector": self.vector,
            "confidence": self.confidence,
            "provenance_json": self.provenance_json,
        }


@dataclasses.dataclass(frozen=True)
class EvidenceSkip:
    """One skipped evidence row (duplicate or existing)."""
    whisky_id: str
    evidence_id: str
    reason: str


@dataclasses.dataclass(frozen=True)
class EvidenceConflict:
    """One conflicting/blocked evidence row."""
    whisky_id: str
    evidence_id: str
    reason: str
    detail: str = ""


@dataclasses.dataclass(frozen=True)
class PromotionPlan:
    """Deterministic promotion plan — staging output only.

    This is separate from the KEP Runtime PromotionPlan;
    this is the evidence-stage plan that feeds QA → PromotionGate.
    """
    inserts: tuple[EvidenceInsert, ...]
    skips: tuple[EvidenceSkip, ...]
    conflicts: tuple[EvidenceConflict, ...]
    num_unresolved_skipped: int    # 8 rows from P500-J lacking whisky_id
    num_quality_rejected_flagged: int  # 60 rows flagged for QA
    pipeline_version: str = EVIDENCE_PIPELINE_VERSION
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at",
                               datetime.now(timezone.utc).isoformat())

    @property
    def plan_hash(self) -> str:
        h = hashlib.sha256()
        for ins in self.inserts:
            h.update(f"INS:{ins.evidence_id}:{ins.whisky_id}\n".encode())
        for sk in self.skips:
            h.update(f"SKP:{sk.evidence_id}:{sk.reason}\n".encode())
        for cf in self.conflicts:
            h.update(f"CFL:{cf.evidence_id}:{cf.reason}\n".encode())
        return h.hexdigest()[:16]

    @property
    def summary(self) -> dict:
        return {
            "inserts": len(self.inserts),
            "skips": len(self.skips),
            "conflicts": len(self.conflicts),
            "unresolved_skipped": self.num_unresolved_skipped,
            "quality_rejected_flagged": self.num_quality_rejected_flagged,
            "plan_hash": self.plan_hash,
            "pipeline_version": self.pipeline_version,
            "created_at": self.created_at,
        }


# ── Evidence planner — P500-L CanonicalFlavorEvidence → PromotionPlan ──

def _set_uuid_to_production_whisky_ids(
    production_db: str,
) -> set[str]:
    """Read all production whisky_id values into a set for FK validation.

    whisky_ids are UUIDs (text)."""
    if not os.path.exists(production_db):
        return set()
    conn = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT whisky_id FROM whiskies").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _existing_evidence_keys(
    production_db: str,
) -> set[tuple[str, str]]:
    """Return set of (whisky_id, source) pairs already in production."""
    if not os.path.exists(production_db):
        return set()
    conn = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT whisky_id, source FROM flavor_evidence"
        ).fetchall()
        return {(r[0], r[1]) for r in rows}
    finally:
        conn.close()


def plan(
    evidence_candidates: list[dict],
    production_db: str,
    quality_rejected_whisky_ids: Optional[set[str]] = None,
    unresolved_whisky_ids: Optional[set[str]] = None,
    source: str = EVIDENCE_SOURCE,
) -> PromotionPlan:
    """Build a deterministic promotion plan from canonical evidence candidates.

    This is the single canonical EVIDENCE entry point.

    Args:
        evidence_candidates: List of dicts, each containing:
            whisky_id : str
            whisky_name : str (optional, for logging)
            vector : dict[str, float]  — canonical 7-axis
            axis_sources : list[dict] — P500-L AxisSource provenance
            status : str — CanonicalizationStatus value
            num_source_records : int
            num_mapped_descriptors : int
            num_unmapped_descriptors : int
            unmapped_descriptors : list[str]
        production_db: Path to production.db (read-only).
        quality_rejected_whisky_ids: Set of whisky_ids that were in the
            staging_quality_rejected group; surfaced for downstream QA.
        unresolved_whisky_ids: Set of whisky_ids that lack production FK.
        source: Source label for this pipeline evidence.

    Returns:
        PromotionPlan with inserts, skips, conflicts.
    """
    valid_whisky_ids = _set_uuid_to_production_whisky_ids(production_db)
    existing_keys = _existing_evidence_keys(production_db)
    qr_set = quality_rejected_whisky_ids or set()
    unresolved_set = unresolved_whisky_ids or set()

    from evidence_mapper import derive_evidence_id, flavor_evidence_to_insert_cols, evidence_row_to_dict

    inserts: list[EvidenceInsert] = []
    skips: list[EvidenceSkip] = []
    conflicts: list[EvidenceConflict] = []
    unresolved_count = 0
    qr_flagged_count = 0
    inserted_keys: set[tuple[str, str]] = set()  # intra-batch dedup

    for candidate in evidence_candidates:
        wid = candidate.get("whisky_id", "")
        wname = candidate.get("whisky_name", wid)
        vector = candidate.get("vector", {})
        status = candidate.get("status", "empty")
        axis_sources = candidate.get("axis_sources", [])
        unmapped = candidate.get("unmapped_descriptors", [])
        num_src = candidate.get("num_source_records", 0)
        num_mapped = candidate.get("num_mapped_descriptors", 0)

        # ── R1: unresolved whisky_id → SKIP ────────────────────────────
        if wid in unresolved_set or wid not in valid_whisky_ids:
            unresolved_count += 1
            skips.append(EvidenceSkip(
                whisky_id=wid,
                evidence_id=derive_evidence_id(wid, source),
                reason="unresolved_whisky_id — no FK in production whiskies table",
            ))
            continue

        # ── R2: EMPTY or CONFLICT status → CONFLICT ────────────────────
        if status in ("empty", "conflict"):
            _eid = derive_evidence_id(wid, source)
            conflicts.append(EvidenceConflict(
                whisky_id=wid,
                evidence_id=_eid,
                reason=f"evidence_status_is_{status}",
                detail=f"whisky={wname} has status={status}; "
                       f"num_source_records={num_src}, mapped={num_mapped}",
            ))
            continue

        # ── R3: duplicate (whisky_id, source) → SKIP ───────────────────
        if (wid, source) in existing_keys:
            _eid = derive_evidence_id(wid, source)
            skips.append(EvidenceSkip(
                whisky_id=wid,
                evidence_id=_eid,
                reason="duplicate_whisky_source_pair — already in flavor_evidence (INSERT-only)",
            ))
            continue

        # ── R3b: intra-batch duplicate → SKIP ─────────────────────────
        if (wid, source) in inserted_keys:
            _eid = derive_evidence_id(wid, source)
            skips.append(EvidenceSkip(
                whisky_id=wid,
                evidence_id=_eid,
                reason="duplicate_whisky_source_pair — intra-batch duplicate (already planned)",
            ))
            continue

        # ── Quality-rejected flag ──────────────────────────────────────
        if wid in qr_set:
            qr_flagged_count += 1

        # ── Build evidence row ────────────────────────────────────────
        eid = derive_evidence_id(wid, source)
        insert_row = flavor_evidence_to_insert_cols(wid, vector, source)

        # Build provenance JSON from AxisSource data
        provenance = {
            "pipeline": EVIDENCE_PIPELINE_VERSION,
            "source": source,
            "axis_sources": axis_sources,
            "num_source_records": num_src,
            "num_mapped_descriptors": num_mapped,
            "unmapped_descriptors": list(unmapped),
        }
        provenance_json = json.dumps(provenance, ensure_ascii=False, sort_keys=True)

        # Compute confidence: average of axis source confidences, or 0
        confidences = [s.get("confidence", 0.0) for s in axis_sources if s.get("confidence")]
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        inserts.append(EvidenceInsert(
            whisky_id=wid,
            evidence_id=eid,
            source=source,
            insert_row=insert_row,
            vector=vector,
            provenance_json=provenance_json,
            confidence=confidence,
        ))
        inserted_keys.add((wid, source))

    return PromotionPlan(
        inserts=tuple(inserts),
        skips=tuple(skips),
        conflicts=tuple(conflicts),
        num_unresolved_skipped=unresolved_count,
        num_quality_rejected_flagged=qr_flagged_count,
    )


# ── Output ─────────────────────────────────────────────────────────────

_DEFAULT_OUTPUT_DIR = str(Path(__file__).resolve().parent / "output")


def write_plan(
    plan: PromotionPlan,
    output_dir: Optional[str] = None,
) -> str:
    """Write the promotion plan to structured JSON files.

    output_dir/evidence_promotion_plan_<ts>.json contains the full plan.
    Returns the directory path.
    """
    out_dir = output_dir or _DEFAULT_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"evidence_promotion_plan_{ts}"

    # Plan summary
    plan_data = {
        "plan": plan.summary,
        "plan_hash": plan.plan_hash,
        "pipeline_version": plan.pipeline_version,
        "created_at": plan.created_at,
        "inserts": [ins.to_dict() for ins in plan.inserts],
        "skips": [
            {"whisky_id": sk.whisky_id, "evidence_id": sk.evidence_id, "reason": sk.reason}
            for sk in plan.skips
        ],
        "conflicts": [
            {"whisky_id": cf.whisky_id, "evidence_id": cf.evidence_id,
             "reason": cf.reason, "detail": cf.detail}
            for cf in plan.conflicts
        ],
    }

    plan_path = os.path.join(out_dir, f"{base}.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2, sort_keys=True)

    # Separate insert rows JSONL (for direct DB insertion downstream)
    inserts_path = os.path.join(out_dir, f"{base}_inserts.jsonl")
    with open(inserts_path, "w", encoding="utf-8") as f:
        for ins in plan.inserts:
            f.write(json.dumps(ins.insert_row, ensure_ascii=False) + "\n")

    # Print summary to stdout
    print(f"Evidence Promotion Plan: {plan_path}")
    print(f"  Inserts: {len(plan.inserts)}")
    print(f"  Skips:   {len(plan.skips)}")
    print(f"  Conflicts: {len(plan.conflicts)}")
    print(f"  Unresolved skipped: {plan.num_unresolved_skipped}")
    print(f"  Quality-rejected flagged: {plan.num_quality_rejected_flagged}")
    print(f"  Plan hash: {plan.plan_hash}")

    return out_dir


def write_plan_deterministic(
    plan: PromotionPlan,
    output_dir: Optional[str] = None,
    label: str = "p500m",
) -> str:
    """Write promotion plan to a deterministic file path (overwrite).

    Useful for CI/verification where the output path must be known.
    Returns the output JSON path.
    """
    out_dir = output_dir or _DEFAULT_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    plan_path = os.path.join(out_dir, f"{label}_plan.json")
    inserts_path = os.path.join(out_dir, f"{label}_inserts.jsonl")

    plan_data = {
        "plan": plan.summary,
        "plan_hash": plan.plan_hash,
        "pipeline_version": plan.pipeline_version,
        "created_at": plan.created_at,
        "inserts": [ins.to_dict() for ins in plan.inserts],
        "skips": [
            {"whisky_id": sk.whisky_id, "evidence_id": sk.evidence_id, "reason": sk.reason}
            for sk in plan.skips
        ],
        "conflicts": [
            {"whisky_id": cf.whisky_id, "evidence_id": cf.evidence_id,
             "reason": cf.reason, "detail": cf.detail}
            for cf in plan.conflicts
        ],
    }
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(inserts_path, "w", encoding="utf-8") as f:
        for ins in plan.inserts:
            f.write(json.dumps(ins.insert_row, ensure_ascii=False) + "\n")
    return plan_path


__all__ = [
    "plan", "write_plan", "write_plan_deterministic",
    "PromotionPlan", "EvidenceInsert", "EvidenceSkip", "EvidenceConflict",
    "EVIDENCE_PIPELINE_VERSION", "EVIDENCE_SOURCE",
]

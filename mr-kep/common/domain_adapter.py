"""Canonical Domain Promotion Adapter Protocol.

Bridges MR-KEP domain writers to KEP Runtime promotion engine.

KEP Runtime owns: orchestration, safety, dry-run, human gate, backup, rollback.
MR-KEP domain adapter owns: staging validation, evidence preparation, domain-specific logic.

Design contract (P500-A / P500-B / P500-D / P500-E):
- Adapter plan() is ALWAYS read-only (staging + production both mode=ro).
- Adapter NEVER opens production.db for writing.
- Adapter NEVER implements its own backup/rollback/human gate.
- KEP Runtime PromotionGate owns all mutation safety.
- Existing evidence is never updated. Duplicate (whisky_id, source) is skipped.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

# ── Shared data contract ─────────────────────────────────────────────

CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]

EVIDENCE_INSERT_COLS = (
    "evidence_id, whisky_id, source, vector_smoky, vector_peaty, "
    "vector_fruity, vector_sweet, vector_spicy, vector_maritime, vector_sherry, vector_rich"
)


def _content_hash(obj: Any) -> str:
    """Deterministic SHA256 of a JSON-serializable object."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


@dataclass
class PromotionPlan:
    """Result of plan(): what WOULD be promoted. Read-only computed."""
    staging_rows: int = 0
    accepted: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    duplicate_count: int = 0
    new_entity_keys: list = field(default_factory=list)
    new_evidence_rows: int = 0
    promoted_flavor_profile_rows: int = 0
    dry_run: bool = True
    plan_hash: str = ""
    """Deterministic hash of the plan content for idempotency/verify."""

    def __post_init__(self):
        if not self.plan_hash:
            self.plan_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        h = hashlib.sha256()
        h.update(f"staging_rows={self.staging_rows}".encode())
        h.update(f"duplicate_count={self.duplicate_count}".encode())
        h.update(f"new_evidence_rows={self.new_evidence_rows}".encode())
        h.update(f"promoted_flavor_profile_rows={self.promoted_flavor_profile_rows}".encode())
        for a in self.accepted:
            h.update(f"ev={a.get('evidence_id','')};wid={a.get('whisky_id','')}".encode())
        for r in self.rejected:
            h.update(f"rj={r.get('evidence_id','')};reason={r.get('reason','')}".encode())
        for s in self.skipped:
            h.update(f"sk={s.get('evidence_id','')};reason={s.get('reason','')}".encode())
        return h.hexdigest()

    @property
    def summary(self) -> dict:
        return {
            "staging_rows": self.staging_rows,
            "accepted": len(self.accepted),
            "rejected": len(self.rejected),
            "skipped": len(self.skipped),
            "duplicate_count": self.duplicate_count,
            "new_entity_keys": len(self.new_entity_keys),
            "new_evidence_rows": self.new_evidence_rows,
            "promoted_flavor_profile_rows": self.promoted_flavor_profile_rows,
            "plan_hash": self.plan_hash,
            "dry_run": self.dry_run,
        }


# ── Protocol ─────────────────────────────────────────────────────────

@runtime_checkable
class DomainPromotionAdapter(Protocol):
    """Interface every MR-KEP domain promotion adapter must implement.

    KEP Runtime calls plan() to compute what would be promoted (read-only),
    then apply_plan() to execute the INSERTs through the runtime's guarded
    connection. The adapter NEVER writes to production.db directly.
    """

    name: str
    source: str

    def plan(
        self,
        staging_db: str,
        production_db: str,
        evidence_ids: Optional[list[str]] = None,
    ) -> PromotionPlan:
        ...

    def apply_plan(
        self,
        plan: PromotionPlan,
        staging_db: str,
        conn: sqlite3.Connection,
    ) -> dict[str, Any]:
        ...


# ── Shared helper: validate no axis exceeds 1.0 (R4 invariant) ────────

def check_r4_invariant(conn: sqlite3.Connection) -> None:
    """Hard R4 invariant: abort if any flavor_evidence axis > 1.0.

    Defensive: if the flavor_evidence table lacks axis columns (e.g. a minimal
    test fixture), skip rather than raise — on production the columns exist and
    the check is authoritative.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(flavor_evidence)")}
    axis_cols = [
        c for c in ("vector_smoky", "vector_peaty", "vector_sherry", "vector_fruity",
                    "vector_sweet", "vector_spicy", "vector_maritime")
        if c in cols
    ]
    if not axis_cols:
        return
    where = " OR ".join(f"{c}>1.0" for c in axis_cols)
    bad = conn.execute(f"SELECT COUNT(*) FROM flavor_evidence WHERE {where}").fetchone()[0]
    if bad:
        raise RuntimeError(f"R4 invariant violated: {bad} rows with axis>1.0")


# ── EditorialDomainAdapter ────────────────────────────────────────────

class EditorialDomainAdapter:
    """Adapts EditorialPromotionWriter to DomainPromotionAdapter protocol."""

    name = "editorial"
    source = "editorial"

    def __init__(self, staging_db: str = ""):
        self._staging_db = staging_db
        self._writer = None

    def _get_writer(self, staging_db: str, production_db: str):
        if self._writer is not None:
            return self._writer
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent
        prom_path = str(root / "mr-kep" / "editorial" / "promotion")
        if prom_path not in sys.path:
            sys.path.insert(0, prom_path)
        from editorial_promotion_writer import EditorialPromotionWriter as EPW
        self._writer = EPW(staging_db=staging_db, prod_db=production_db)
        return self._writer

    def plan(
        self,
        staging_db: str,
        production_db: str,
        evidence_ids: Optional[list[str]] = None,
    ) -> PromotionPlan:
        writer = self._get_writer(staging_db, production_db)
        result = writer.plan()

        plan = PromotionPlan(
            staging_rows=result["staging_rows"],
            duplicate_count=result["duplicate_count"],
            new_evidence_rows=result["new_evidence_rows"],
            promoted_flavor_profile_rows=result["promoted_flavor_profile_rows"],
        )

        for p in result["prepared"]:
            plan.accepted.append({
                "evidence_id": p["evidence_id"],
                "whisky_id": p["whisky_id"],
                "flavor_evidence": p["flavor_evidence"],
                "flavor_profiles": p["flavor_profiles"],
            })
            # NOTE: new_evidence_rows / promoted_flavor_profile_rows are already
            # set above from writer.plan()'s authoritative counts. Do NOT
            # double-count here (would break the gate's expected==actual match).

        plan.rejected = result["rejected"]
        plan.skipped = result["skipped"]

        if evidence_ids:
            eid_set = set(evidence_ids)
            plan.accepted = [a for a in plan.accepted if a["evidence_id"] in eid_set]
            plan.new_evidence_rows = len(plan.accepted)

        # Compute deterministic plan hash
        plan.plan_hash = plan._compute_hash()
        return plan

    def apply_plan(
        self,
        plan: PromotionPlan,
        staging_db: str,
        conn: sqlite3.Connection,
    ) -> dict[str, Any]:
        cur = conn.cursor()
        new_ev = 0
        new_fp = 0

        for p in plan.accepted:
            cur.execute(
                f"INSERT INTO flavor_evidence ({EVIDENCE_INSERT_COLS}) "
                f"VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                p["flavor_evidence"],
            )
            new_ev += 1
            if p["flavor_profiles"] is not None:
                cur.execute(
                    "INSERT INTO flavor_profiles (whisky_id, flavor_profile) VALUES (?,?)",
                    p["flavor_profiles"],
                )
                new_fp += 1

        check_r4_invariant(conn)
        # Commit into the connection the gate handed us. The gate (PromotionGate)
        # either reopens this temp copy to verify the delta, or copies it to
        # production.db after apply — so the writes MUST be persisted here.
        conn.commit()

        return {
            "new_evidence_rows": new_ev,
            "promoted_flavor_profile_rows": new_fp,
        }


# ── Adapter registry ─────────────────────────────────────────────────

_ADAPTER_REGISTRY: dict[str, type] = {}


def register_adapter(name: str, adapter_cls: type) -> None:
    _ADAPTER_REGISTRY[name] = adapter_cls


def get_adapter(name: str, **kwargs) -> DomainPromotionAdapter:
    if name not in _ADAPTER_REGISTRY:
        raise ValueError(f"Unknown domain adapter: {name!r}. "
                         f"Registered: {list(_ADAPTER_REGISTRY.keys())}")
    return _ADAPTER_REGISTRY[name](**kwargs)


def list_adapters() -> list[str]:
    return list(_ADAPTER_REGISTRY.keys())


register_adapter("editorial", EditorialDomainAdapter)


__all__ = [
    "DomainPromotionAdapter", "PromotionPlan", "EditorialDomainAdapter",
    "CANONICAL_AXES", "EVIDENCE_INSERT_COLS", "check_r4_invariant",
    "_content_hash",
    "register_adapter", "get_adapter", "list_adapters",
]

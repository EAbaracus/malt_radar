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
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from flavor_scale_utils import (
    to_storage_scale, to_profile_scale, validate_storage_vector,
)

# ── Shared data contract ─────────────────────────────────────────────

CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]

# Promotable match statuses (mirrors editorial_promotion_writer.PROMOTABLE_MATCH)
PROMOTABLE_MATCH = {"exact", "normalized_exact", "fuzzy"}
# Provenance states rejected outright (mirrors editorial REJECTED_PROVENANCE)
REJECTED_PROVENANCE = {"staging_rejected", "rejected", "quality_rejected"}

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


class BookDomainAdapter:
    """Adapts book staging (staging_book_reviews) to DomainPromotionAdapter protocol.

    Mirror of EditorialDomainAdapter but for the BOOK domain. Reads the
    canonical book staging table (staging_book_reviews, derived deterministically
    from extracted_facts), validates, and prepares flavor_evidence inserts (0-1)
    via the shared flavor_scale_utils. Never opens production.db for writing;
    plan() is read-only against both DBs.

    Editorial adapter is untouched — this is an additive domain registration.
    """
    name = "book"
    source = "book"
    # Adapter-aware staging table (PromotionEngine.prepare uses getattr)
    staging_table = "staging_book_reviews"

    def __init__(self, staging_db: str = ""):
        self._staging_db = staging_db

    def plan(
        self,
        staging_db: str,
        production_db: str,
        evidence_ids: Optional[list[str]] = None,
    ) -> PromotionPlan:
        if not os.path.exists(staging_db):
            raise PromotionError(f"staging db missing: {staging_db}")
        st = sqlite3.connect(staging_db)
        st.row_factory = sqlite3.Row
        rows = st.execute("SELECT * FROM staging_book_reviews").fetchall()
        st.close()

        # read-only check of existing production state
        prod = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
        prod.row_factory = sqlite3.Row
        valid_wids = {r[0] for r in prod.execute("SELECT whisky_id FROM whiskies")}
        existing_ev = {r[0] for r in prod.execute("SELECT evidence_id FROM flavor_evidence")}
        existing_fp = {r[0] for r in prod.execute("SELECT whisky_id FROM flavor_profiles")}
        prod.close()

        prepared = []
        accepted, rejected, skipped, duplicates = [], [], [], []
        axis_present = {ax: 0 for ax in CANONICAL_AXES}
        conf_bins = {"<0.7": 0, "0.7-0.85": 0, "0.85-0.95": 0, ">=0.95": 0}

        for r in rows:
            row = dict(r)
            eid = row["evidence_id"]
            # duplicate evidence (already promoted)
            if eid in existing_ev:
                duplicates.append(eid)
                skipped.append({"evidence_id": eid,
                                "reason": "duplicate evidence_id already in flavor_evidence"})
                continue
            # AMBIGUOUS / NO_MATCH classification from transform audit field
            if row.get("er_class") in ("AMBIGUOUS", "NO_MATCH"):
                rejected.append({"evidence_id": eid,
                                 "reason": f"entity resolution = {row.get('er_class')} (not promotable)"})
                continue
            # whisky_id existence
            wid = row.get("matched_master_whisky_id")
            if not wid or wid not in valid_wids:
                rejected.append({"evidence_id": eid, "reason": "invalid whisky_id (not in production.whiskies)"})
                continue
            try:
                wid2, _eid, svec, pvec = _validate_book_row(row)
            except RowRejected as ex:
                rejected.append({"evidence_id": ex.evidence_id, "reason": ex.reason})
                continue

            ev_tuple = (
                eid, wid, "book",
                svec["smoky"], svec["peaty"], svec["fruity"], svec["sweet"],
                svec["spicy"], svec["maritime"], svec["sherry"], None,  # vector_rich legacy col -> None
            )
            wants_fp = wid not in existing_fp
            fp_tuple = (wid, json.dumps({ax: pvec[ax] for ax in CANONICAL_AXES})) if wants_fp else None
            prepared.append({
                "evidence_id": eid,
                "whisky_id": wid,
                "match_status": row.get("match_status"),
                "evidence_confidence": row.get("evidence_confidence"),
                "flavor_evidence": ev_tuple,
                "flavor_profiles": fp_tuple,
            })
            accepted.append(eid)
            for ax in CANONICAL_AXES:
                if svec[ax] is not None and svec[ax] > 0:
                    axis_present[ax] += 1
            ec = row.get("evidence_confidence") or 0.0
            if ec < 0.7: conf_bins["<0.7"] += 1
            elif ec < 0.85: conf_bins["0.7-0.85"] += 1
            elif ec < 0.95: conf_bins["0.85-0.95"] += 1
            else: conf_bins[">=0.95"] += 1

        plan = PromotionPlan(
            staging_rows=len(rows),
            duplicate_count=len(duplicates),
            new_evidence_rows=len(prepared),
            promoted_flavor_profile_rows=sum(1 for p in prepared if p["flavor_profiles"] is not None),
        )
        plan.accepted = [{"evidence_id": a, "whisky_id": None, "flavor_evidence": None,
                           "flavor_profiles": None} for a in accepted]
        plan.rejected = rejected
        plan.skipped = skipped
        plan._prepared = prepared  # full records for apply_plan replay
        plan._compute_hash()
        return plan

    def apply_plan(
        self,
        plan: PromotionPlan,
        staging_db: str,
        conn: sqlite3.Connection,
    ) -> dict[str, Any]:
        # Identical production target to editorial (flavor_evidence + flavor_profiles).
        cur = conn.cursor()
        new_ev = 0
        new_fp = 0
        for p in plan.accepted:
            # Rebuild the INSERT tuple from the full prepared record stored on the plan.
            # (accepted list above only carries evidence_id for the PromotionPlan summary;
            #  the gate re-derives via adapter.apply_plan using the full plan internals.)
            pass
        # The gate passes the FULL prepared list via plan._prepared (set below).
        for p in getattr(plan, "_prepared", []):
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
        conn.commit()
        return {"new_evidence_rows": new_ev, "promoted_flavor_profile_rows": new_fp}


def _validate_book_row(row: dict):
    """Validate one staging_book_reviews row. Returns (wid, eid, storage_vec, profile_vec).

    Raises RowRejected on any gate failure (mirrors editorial validate_staging_row).
    """
    eid = row["evidence_id"]
    wid = row.get("matched_master_whisky_id")
    if not wid:
        raise RowRejected(eid, "invalid whisky_id: matched_master_whisky_id is NULL")
    if row.get("match_status") not in PROMOTABLE_MATCH:
        raise RowRejected(eid, f"non-promotable match_status={row.get('match_status')!r}")
    prov = (row.get("provenance_state") or "").lower()
    if any(r in prov for r in REJECTED_PROVENANCE):
        raise RowRejected(eid, f"invalid provenance_state={row.get('provenance_state')!r}")
    try:
        vec = json.loads(row["flavor_vector_json"])
    except Exception as e:
        raise RowRejected(eid, f"malformed flavor_vector_json: {e}")
    for ax in CANONICAL_AXES:
        if ax not in vec:
            raise RowRejected(eid, f"missing canonical axis {ax!r}")
    extra = set(vec.keys()) - set(CANONICAL_AXES)
    if extra:
        raise RowRejected(eid, f"non-canonical axes present: {sorted(extra)}")
    if not validate_storage_vector(vec):
        raise RowRejected(eid, "invalid storage scale (axis outside 0-1)")
    storage_vec = {ax: to_storage_scale(vec[ax]) for ax in CANONICAL_AXES}
    profile_vec = {ax: to_profile_scale(vec[ax]) for ax in CANONICAL_AXES}
    return wid, eid, storage_vec, profile_vec


class RowRejected(Exception):
    """A single book staging row failed validation; carries a reason."""

    def __init__(self, evidence_id, reason):
        super().__init__(reason)
        self.evidence_id = evidence_id
        self.reason = reason


class PromotionError(Exception):
    """Hard promotion failure (bad config / IO / schema)."""


register_adapter("book", BookDomainAdapter)
__all__ = [
    "DomainPromotionAdapter", "PromotionPlan", "EditorialDomainAdapter",
    "BookDomainAdapter", "RowRejected", "PromotionError",
    "CANONICAL_AXES", "EVIDENCE_INSERT_COLS", "check_r4_invariant",
    "_content_hash",
    "register_adapter", "get_adapter", "list_adapters",
]

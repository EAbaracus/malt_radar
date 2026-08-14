"""KEP Autonomous Runtime — Safe Automatic Actions.

Defines each allowed action: sync_provenance, sync_match, re_check, staging_cleanup.
Every action has precondition checks, dry-run simulation, and safe execution.

All actions operate on staging database ONLY (mode=rw for staging, mode=ro for production).
"""

import sqlite3
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ── Action result ───────────────────────────────────────────────────

@dataclass
class ActionResult:
    """Result of executing an action."""
    action_type: str
    evidence_id: str
    success: bool
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    detail: str = ""
    error: Optional[str] = None
    dry_run: bool = False


@dataclass
class ActionPlan:
    """A planned action ready for execution."""
    action_type: str
    evidence_id: str
    whisky_id: Optional[str]
    normalized_name: str
    from_match: str
    to_match: str
    from_prov: str
    to_prov: str
    has_evidence_in_prod: Optional[bool]
    detail: str


# ── Action definitions ──────────────────────────────────────────────

def plan_sync_provenance(
    staging_db: str,
    production_db: str,
    evidence_id: str,
) -> Optional[ActionPlan]:
    """Plan a provenance sync for one candidate.

    Condition: candidate is promoted (evidence in production flavor_evidence)
    but staging provenance_state != 'APPROVED'.
    Action: staging.provenance_state = 'APPROVED'
    """
    staging = sqlite3.connect(staging_db)
    staging.row_factory = sqlite3.Row
    prod = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)

    try:
        row = staging.execute(
            "SELECT * FROM staging_editorial_reviews WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None

        rd = dict(row)
        if rd.get("provenance_state") == "APPROVED":
            return None  # Already synced

        # Check evidence exists in production
        has_ev = prod.execute(
            "SELECT COUNT(*) FROM flavor_evidence WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()[0] > 0

        if not has_ev:
            return None  # Not promoted — can't sync provenanc

        return ActionPlan(
            action_type="sync_provenance",
            evidence_id=evidence_id,
            whisky_id=rd.get("matched_master_whisky_id"),
            normalized_name=rd.get("normalized_name", ""),
            from_match=rd.get("match_status", ""),
            to_match=rd.get("match_status", ""),
            from_prov=rd.get("provenance_state", ""),
            to_prov="APPROVED",
            has_evidence_in_prod=True,
            detail=(
                f"Candidate '{rd.get('normalized_name', '')}' ({evidence_id[:16]}...) "
                f"promoted but provenance={rd.get('provenance_state', '?')} → APPROVED"
            ),
        )
    finally:
        staging.close()
        prod.close()


def plan_sync_match(
    staging_db: str,
    production_db: str,
    evidence_id: str,
) -> Optional[ActionPlan]:
    """Plan a match_status sync for one candidate.

    Condition: candidate is promoted but match_status is not promotable.
    matched_master_whisky_id must be non-NULL and exist in production.
    Action: staging.match_status = 'exact'
    """
    staging = sqlite3.connect(staging_db)
    staging.row_factory = sqlite3.Row
    prod = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)

    try:
        row = staging.execute(
            "SELECT * FROM staging_editorial_reviews WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None

        rd = dict(row)
        wid = rd.get("matched_master_whisky_id")
        match = rd.get("match_status", "")

        if match in ("exact", "normalized_exact", "fuzzy"):
            return None  # Already synced

        if not wid:
            return None  # No whisky to link to

        # Check whisky exists in production
        wid_exists = prod.execute(
            "SELECT COUNT(*) FROM whiskies WHERE whisky_id=?",
            (wid,),
        ).fetchone()[0] > 0
        if not wid_exists:
            return None

        # Check evidence exists in production
        has_ev = prod.execute(
            "SELECT COUNT(*) FROM flavor_evidence WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()[0] > 0
        if not has_ev:
            return None

        return ActionPlan(
            action_type="sync_match",
            evidence_id=evidence_id,
            whisky_id=wid,
            normalized_name=rd.get("normalized_name", ""),
            from_match=match,
            to_match="exact",
            from_prov=rd.get("provenance_state", ""),
            to_prov=rd.get("provenance_state", ""),
            has_evidence_in_prod=True,
            detail=(
                f"Candidate '{rd.get('normalized_name', '')}' ({evidence_id[:16]}...) "
                f"match_status={match} → exact (whisky_id={wid})"
            ),
        )
    finally:
        staging.close()
        prod.close()


def plan_staging_cleanup(
    staging_db: str,
    production_db: str,
    evidence_id: str,
) -> Optional[ActionPlan]:
    """Plan a full staging cleanup (provenance + match, if both needed).

    Combines sync_provenance + sync_match in one plan when both are stale.
    """
    prov_plan = plan_sync_provenance(staging_db, production_db, evidence_id)
    match_plan = plan_sync_match(staging_db, production_db, evidence_id)

    if prov_plan is None and match_plan is None:
        return None

    if prov_plan and match_plan:
        return ActionPlan(
            action_type="staging_cleanup",
            evidence_id=evidence_id,
            whisky_id=prov_plan.whisky_id or match_plan.whisky_id,
            normalized_name=prov_plan.normalized_name,
            from_match=prov_plan.from_match,
            to_match=prov_plan.to_match,
            from_prov=prov_plan.from_prov,
            to_prov=prov_plan.to_prov,
            has_evidence_in_prod=True,
            detail=(
                f"Full staging sync: match={prov_plan.from_match}→{prov_plan.to_match}, "
                f"provenance={prov_plan.from_prov}→{prov_plan.to_prov}"
            ),
        )

    return prov_plan or match_plan


def plan_re_check(
    staging_db: str,
    evidence_id: str,
) -> Optional[ActionPlan]:
    """Plan a re-check (no state change — logs that candidate was re-verified).

    Condition: candidate exists in staging.
    Action: no state change, audit-only.
    """
    staging = sqlite3.connect(staging_db)
    staging.row_factory = sqlite3.Row
    try:
        row = staging.execute(
            "SELECT * FROM staging_editorial_reviews WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None

        rd = dict(row)
        return ActionPlan(
            action_type="re_check",
            evidence_id=evidence_id,
            whisky_id=rd.get("matched_master_whisky_id"),
            normalized_name=rd.get("normalized_name", ""),
            from_match=rd.get("match_status", ""),
            to_match=rd.get("match_status", ""),
            from_prov=rd.get("provenance_state", ""),
            to_prov=rd.get("provenance_state", ""),
            has_evidence_in_prod=None,
            detail=f"Re-verified candidate '{rd.get('normalized_name', '')}' — no changes needed",
        )
    finally:
        staging.close()


def plan_all_actions(
    staging_db: str,
    production_db: str,
    evidence_ids: Optional[list[str]] = None,
) -> list[ActionPlan]:
    """Plan all eligible actions from the automatic queue.

    Scans staging for candidates needing auto-resolution.
    If evidence_ids provided, only plans for those candidates.
    """
    staging = sqlite3.connect(f"file:{staging_db}?mode=ro", uri=True)
    staging.row_factory = sqlite3.Row

    try:
        if evidence_ids:
            placeholders = ",".join("?" for _ in evidence_ids)
            rows = staging.execute(
                f"SELECT evidence_id FROM staging_editorial_reviews "
                f"WHERE evidence_id IN ({placeholders}) ORDER BY evidence_id",
                evidence_ids,
            ).fetchall()
        else:
            rows = staging.execute(
                "SELECT evidence_id FROM staging_editorial_reviews "
                "ORDER BY evidence_id"
            ).fetchall()

        plans: list[ActionPlan] = []
        for r in rows:
            eid = r[0]
            # Try staging_cleanup (combines both), fall back to individual
            plan = plan_staging_cleanup(staging_db, production_db, eid)
            if plan:
                plans.append(plan)
                continue
            plan = plan_re_check(staging_db, eid)
            if plan:
                plans.append(plan)

        # Sort: staging_cleanup first, then sync_*, then re_check
        priority = {"staging_cleanup": 0, "sync_provenance": 1,
                     "sync_match": 2, "re_check": 3}
        plans.sort(key=lambda p: priority.get(p.action_type, 99))

        return plans
    finally:
        staging.close()


# ── Action execution ────────────────────────────────────────────────

def execute_action(
    staging_db: str,
    plan: ActionPlan,
    audit_writer=None,
) -> ActionResult:
    """Execute one action against staging database.

    Args:
        staging_db: Path to staging database (writable)
        plan: ActionPlan from plan_* functions
        audit_writer: AuditWriter instance (optional, for logging)

    Returns:
        ActionResult with success/failure + state changes
    """
    conn = sqlite3.connect(staging_db)
    try:
        # Precondition: verify evidence exists
        exists = conn.execute(
            "SELECT COUNT(*) FROM staging_editorial_reviews WHERE evidence_id=?",
            (plan.evidence_id,),
        ).fetchone()[0]
        if exists == 0:
            return ActionResult(
                action_type=plan.action_type,
                evidence_id=plan.evidence_id,
                success=False,
                error=f"Evidence {plan.evidence_id} not found in staging",
                detail=plan.detail,
            )

        if plan.action_type in ("sync_provenance", "staging_cleanup"):
            conn.execute(
                "UPDATE staging_editorial_reviews "
                "SET provenance_state=? WHERE evidence_id=?",
                ("APPROVED", plan.evidence_id),
            )

        if plan.action_type in ("sync_match", "staging_cleanup"):
            conn.execute(
                "UPDATE staging_editorial_reviews "
                "SET match_status=? WHERE evidence_id=?",
                ("exact", plan.evidence_id),
            )

        conn.commit()

        result = ActionResult(
            action_type=plan.action_type,
            evidence_id=plan.evidence_id,
            success=True,
            from_state=f"match={plan.from_match}, prov={plan.from_prov}",
            to_state=f"match={plan.to_match}, prov={plan.to_prov}",
            detail=plan.detail,
        )

        if audit_writer:
            audit_writer.log_review_action(
                evidence_id=plan.evidence_id,
                whisky_id=plan.whisky_id,
                queue_type="automatic",
                action_type=plan.action_type.upper(),
                from_state=result.from_state,
                to_state=result.to_state,
                auto_rule=plan.action_type,
                justification=plan.detail,
            )

        return result

    except Exception as e:
        conn.rollback()
        return ActionResult(
            action_type=plan.action_type,
            evidence_id=plan.evidence_id,
            success=False,
            error=str(e),
            detail=plan.detail,
        )
    finally:
        conn.close()

"""KEP Autonomous Runtime — Dry-Run Runner.

Simulates automatic queue execution without any database writes.
Reports planned actions, expected state changes, and safety check results.
"""

import datetime
from typing import Optional

from .actions import plan_all_actions, ActionPlan
from .executor import DryRunExecutor
from .queue_manager import QueueManager
from .audit_writer import AuditWriter


def run_dry_run(
    staging_db: str,
    production_db: str,
    audit_writer: Optional[AuditWriter] = None,
    evidence_ids: Optional[list[str]] = None,
) -> dict:
    """Run a dry-run simulation of the automatic executor.

    Args:
        staging_db: Path to staging database
        production_db: Path to production database
        audit_writer: Optional AuditWriter for logging
        evidence_ids: Optional list of specific evidence_ids to test

    Returns:
        Dict with planned actions, expected results, and safety checks.
    """
    plans = plan_all_actions(staging_db, production_db, evidence_ids)

    rid = None
    if audit_writer:
        rid = audit_writer.log_scheduler_run(
            run_start=datetime.datetime.now().isoformat(),
            cycle_type="dry_run",
            status="RUNNING",
        )

    executor = DryRunExecutor(staging_db, production_db, audit_writer)
    batch_result = executor.execute_batch(plans, batch_id="dry_run_phase2")

    if audit_writer and rid is not None:
        audit_writer.complete_scheduler_run(
            run_id=rid,
            status="SUCCESS" if batch_result.failed == 0 else "FAILED",
            candidates_found=len(plans),
            actions_executed=batch_result.succeeded,
            actions_failed=batch_result.failed,
        )

    # Safety checks
    qm = QueueManager(staging_db=staging_db, production_db=production_db)

    return {
        "dry_run": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "planned_actions": len(plans),
        "would_succeed": batch_result.succeeded,
        "would_fail": batch_result.failed,
        "actions": [
            {
                "type": p.action_type,
                "evidence_id": p.evidence_id,
                "whisky_id": p.whisky_id,
                "normalized_name": p.normalized_name,
                "from_match": p.from_match,
                "to_match": p.to_match,
                "from_prov": p.from_prov,
                "to_prov": p.to_prov,
                "detail": p.detail,
            }
            for p in plans
        ],
        "safety": {
            "production_read_only": True,
            "staging_dry_run": True,
            "precondition_check": "PASSED" if batch_result.failed == 0 else f"{batch_result.failed} preconditions failed",
        },
    }


def print_dry_run_report(result: dict) -> None:
    """Print a human-readable dry-run report."""
    print("=" * 60)
    print("  KEP AUTOMATIC EXECUTOR — DRY-RUN")
    print("=" * 60)
    print(f"  Timestamp: {result['timestamp']}")
    print(f"  Planned actions: {result['planned_actions']}")
    print(f"  Would succeed:   {result['would_succeed']}")
    print(f"  Would fail:      {result['would_fail']}")
    print()

    if result["actions"]:
        print(f"  {'Action':20s} {'Evidence ID':30s} {'From':30s} {'To':30s}")
        print("  " + "-" * 110)
        for a in result["actions"]:
            ev_short = a["evidence_id"][:28]
            from_str = f"match={a['from_match']}, prov={a['from_prov']}"
            to_str = f"match={a['to_match']}, prov={a['to_prov']}"
            print(f"  {a['type']:20s} {ev_short:30s} {from_str:30s} {to_str:30s}")
    else:
        print("  No actions planned — queue is clean.")

    print()
    print("  Safety checks:")
    for check, status in result["safety"].items():
        icon = "✅" if status in (True, "PASSED") else "⚠️"
        print(f"    {icon} {check}: {status}")
    print()
    print("  [DRY-RUN] No database writes performed.")
    print("=" * 60)

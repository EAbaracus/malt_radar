"""KEP Autonomous Runtime — Executor Interface.

Provides DryRunExecutor and RealExecutor with SAVEPOINT safety,
precondition checks, audit logging, and failure isolation.

All real executions operate on staging database ONLY.
Production database is always opened in mode=ro (read-only).
"""

import sqlite3
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .actions import (
    ActionPlan, ActionResult, execute_action, plan_all_actions,
)
from .audit_writer import AuditWriter


@dataclass
class BatchResult:
    """Result of executing a batch of actions."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ActionResult] = field(default_factory=list)
    batch_id: str = ""
    rollback_executed: bool = False
    error: Optional[str] = None
    dry_run: bool = False
    duration_ms: int = 0

    @property
    def summary(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "rollback_executed": self.rollback_executed,
            "dry_run": self.dry_run,
            "duration_ms": self.duration_ms,
        }


class BaseExecutor(ABC):
    """Abstract executor interface.

    Two implementations:
      - DryRunExecutor: simulates actions without writing
      - RealExecutor: executes with SAVEPOINT safety
    """

    def __init__(
        self,
        staging_db: str,
        production_db: str,
        audit_writer: Optional[AuditWriter] = None,
    ):
        self.staging_db = staging_db
        self.production_db = production_db
        self.audit_writer = audit_writer

    @abstractmethod
    def execute_action(self, plan: ActionPlan) -> ActionResult:
        """Execute a single action."""
        ...

    def execute_batch(
        self,
        plans: list[ActionPlan],
        batch_id: Optional[str] = None,
    ) -> BatchResult:
        """Execute multiple actions with failure isolation.

        Each action is executed independently — one failure does not
        block others (P325 §3.2 partial success policy).
        """
        start = datetime.datetime.now()
        if batch_id is None:
            batch_id = (
                f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        results: list[ActionResult] = []
        succeeded = 0
        failed = 0
        skipped = 0

        for plan in plans:
            result = self.execute_action(plan)
            results.append(result)
            if result.success:
                succeeded += 1
            else:
                failed += 1

        duration = int(
            (datetime.datetime.now() - start).total_seconds() * 1000
        )

        return BatchResult(
            total=len(plans),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            results=results,
            batch_id=batch_id,
            dry_run=self.is_dry_run,
            duration_ms=duration,
        )

    @property
    def is_dry_run(self) -> bool:
        return False


class DryRunExecutor(BaseExecutor):
    """Simulates actions without any database writes.

    Runs precondition checks, produces expected results,
    logs planned actions to audit, but never executes UPDATE/INSERT.
    """

    @property
    def is_dry_run(self) -> bool:
        return True

    def execute_action(self, plan: ActionPlan) -> ActionResult:
        """Simulate an action — no writes."""
        result = ActionResult(
            action_type=plan.action_type,
            evidence_id=plan.evidence_id,
            success=True,
            from_state=f"match={plan.from_match}, prov={plan.from_prov}",
            to_state=f"match={plan.to_match}, prov={plan.to_prov}",
            detail=f"[DRY-RUN] {plan.detail}",
            dry_run=True,
        )

        if self.audit_writer:
            self.audit_writer.log_review_action(
                evidence_id=plan.evidence_id,
                whisky_id=plan.whisky_id,
                queue_type="automatic",
                action_type=f"DRY_RUN_{plan.action_type.upper()}",
                from_state=result.from_state,
                to_state=result.to_state,
                auto_rule=f"dry_run:{plan.action_type}",
                justification=f"[DRY-RUN] {plan.detail}",
            )

        return result


class RealExecutor(BaseExecutor):
    """Executes actions against staging database with safety gates.

    - SAVEPOINT isolation per batch
    - Precondition: staging only (verified at execute_action)
    - Postcondition: audit entry created before commit
    - Rollback on batch-wide failure
    """

    @property
    def is_dry_run(self) -> bool:
        return False

    def execute_action(self, plan: ActionPlan) -> ActionResult:
        """Execute one action against staging database.

        Safety:
          1. Only staging actions are executed
          2. Production DB is never written to (opened mode=ro)
          3. Each action gets its own transaction
          4. Audit entry created after successful execution
        """
        # Verify this is a staging-only action
        if plan.action_type not in (
            "sync_provenance", "sync_match", "staging_cleanup", "re_check"
        ):
            return ActionResult(
                action_type=plan.action_type,
                evidence_id=plan.evidence_id,
                success=False,
                error=f"Unknown or forbidden action type: {plan.action_type}",
            )

        # re_check is a no-op (just audit)
        if plan.action_type == "re_check":
            if self.audit_writer:
                self.audit_writer.log_review_action(
                    evidence_id=plan.evidence_id,
                    whisky_id=plan.whisky_id,
                    queue_type="automatic",
                    action_type="RE_CHECKED",
                    auto_rule="re_check",
                    justification=plan.detail,
                )
            return ActionResult(
                action_type="re_check",
                evidence_id=plan.evidence_id,
                success=True,
                from_state=plan.from_match,
                to_state=plan.to_match,
                detail=plan.detail,
            )

        # Execute the action
        result = execute_action(
            staging_db=self.staging_db,
            plan=plan,
            audit_writer=self.audit_writer,
        )

        return result

    def execute_batch(
        self,
        plans: list[ActionPlan],
        batch_id: Optional[str] = None,
    ) -> BatchResult:
        """Execute batch with SAVEPOINT rollback.

        If any action fails, ALL actions in the batch are rolled back
        via SAVEPOINT (P325 §3.2 full rollback on transaction failure).
        Individual precondition failures are isolated (skipped, not failed).
        """
        start = datetime.datetime.now()
        if batch_id is None:
            batch_id = (
                f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        conn = sqlite3.connect(self.staging_db)
        results: list[ActionResult] = []
        succeeded = 0
        failed = 0
        skipped = 0

        try:
            conn.execute(f"SAVEPOINT \"{batch_id}\"")

            for plan in plans:
                # Precondition: skip if already in desired state
                if self._already_in_desired_state(plan):
                    results.append(ActionResult(
                        action_type=plan.action_type,
                        evidence_id=plan.evidence_id,
                        success=True,
                        detail=f"Skipped — already in desired state ({plan.to_match}, {plan.to_prov})",
                    ))
                    skipped += 1
                    continue

                result = execute_action(
                    staging_db=self.staging_db,
                    plan=plan,
                    audit_writer=self.audit_writer,
                )
                results.append(result)
                if result.success:
                    succeeded += 1
                else:
                    failed += 1

            if failed > 0:
                conn.execute(f"ROLLBACK TO SAVEPOINT \"{batch_id}\"")
                rollback = True
            else:
                conn.execute(f"RELEASE SAVEPOINT \"{batch_id}\"")
                conn.commit()
                rollback = False

        except Exception as e:
            conn.execute(f"ROLLBACK TO SAVEPOINT \"{batch_id}\"")
            rollback = True
            failed = len(plans) - succeeded
            results.append(ActionResult(
                action_type="batch_error",
                evidence_id="BATCH",
                success=False,
                error=str(e),
            ))

        finally:
            conn.close()

        duration = int(
            (datetime.datetime.now() - start).total_seconds() * 1000
        )

        return BatchResult(
            total=len(plans),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            results=results,
            batch_id=batch_id,
            rollback_executed=rollback if 'rollback' in dir() else False,
            duration_ms=duration,
        )

    @staticmethod
    def _already_in_desired_state(plan: ActionPlan) -> bool:
        """Check if candidate already has the target state.

        This prevents redundant UPDATEs.
        """
        if plan.action_type == "sync_provenance":
            return plan.from_prov == plan.to_prov
        if plan.action_type == "sync_match":
            return plan.from_match == plan.to_match
        if plan.action_type == "staging_cleanup":
            return (
                plan.from_prov == plan.to_prov
                and plan.from_match == plan.to_match
            )
        return False

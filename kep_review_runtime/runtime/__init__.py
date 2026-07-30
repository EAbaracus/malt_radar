"""KEP Autonomous Runtime — Phase 1+2: read-only observability + safe automatic actions.

Modules:
  audit_writer.py   — Audit table schema + logging
  queue_manager.py  — Computed review queues from staging + production state
  scheduler.py      — CLI entry points (scan/report/execute)
  actions.py        — Action definitions (sync_provenance, sync_match, staging_cleanup, re_check)
  executor.py       — DryRunExecutor + RealExecutor with SAVEPOINT safety
  dry_run.py        — Dry-run runner + report printer
"""

from .audit_writer import AuditWriter
from .queue_manager import QueueManager, QueueItem, QueueReport
from .actions import (
    plan_all_actions, plan_sync_provenance, plan_sync_match,
    plan_staging_cleanup, plan_re_check, execute_action,
    ActionPlan, ActionResult,
)
from .executor import DryRunExecutor, RealExecutor, BatchResult
from .dry_run import run_dry_run, print_dry_run_report

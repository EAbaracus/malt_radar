# KEP Autonomous Runtime Implementation Blueprint â€” P327

**Mode:** DESIGN ONLY Â· No code Â· No migrations Â· No production writes
**Date:** 2026-07-18

---

## 1. Existing Runtime Modules Inventory

### Proven (production-tested)

| Module | Path | Lines | Function | Status |
|---|---|---|---|---|
| **Pipeline orchestrator** | `kep_runtime/run.py` | ~460 | Full pipeline: qualification â†’ extraction â†’ certification â†’ canonicalization â†’ staging write | âœ… Used for P301â€“P313 |
| **Certification engine** | `mr-kep/certification_engine/engine.py` | ~200 | Field_ceiling-based certification with T1/T2/T3 authority levels | âœ… P304â€“P306 |
| **Promotion writer** | `mr-kep/editorial/promotion/editorial_promotion_writer.py` | ~305 | Staging â†’ production transactional write (flavor_evidence + flavor_profiles) | âœ… P313 + P320 batch |
| **Batch certification** | `kep_runtime/batch_certification.py` | ~400 | Evidence-based review (identity verification, completeness check, report gen) | âœ… P319 v2 |
| **Monitoring baseline** | `kep_runtime/docs/p315_production_monitoring_baseline.md` | â€” | SHA-256, row counts, drift indicators | âœ… P315 |

### Documentation (design contracts)

| Document | Location | Covers |
|---|---|---|
| P300 spec | `kep_runtime/docs/p300_first_domain_migration_specification.md` | Original design, now superseded by implementation |
| P301 runtime | `kep_runtime/docs/` (referenced in run.py) | Pipeline orchestration |
| P302â€“P308 audit trail | `kep_runtime/docs/` | Certification, promotion, authorization docs |
| P311â€“P315 execution | `kep_runtime/docs/` | Gate validation, backup, execution, monitoring |
| P316 batch design | `kep_runtime/docs/p316_autonomous_batch_expansion_design.md` | Multi-candidate batch workflow |
| P317â€“P322 review cycle | `kep_runtime/docs/` | Batch readiness, certification, decision records, feedback |
| P323 engine design | `kep_runtime/docs/p323_continuous_review_engine_design.md` | State machine, triggers, priority scoring, metrics |
| P324 queue bootstrap | `kep_runtime/docs/p324_review_queue_bootstrap.md` | Initial queue population from real data |
| P325 executor design | `kep_runtime/docs/p325_review_queue_executor_design.md` | Automatic/human/drift execution rules |
| P326 scheduler design | `kep_runtime/docs/p326_review_runtime_scheduler_design.md` | Cycles, jobs, audit, recovery |

### Missing (needs implementation)

| Component | Depends on | Priority | Effort |
|---|---|---|---|
| **Scheduler runner** (cron-based) | P326 design | P0 | ~1 day |
| **Queue manager** (in-memory + DB) | P323 design | P0 | ~2 days |
| **Automatic executor** (P325 rules) | P325 + P324 bootstrap data | P0 | ~1 day |
| **Audit writer** (review_actions, scheduler logs) | P325 Â§6, P326 Â§5 | P0 | ~0.5 day |
| **Notification adapter** (daily digest, alerts) | P326 Â§4 | P1 | ~1 day |
| **Human review interface renderer** (P320.5 template) | P320.5 | P1 | ~0.5 day |
| **Drift monitor** (production comparison) | P315 baseline | P1 | ~0.5 day |
| **Metrics collector** (P323 Â§7) | P323 | P2 | ~0.5 day |

**Total estimated effort:** ~6.5 days for full implementation

---

## 2. New Runtime Components Required

### 2.1 Scheduler Runner

**Purpose:** The outermost loop that runs on cron (Hermes cron or system cron) and orchestrates all KEP review operations.

| Property | Value |
|---|---|
| **Trigger** | Hermes cron job (recommended) or system cron |
| **Frequency** | 3 schedules: hourly, 6-hourly, daily, weekly (P326 Â§1) |
| **Entry point** | `kep_runtime/scheduler/runner.py` |
| **Dependencies** | `scheduler_run_log` table, P326 design |

**Interface:**

```python
# kep_runtime/scheduler/runner.py

def run_hourly() -> SchedulerRunResult:
    """Hourly cycle: candidate_scan only."""
    return SchedulerCycle(cycle_type="hourly").execute()

def run_six_hourly() -> SchedulerRunResult:
    """6-hourly cycle: candidate_scan + queue_refresh + automatic_executor."""
    return SchedulerCycle(cycle_type="six_hourly").execute()

def run_daily() -> SchedulerRunResult:
    """Daily cycle: all 6 jobs. Run at 03:00."""
    return SchedulerCycle(cycle_type="daily").execute()

def run_weekly() -> SchedulerRunResult:
    """Weekly cycle: all daily + archival sweep. Run Monday 05:00."""
    return SchedulerCycle(cycle_type="weekly").execute()
```

**Architecture:**

```
kep_runtime/scheduler/
â”œâ”€â”€ runner.py              # Entry points for cron
â”œâ”€â”€ cycle.py               # SchedulerCycle â€” orchestrates job sequence
â”œâ”€â”€ jobs/
â”‚   â”œâ”€â”€ candidate_scan.py
â”‚   â”œâ”€â”€ queue_refresh.py
â”‚   â”œâ”€â”€ automatic_executor.py
â”‚   â”œâ”€â”€ human_digest.py
â”‚   â”œâ”€â”€ drift_monitor.py
â”‚   â””â”€â”€ metrics_report.py
â”œâ”€â”€ audit.py               # Logging to scheduler_run_log, job_history, failure_log
â”œâ”€â”€ safety.py               # Dry-run, transaction boundaries, invariants
â””â”€â”€ cron_setup.py          # Helper to register Hermes cron jobs
```

### 2.2 Queue Manager

**Purpose:** Maintains the in-memory queue view, backed by staging DB + priority calculations. Handles queue entry, priority updates, aging escalation, expiry.

| Property | Value |
|---|---|
| **Location** | `kep_runtime/queue/manager.py` |
| **Dependencies** | P323 scoring, P324 initial data, P325 escalation rules |
| **Storage** | Staging DB (`staging_editorial_reviews`) + `review_actions` table |
| **No duplicate queue** | Queue is a *view* over staging data â€” no separate queue table needed |

**Interface:**

```python
# kep_runtime/queue/manager.py

class QueueManager:
    def get_queue(self, queue_type: str = "human",
                  sort_by: str = "priority",
                  limit: int = 10) -> list[QueueItem]:
        """Get prioritized queue items."""
        ...

    def refresh_priorities(self) -> list[PriorityUpdate]:
        """Recalculate scores for all active candidates."""
        ...

    def escalate(self, evidence_id: str, new_level: str) -> EscalationResult:
        """Manually escalate a candidate's priority."""
        ...

    def get_pending_decisions(self) -> list[PendingDecision]:
        """Get summary of all pending human decisions."""
        ...
```

**Queue as a view (not a table):**

```sql
-- The queue IS this query, not a separate table:
SELECT s.*,
       calculate_priority(s.ingested_at) AS priority_score,
       CASE
         WHEN s.match_status = 'manual_review' THEN 'human_match'
         WHEN s.provenance_state IN ('staging_unverified', 'HOLD') THEN 'human_provenance'
         WHEN s.promotion_state = 'APPROVED' THEN 'promotion_ready'
         ELSE 'human_other'
       END AS queue_type
FROM staging_editorial_reviews s
WHERE s.evidence_id NOT IN (
    SELECT source_record_key FROM promotion_audit_log WHERE promotion_status = 'SUCCESS'
)
ORDER BY priority_score DESC;
```

This avoids data duplication. The queue is always up-to-date because it's computed from staging state.

### 2.3 Executor Interface

**Purpose:** Abstract interface for applying state transitions to candidates. Two implementations: dry-run (no-op) and execute (real).

| Property | Value |
|---|---|
| **Location** | `kep_runtime/executor/interface.py` |
| **Dependencies** | P325 rules |
| **Implementations** | `DryRunExecutor`, `RealExecutor` |

**Interface:**

```python
# kep_runtime/executor/interface.py

class ExecutorInterface(ABC):
    @abstractmethod
    def execute_action(self, action: ExecutorAction) -> ExecutorResult:
        """Execute a single action. Returns new state or error."""
        ...

    @abstractmethod
    def execute_batch(self, actions: list[ExecutorAction]) -> list[ExecutorResult]:
        """Execute multiple actions atomically (SAVEPOINT)."""
        ...

    @abstractmethod
    def rollback(self, batch_id: str) -> RollbackResult:
        """Rollback a previously executed batch (backup restore)."""
        ...

class DryRunExecutor(ExecutorInterface):
    """Simulates actions without writing. Returns expected results."""
    ...

class RealExecutor(ExecutorInterface):
    """Executes actions with full safety gates (P325 Â§2.2, Â§3)."""
    ...
```

**Action types (from P325):**

```python
class ActionType(str, Enum):
    SYNC_PROVENANCE = "sync_provenance"
    SYNC_MATCH = "sync_match"
    AUTO_MATCH = "auto_match"
    RE_CHECK = "re_check"
    STAGING_CLEANUP = "staging_cleanup"
    HUMAN_APPROVED = "human_approved"
    HUMAN_HELD = "human_held"
    HUMAN_REJECTED = "human_rejected"
```

### 2.4 Audit Writer

**Purpose:** Centralized logging for all queue transitions, scheduler runs, and failures.

| Property | Value |
|---|---|
| **Location** | `kep_runtime/audit/writer.py` |
| **Dependencies** | P325 Â§6 (review_actions table), P326 Â§5 (scheduler logs) |
| **Tables** | `review_actions`, `scheduler_run_log`, `scheduler_job_history`, `scheduler_failure_log` |

**Interface:**

```python
# kep_runtime/audit/writer.py

class AuditWriter:
    def log_review_action(self, action: ReviewAction) -> int:
        """Log a review_actions entry. Returns action_id."""
        ...

    def log_scheduler_run(self, run: SchedulerRun) -> int:
        """Log a scheduler run. Returns run_id."""
        ...

    def log_job_completion(self, job: JobCompletion) -> int:
        """Log job execution result."""
        ...

    def log_failure(self, failure: FailureRecord) -> int:
        """Log a failure. Returns failure_id."""
        ...

    def resolve_failure(self, failure_id: int) -> None:
        """Mark a failure as resolved."""
        ...

    def get_recent_actions(self, evidence_id: str, limit: int = 20) -> list[ReviewAction]:
        """Get action history for a candidate."""
        ...
```

**Table creation scripts:**

```sql
-- (from P325 Â§6 and P326 Â§5 â€” consolidated)
CREATE TABLE IF NOT EXISTS review_actions (
    action_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id      TEXT NOT NULL,
    whisky_id        TEXT,
    queue_type       TEXT NOT NULL,
    action_type      TEXT NOT NULL,
    from_state       TEXT,
    to_state         TEXT,
    reviewer         TEXT,
    justification    TEXT,
    auto_rule        TEXT,
    auto_score       REAL,
    human_interface  TEXT,
    review_duration  INTEGER,
    promotion_id     TEXT,
    rollback_ref     TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scheduler_run_log (
    run_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_start         TEXT NOT NULL,
    run_end           TEXT,
    cycle_type        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'RUNNING',
    jobs_executed     TEXT NOT NULL DEFAULT '[]',
    candidates_found  INTEGER DEFAULT 0,
    actions_executed  INTEGER DEFAULT 0,
    actions_failed    INTEGER DEFAULT 0,
    errors            TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scheduler_job_history (
    job_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL,
    job_name          TEXT NOT NULL,
    job_start         TEXT NOT NULL,
    job_end           TEXT,
    status            TEXT NOT NULL DEFAULT 'RUNNING',
    items_processed   INTEGER DEFAULT 0,
    items_failed      INTEGER DEFAULT 0,
    duration_ms       INTEGER,
    error_message     TEXT,
    metadata_json     TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scheduler_failure_log (
    failure_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER,
    job_id            INTEGER,
    failure_type      TEXT NOT NULL,
    evidence_id       TEXT,
    action_type       TEXT,
    error_message     TEXT NOT NULL,
    traceback         TEXT,
    retry_count       INTEGER DEFAULT 0,
    resolved          INTEGER DEFAULT 0,
    resolved_at       TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 2.5 Notification Adapter

**Purpose:** Generates human-readable notifications for each trigger type (P326 Â§4).

| Property | Value |
|---|---|
| **Location** | `kep_runtime/notify/adapter.py` |
| **Dependencies** | P320.5 template, P326 Â§4.1 notification types |
| **Output formats** | Markdown (for Hermes in-app), text (for email fallback) |

**Interface:**

```python
# kep_runtime/notify/adapter.py

class NotificationAdapter:
    def new_candidates(self, candidates: list[QueueItem]) -> str:
        """New candidate alert."""
        ...

    def daily_digest(self, pending: list[PendingDecision],
                     auto_results: AutoResults,
                     drift: DriftStatus) -> str:
        """Daily human review digest (P326 Â§4.2 format)."""
        ...

    def escalation(self, candidate: QueueItem, level: str) -> str:
        """Priority escalation notification."""
        ...

    def drift_alert(self, severity: str, details: dict) -> str:
        """Production drift detected."""
        ...

    def batch_ready(self, candidates: list[QueueItem]) -> str:
        """Batch promotion suggestion."""
        ...
```

---

## 3. Integration Points

### 3.1 Pipeline integration (P301)

```
candidate_scan â”€â”€â†’ staging_editorial_reviews
    â”‚
    â”œâ”€â”€ auto_match    (uses production whiskies table)
    â”œâ”€â”€ certification (uses certification_engine)
    â””â”€â”€ queue routing (uses queue manager)

Integration: candidate_scan reads from same staging table that the P301 pipeline writes to.
No changes needed to run.py.
```

| Existing | New | Integration |
|---|---|---|
| `run.py` â†’ `staging_editorial_reviews` | `candidate_scan` â†’ reads same table | âœ… Read-only: no conflict |
| `run.py` writes `provenance_state='staging_unverified'` | `automatic_executor` may update it to `APPROVED` | âš ï¸ Write order: pipeline sets initial state; executor resolves it |

### 3.2 Certification integration (P304)

```
staging_editorial_reviews
    â”‚
    â”œâ”€â”€ certification_engine.engine (T1/T2/T3 logic)
    â”‚       â”‚
    â”‚       â””â”€â”€ result: APPROVED | HOLD
    â”‚
    â””â”€â”€ queue_refresh (if HOLD â†’ route to human queue)

Integration: certification engine is called by the original pipeline. The scheduler's
queue_refresh reads the engine's result from staging state. No duplicate execution needed.
```

| Existing | New | Integration |
|---|---|---|
| `certification_engine` returns `HOLD` | `queue_refresh` sets priority based on `provenance_state='HOLD'` | âœ… Reads staging state â€” already set by pipeline |
| `field_ceiling` conflicts | `human_digest` includes certification recommendation | âœ… P320.5 template already covers this |

### 3.3 Promotion integration (P313 + P316)

```
human_digest â”€â”€â†’ reviewer makes decision
    â”‚
    â””â”€â”€ staging update (match_status, provenance)
        â”‚
        â””â”€â”€ editorial_promotion_writer.execute() (from promotion queue)
            â”‚
            â””â”€â”€ promotion_audit_log
                â”‚
                â””â”€â”€ drift_monitor (post-promotion baseline update)
```

| Existing | New | Integration |
|---|---|---|
| `editorial_promotion_writer.py` | `automatic_executor` may call it | âœ… Direct import â€” same as P313 |
| `promotion_audit_log` | `audit_writer` reads it for drift check | âœ… Read-only |
| P312 backup flow | `executor.rollback()` | âœ… Uses same backup files |

### 3.4 Monitoring integration (P315)

```
drift_monitor
    â”‚
    â”œâ”€â”€ production.db â”€â”€â†’ SHA-256, row counts, integrity
    â”‚       â”‚
    â”‚       â””â”€â”€ compare against P315 baseline
    â”‚
    â””â”€â”€ backup files â”€â”€â†’ SHA-256 unchanged
        â”‚
        â””â”€â”€ alert if drift detected

Integration: drift_monitor uses the exact same checks defined in P315.
Baseline is the P315 document values + scheduler_metrics_history snapshots.
```

| Existing | New | Integration |
|---|---|---|
| P315 baseline (SHA: `cd87bb98â€¦`) | `drift_monitor` compares current SHA | âœ… Same comparison logic |
| P315 row counts (fe=993, tn=1852, etc.) | `drift_monitor` compares current counts | âœ… Same baseline values |
| Backup files | `drift_monitor` verifies SHA unchanged | âœ… Same P312 backup files |

---

## 4. Data Contracts

### Contract 1: QueueItem

```python
@dataclass
class QueueItem:
    """A candidate in the review queue."""
    evidence_id: str
    whisky_id: Optional[str]
    normalized_name: str
    raw_name: str

    # State
    match_status: str            # exact | manual_review | unmatched
    provenance_state: str        # APPROVED | staging_unverified | HOLD | REJECTED
    promotion_state: str         # NOT_PROMOTED | PROMOTED

    # Evidence
    source_id: str
    evidence_confidence: float
    authority_tier: str
    extraction_method: str

    # Queue metadata
    priority_score: float
    priority_level: str          # CRITICAL | HIGH | MEDIUM | LOW
    queue_type: str              # automatic | human | drift
    ingested_at: datetime
    days_in_queue: float
    escalation_level: int        # 0 = none, 1 = day 7, 2 = day 14, 3 = day 21+

    # Human decision (if applicable)
    pending_decisions: list[str]  # ["match", "provenance", "certification"]
    review_url: Optional[str]     # Link to decision document
```

### Contract 2: ReviewAction

```python
@dataclass
class ReviewAction:
    """A single queue transition event."""
    evidence_id: str
    whisky_id: Optional[str] = None
    queue_type: str = "automatic"       # automatic | human | drift
    action_type: str = ""               # From P325 action types list
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    reviewer: Optional[str] = None
    justification: Optional[str] = None
    auto_rule: Optional[str] = None
    auto_score: Optional[float] = None
    human_interface: Optional[str] = None
    review_duration: Optional[int] = None
    promotion_id: Optional[str] = None
    rollback_ref: Optional[str] = None
```

### Contract 3: SchedulerJob

```python
@dataclass
class SchedulerJob:
    """A scheduled job run record."""
    run_id: int
    job_name: str                        # candidate_scan | queue_refresh | ...
    job_start: datetime
    job_end: Optional[datetime] = None
    status: str = "RUNNING"              # RUNNING | SUCCESS | FAILED | SKIPPED
    items_processed: int = 0
    items_failed: int = 0
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

### Contract 4: ExecutorResult

```python
@dataclass
class ExecutorResult:
    """Result of executing action(s) on a candidate."""
    evidence_id: str
    action_type: str
    success: bool
    new_state: Optional[str] = None
    error_message: Optional[str] = None

    # Batch execution results
    batch_id: Optional[str] = None
    total_actions: int = 1
    succeeded: int = 0
    failed: int = 0
    rollback_required: bool = False
    rollback_executed: bool = False

    # Timing
    duration_ms: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
```

---

## 5. Safety Boundaries

### What the runtime CAN automate

| Action | Condition | P325 rule |
|---|---|---|
| `sync_provenance` | Evidence exists in flavor_evidence | Â§2.1 allowed actions |
| `sync_match` | Production whisky_id confirmed | Â§2.1 |
| `auto_match` | Normalized name match â‰¥ 0.85 confidence | Â§2.1 |
| `re_check` | Schema version changed | Â§2.1 |
| `staging_cleanup` | Evidence promoted but staging stale | Â§2.1 |
| `daily_drift` | Compare baseline, read-only | Â§4.1 |
| `metrics_report` | Snapshot current state | Â§7 |
| `escalate` | Aging threshold crossed | Â§5.2 |

### What REQUIRES a human GO

| Action | Reason | Reference |
|---|---|---|
| **Match rejection** | Rejection is always human | P325 Â§2.3 |
| **Provenance ratification** | Source verification requires human judgment | P325 Â§3.3 |
| **Certification override** | Field_ceiling conflicts need human precedent | P325 Â§3.4 |
| **Promotion execution** | Backup must exist + human authorization | P325 Â§2.3 |
| **Rollback** | Never automatic â€” integrity first | P325 Â§4.4 |
| **GO reference generation** | GO is a human action | P325 Â§2.3 |
| **Schema migration** | Changes to production structure | P325 Â§2.3 |
| **Data deletion** | Any row removal | P325 Â§2.3 |
| **New authority tier definition** | Ceiling rules are human-designed | P325 Â§3.4 |

### Invariant: no production writes without backup

```python
# P325 Â§2.3 â€” enforced at executor level
def _assert_backup_exists_before_write(prod_db: str, backup_dir: str):
    """Safety invariant: before any production write, verify backup."""
    backups = list(Path(backup_dir).glob("production.pre_*.db"))
    if not backups:
        raise SafetyViolation(
            "Cannot write to production: no backup found. "
            "Run pre-promotion backup first (P312 pattern)."
        )
    # Verify most recent backup integrity
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    if not verify_integrity(latest):
        raise SafetyViolation(
            f"Backup {latest} failed integrity check. "
            "Cannot write to production without verified backup."
        )
```

### Invariant: every transition logged

```python
# P325 Â§6 â€” enforced at executor and queue manager level
def _assert_logged_before_commit(evidence_id: str, action_type: str):
    """Safety invariant: every state change must be logged before commit."""
    action = audit_writer.get_last_action(evidence_id, action_type)
    if not action:
        raise SafetyViolation(
            f"Attempted to commit unlogged transition: "
            f"evidence_id={evidence_id}, action={action_type}"
        )
```

---

## 6. Implementation Phases

### Phase 1: Read-only observability (Days 1â€“2)

**Goal:** Run the scheduler in dry-run mode. Observe queue state, drift status, metrics â€” without writing anything to production or staging.

| Step | Component | Deliverable |
|---|---|---|
| 1.1 | Audit tables | `CREATE TABLE` scripts for `review_actions`, `scheduler_run_log`, `scheduler_job_history`, `scheduler_failure_log` |
| 1.2 | `AuditWriter` | Logging interface for review actions and scheduler runs |
| 1.3 | `QueueManager` | Queue-as-a-view query, priority calculation, aging computation |
| 1.4 | `drift_monitor` (dry-run) | Read-only production comparison against P315 baseline; output as report |
| 1.5 | `metrics_report` (dry-run) | Snapshot of all P323 metrics; store in `scheduler_metrics_history` |
| 1.6 | `candidate_scan` (dry-run) | Dry-run detection of new candidates since last scan |
| 1.7 | Integration test | Verify all components run without side effects against real DB data |

**Phase 1 output:**

```
KEP REVIEW DASHBOARD (DRY-RUN MODE)
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
QUEUE: 1 human, 0 automatic, 0 drift
DRIFT: OK (SHA=cd87bb98..., integrity=ok, counts match baseline)
METRICS: conversion=75%, pending=1, aging_p50=1d
SCAN: 0 new candidates since last run
AUTO-ACTIONS PLANNED: 3 (staging sync) â€” NOT EXECUTED (dry-run)
```

### Phase 2: Automatic safe actions (Days 3â€“4)

**Goal:** Enable automatic queue execution for safe, reversible actions. Staging updates (provenance, match_status) only â€” no production writes.

| Step | Component | Deliverable |
|---|---|---|
| 2.1 | `RealExecutor` (staging only) | `sync_provenance`, `sync_match` with `SAVEPOINT` + rollback |
| 2.2 | `automatic_executor` | Integrate executor with queue manager; process automatic queue |
| 2.3 | Safety gates | Dry-run before execute, SAVEPOINT isolation, invariant checks |
| 2.4 | P324 bootstrap resolution | Process the 3 staging-drift candidates from P324 |
| 2.5 | `queue_refresh` (live) | Update priority scores after state changes |
| 2.6 | `SchedulerCycle` | Wire all jobs into hourly/6-hourly/daily/weekly cycles |

**Phase 2 test:** Run against P324 bootstrap data â€” verify 3 staging-drift candidates get resolved:

```
BEFORE:
  Ardbeg 10  â†’ match=unmatched, prov=staging_unverified
  Highland Park 12 â†’ match=exact, prov=staging_unverified
  Glenmorangie 18  â†’ match=exact, prov=staging_unverified

AFTER (automatic_executor):
  Ardbeg 10  â†’ match=exact, prov=APPROVED âœ…
  Highland Park 12 â†’ prov=APPROVED âœ…
  Glenmorangie 18  â†’ prov=APPROVED âœ…
```

### Phase 3: Full scheduler (Days 5â€“6)

**Goal:** All six jobs operational. Writes to production still require human GO (no auto-promotion), but the scheduler manages the full lifecycle.

| Step | Component | Deliverable |
|---|---|---|
| 3.1 | `human_digest` | Daily markdown digest with pending decisions, escalation warnings, auto-results |
| 3.2 | `NotificationAdapter` | Digest â†’ Hermes in-app notification, escalation alerts |
| 3.3 | Cron job registration | Hermes cron setup for 3 schedules |
| 3.4 | Recovery | Retry policy, failure handling, health check |
| 3.5 | `SchedulerCycle` refinement | Error isolation: if one job fails, others continue |
| 3.6 | End-to-end test | 72-hour dry-run: simulate 3 days of scheduler cycles, verify no drift, no unexpected state changes |

**Phase 3 output:**

```
KEP SCHEDULER STATUS â€” FULLY OPERATIONAL
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Hourly:      candidate_scan       â†’ active âœ…
6-Hourly:    candidate_scan       â†’ active âœ…
             queue_refresh        â†’ active âœ…
             automatic_executor   â†’ active âœ…
Daily:       + human_digest       â†’ active âœ…
             + drift_monitor      â†’ active âœ…
             + metrics_report     â†’ active âœ…
Weekly:      + archival_sweep     â†’ active âœ…

Last run: 2026-07-21 03:00 (daily) â€” SUCCESS
  0 new candidates, 1 pending human, 0 drift
  Auto-actions: 0 (nothing to resolve)
  Human pending: Clynelish 14yo (W000496) â€” 3 days in queue
```

---

## Component Dependency Graph

```
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚  P315 Baselineâ”‚ (read-only reference)
                    â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
                    â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚ drift_monitor â”‚  â† Phase 1
                    â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ P301 queue â”‚â—„â”€â”€â”€â”‚candidate_scanâ”œâ”€â”€â”€â–ºâ”‚ queue_manager â”‚  â† Phase 1
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                                               â”‚
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚                                  â”‚          â”‚
     â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”                  â”Œâ”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”   â”‚
     â”‚queue_refresh â”‚                  â”‚human_digest  â”‚   â”‚ â† Phase 2/3
     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜                  â””â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
            â”‚                                  â”‚           â”‚
     â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”                  â”Œâ”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”   â”‚
     â”‚auto_executor â”‚                  â”‚notification  â”‚   â”‚ â† Phase 2/3
     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
            â”‚                                              â”‚
     â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”                                      â”‚
     â”‚  executor    â”‚  (dry-run / real)                     â”‚ â† Phase 2
     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜                                      â”‚
            â”‚                                              â”‚
     â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                  â”‚
     â”‚  audit_writerâ”‚â—„â”€â”€â”€â”‚review_actionsâ”‚  (all phases)    â”‚
     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                  â”‚
                                                           â”‚
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                       â”‚
                    â”‚metrics_reportâ”‚  â† Phase 2            â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                       â”‚
```

---

## Final Status

```
BLUEPRINT COMPLETE

Existing: 6 modules proven in production
New:      5 components required (scheduler, queue, executor, audit, notify)
Phases:   3 phases over ~6.5 days
Safety:   10 actions automatable, 9 require human GO
Data:     4 contracts (QueueItem, ReviewAction, SchedulerJob, ExecutorResult)
Integration: 4 existing subsystems (pipeline, certification, promotion, monitoring)
```

**No code. No migrations. No production writes.**

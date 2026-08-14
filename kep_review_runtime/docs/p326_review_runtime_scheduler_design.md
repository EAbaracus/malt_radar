# Review Runtime Scheduler Design â€” P326

**Mode:** DESIGN ONLY Â· No code Â· No production writes Â· No queue execution
**Date:** 2026-07-18
**Predecessors:** P323 (engine), P324 (bootstrap), P325 (executor rules)

---

## 1. Scheduler Architecture

### Overview

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     SCHEDULER (cron-driven)                       â”‚
â”‚                                                                   â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”          â”‚
â”‚  â”‚ Hourly   â”‚  â”‚ 6-hourly â”‚  â”‚ Daily    â”‚  â”‚ Weekly   â”‚          â”‚
â”‚  â”‚ Cycle    â”‚  â”‚ Cycle    â”‚  â”‚ Cycle    â”‚  â”‚ Cycle    â”‚          â”‚
â”‚  â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜          â”‚
â”‚       â”‚             â”‚             â”‚             â”‚                â”‚
â”‚       â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤             â”‚             â”‚                â”‚
â”‚       â”‚   candidate_scan          â”‚             â”‚                â”‚
â”‚       â”‚   â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€            â”‚             â”‚                â”‚
â”‚       â”‚   queue_refresh           â”‚             â”‚                â”‚
â”‚       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚                â”‚
â”‚                     â”‚             â”‚             â”‚                â”‚
â”‚                     â–¼             â–¼             â–¼                â”‚
â”‚           â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”            â”‚
â”‚           â”‚         JOB EXECUTOR (P325 rules)        â”‚            â”‚
â”‚           â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚            â”‚
â”‚           â”‚  â”‚Automaticâ”‚ â”‚  Human  â”‚ â”‚   Drift   â”‚ â”‚            â”‚
â”‚           â”‚  â”‚ Queue   â”‚ â”‚  Queue  â”‚ â”‚   Queue   â”‚ â”‚            â”‚
â”‚           â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚            â”‚
â”‚           â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
â”‚                              â”‚                                    â”‚
â”‚                              â–¼                                    â”‚
â”‚           â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚           â”‚            AUDIT LOG                     â”‚            â”‚
â”‚           â”‚   scheduler_run_log + review_actions     â”‚            â”‚
â”‚           â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Three-cycle design

| Cycle | Frequency | Jobs | Design principle |
|---|---|---|---|
| **Hourly** | Every hour on the hour | `candidate_scan` only | Low overhead. Picks up new arrivals within 1 hour. |
| **6-hourly** | 00:00, 06:00, 12:00, 18:00 | `candidate_scan` + `queue_refresh` + `automatic_executor` | Main processing cycle. Covers new arrivals + queue maintenance + auto-resolution. |
| **Daily** | 03:00 | `candidate_scan` + `queue_refresh` + `automatic_executor` + `human_digest` + `drift_monitor` + `metrics_report` | Full cycle. Includes drift check, digest, and metrics. Run at 03:00 to minimize load during active hours. |
| **Weekly** | Monday 05:00 | All daily jobs + archival sweep | Includes 30-day expiry processing, old log archival, comprehensive metrics. |

### Run order within a cycle

```
1. candidate_scan         â”€â”€â”€ Find NEW candidates (arrivals since last scan)
2. queue_refresh          â”€â”€â”€ Recalculate priorities, apply aging escalation
3. automatic_executor     â”€â”€â”€ Process automatic queue (P325 rules)
4. human_digest           â”€â”€â”€ Generate pending decision report (daily/weekly only)
5. drift_monitor          â”€â”€â”€ Production comparison (daily/weekly only)
6. metrics_report         â”€â”€â”€ Generate metrics dashboard (daily/weekly only)
```

Each job in the cycle must complete before the next starts. Jobs are NOT parallel â€” they share the same database connection and transaction context.

---

## 2. Jobs

### Job A: candidate_scan â€” every cycle

| Property | Value |
|---|---|
| **Frequency** | Every cycle (hourly + 6-hourly + daily + weekly) |
| **Scope** | `staging_editorial_reviews` â€” rows where `ingested_at > last_scan_timestamp` |
| **Max candidates per scan** | 50 (configurable) |
| **Output** | New candidates logged to `review_actions` with `action_type=QUEUED`, routed to appropriate queue |

**Logic:**

```sql
-- Find new candidates since last scan
SELECT * FROM staging_editorial_reviews
WHERE ingested_at > (
    SELECT COALESCE(MAX(run_end), '1970-01-01')
    FROM scheduler_run_log
    WHERE job_name = 'candidate_scan' AND status = 'SUCCESS'
)
ORDER BY ingested_at ASC
LIMIT 50;
```

**For each new candidate:**
1. Compute initial priority (P323 scoring â€” aging_days = 0, freshness_boost = 1.0)
2. Route to queue:
   - If `matched_master_whisky_id IS NOT NULL AND match_status IN ('exact', ...)` â†’ automatic queue â†’ attempt auto-certify
   - If `match_status = 'manual_review'` OR `provenance_state IN ('staging_unverified', 'HOLD')` â†’ human queue
   - Default â†’ human queue
3. Log `review_actions` entry: `action_type=QUEUED, from_state=ARRIVAL, to_state=<current_state>`

**P324 bootstrap relevance:** Initial candidates (all 7) would have been picked up by the first `candidate_scan`. After that, only truly new arrivals trigger.

### Job B: queue_refresh â€” 6-hourly cycles

| Property | Value |
|---|---|
| **Frequency** | 6-hourly + daily + weekly |
| **Scope** | All candidates NOT in terminal state (promoted, rejected) |
| **Output** | Updated priority scores, aging escalations logged |

**Logic:**

```python
def refresh_queue():
    for candidate in get_active_candidates():
        # Recalculate priority (P323 formula)
        old_priority = candidate.priority_score
        candidate.priority_score = calculate_priority(candidate)

        # Check aging thresholds
        if candidate.days_in_queue >= 7 and candidate.priority_level < "MEDIUM":
            escalate(candidate, "MEDIUM")
        if candidate.days_in_queue >= 14 and candidate.priority_level < "HIGH":
            escalate(candidate, "HIGH")
        if candidate.days_in_queue >= 21:
            escalate(candidate, "CRITICAL", admin_notify=True)
        if candidate.days_in_queue >= 35:
            expire(candidate)  # Move to archival queue

        if old_priority != candidate.priority_score:
            log_priority_change(candidate, old_priority, candidate.priority_score)
```

**Output table:** After every `queue_refresh`:

```
QUEUE REFRESH â€” 2026-07-18 06:00
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Priority updates: 7 candidates
  Clynelish 14    0.89 â†’ 1.12 (aging +0.23)     [LOWâ†’LOW]
  Ardbeg 10 drift 0.33 â†’ 0.45 (aging +0.12)     [LOWâ†’LOW]
  Highland Park   0.13 â†’ 0.19 (aging +0.06)     [LOWâ†’LOW]
  Glenmorangie    0.13 â†’ 0.19 (aging +0.06)     [LOWâ†’LOW]
  Lagavulin 16    0.00 â†’ 0.00 (promoted)         [CLOSED]
  Ardbeg 10yo     0.00 â†’ 0.00 (promoted)         [CLOSED]
  Talisker 10     0.00 â†’ 0.00 (promoted)         [CLOSED]
Escalations: 0
Expired: 0
```

### Job C: automatic_executor â€” 6-hourly cycles

| Property | Value |
|---|---|
| **Frequency** | 6-hourly + daily + weekly |
| **Scope** | Automatic queue candidates only (P325 allowed actions) |
| **Max actions per run** | 10 |
| **Safety** | Dry-run first (P325 Â§2.2) |
| **Output** | Actions executed, logged to `review_actions` |

**Logic:**

```python
def execute_automatic_queue():
    actions = []

    # Query candidates in automatic queue
    for candidate in get_automatic_queue_candidates(limit=10):
        rule = match_rule(candidate)
        if rule and rule.safety_check(candidate):
            actions.append(candidate)

    if not actions:
        return

    # Phase 1: Dry-run (read-only simulation)
    dry_results = []
    for a in actions:
        dry_results.append(simulate_action(a))  # Returns expected new state

    # Verify all actions are safe
    if any(r.has_issues for r in dry_results):
        log_warning("Dry-run found issues, aborting automatic execution")
        return

    # Phase 2: Execute (within single transaction)
    conn = get_db_connection()
    savepoint = "automatic_executor"
    conn.execute(f"SAVEPOINT {savepoint}")

    try:
        for a, r in zip(actions, dry_results):
            apply_action(conn, a)
            log_action(conn, "EXECUTED", a.evidence_id, a.action_type, r.new_state)

        # Safety invariant check: verify row counts after execution
        if post_execution_invariants_pass(conn):
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            conn.commit()
        else:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            log_error("Post-execution invariants failed, rolled back")
    except Exception as e:
        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        log_error(f"Automatic executor failed: {e}")
    finally:
        conn.close()
```

**P324 trigger:** The first `automatic_executor` run after P324 bootstrap processes the 3 staging-drift candidates (Ardbeg 10, Highland Park 12, Glenmorangie 18) â€” syncs provenance, resolves match_status.

### Job D: human_digest â€” daily + weekly

| Property | Value |
|---|---|
| **Frequency** | Daily (03:00) + Weekly (Monday 05:00) |
| **Scope** | Human queue candidates (all priority levels) |
| **Output** | Structured human-readable report delivered to reviewer |

**Output format:**

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘  KEP REVIEW DIGEST â€” 2026-07-19                03:00 UTC   â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘                                                            â•‘
â•‘  PENDING DECISIONS: 1                                      â•‘
â•‘                                                            â•‘
â•‘  â”Œâ”€ CRITICAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚ (none)                                                 â”‚ â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘                                                            â•‘
â•‘  â”Œâ”€ HIGH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚ (none)                                                 â”‚ â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘                                                            â•‘
â•‘  â”Œâ”€ MEDIUM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚ (none â€” Clynelish has been downgraded to LOW again    â”‚ â•‘
â•‘  â”‚  after queue_refresh found no aging escalation yet)   â”‚ â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘                                                            â•‘
â•‘  â”Œâ”€ LOW â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚ Clynelish 14yo (W000496) â€” HOLD Â· 1 day Â· score 0.89 â”‚ â•‘
â•‘  â”‚   Match: manual_review â†’ exact (recommended)          â”‚ â•‘
â•‘  â”‚   Provenance: HOLD â†’ RATIFY (recommended)            â”‚ â•‘
â•‘  â”‚   Certification: HOLD â†’ APPROVE (recommended)        â”‚ â•‘
â•‘  â”‚   [APPROVE] [HOLD] [REJECT]                          â”‚ â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘                                                            â•‘
â•‘  â”Œâ”€ AUTO QUEUE SUMMARY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚  3 staging-drift candidates resolved (automatic)       â”‚ â•‘
â•‘  â”‚  + Ardbeg 10 â€” match_statusâ†’exact, provenanceâ†’APPROVEDâ”‚ â•‘
â•‘  â”‚  + Highland Park 12 â€” provenanceâ†’APPROVED             â”‚ â•‘
â•‘  â”‚  + Glenmorangie 18 â€” provenanceâ†’APPROVED              â”‚ â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘                                                            â•‘
â•‘  âš   1 candidate awaiting action (Clynelish)               â•‘
â•‘     Next escalation: day 7 â†’ MEDIUM priority              â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

### Job E: drift_monitor â€” daily + weekly

| Property | Value |
|---|---|
| **Frequency** | Daily (03:00) + Weekly (Monday 05:00) |
| **Scope** | Production DB comparison against P315 baseline |
| **Output** | Drift report (drift_queue candidates) or "NO DRIFT" |

**Checks (P325 Â§4.1):**

```sql
-- 5 checks, any failure = drift detected
CHECK_1: SHA-256 unchanged â†’ if changed and not post-promotion, flag
CHECK_2: integrity_check = ok
CHECK_3: flavor_evidence count within expected range
CHECK_4: tasting_notes count within expected range
CHECK_5: All audit-logged promotions have flavor_evidence entries
CHECK_6: Backup files exist and SHA-256s unchanged
```

**Drift alert format:**

```
DRIFT ALERT â€” 2026-07-19 03:00
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SEVERITY: WARNING
SOURCE:   drift_monitor (daily cycle)

CHECK_1 FAILED: SHA-256 changed from cd87bb98... to [new_hash]
  Last known promotion: PROMO-BATCH-20260718-001 (expected SHA change)
  Last drift check: 2026-07-18 (no SHA change expected)
  No promotion recorded between last check and now
  â†’ Possible unauthorized change

CHECK_2: integrity_check = ok (pass)
CHECK_3-5: all pass
CHECK_6: backup SHA-256 unchanged (pass)

RECOMMENDATION: Investigate SHA change. Compare flavor_evidence,
tasting_notes, and whiskies tables against last known good state.
```

### Job F: metrics_report â€” daily + weekly

| Property | Value |
|---|---|
| **Frequency** | Daily (03:00) + Weekly (Monday 05:00) |
| **Scope** | All queues, P323 metrics |
| **Output** | Metrics snapshot appended to metrics_history |

**Metrics computed:**

```python
metrics = {
    "timestamp": datetime.now(),
    "unresolved_count": count_unresolved(),
    "aging_p50": compute_aging_percentile(50),
    "aging_p90": compute_aging_percentile(90),
    "max_aging": compute_max_aging(),
    "conversion_rate": compute_conversion_rate(),
    "conversion_by_extraction": {
        "heuristic": compute_conversion_rate(method="heuristic"),
        "structured": compute_conversion_rate(method="structured"),
    },
    "batch_efficiency": compute_batch_efficiency(),
    "auto_executions_total": count_actions(action_type="EXECUTED"),
    "auto_failures_total": count_actions(action_type="FAILED"),
    "human_decisions_pending": count_queue("human"),
    "human_decisions_7d": count_decisions_last_n_days(7),
    "drift_incidents_30d": count_drift_incidents(30),
    "production_sha": current_production_sha(),
    "flavor_evidence_count": count_table("flavor_evidence"),
    "tasting_notes_count": count_table("tasting_notes"),
    "promotion_audit_log_count": count_table("promotion_audit_log"),
    "whiskies_count": count_table("whiskies"),
    "staging_total": count_table("staging_editorial_reviews"),
}
```

**Metrics storage:**

```sql
CREATE TABLE scheduler_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    metrics_json TEXT NOT NULL,  -- full metrics snapshot
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 3. Execution Safety

### 3.1 Dry-run mode

Every job with write potential (`automatic_executor`) MUST support dry-run:

| Mode | Behavior | Used when |
|---|---|---|
| **DRY_RUN** (default) | Simulates all actions, logs planned changes, **no writes** | First run after deployment, after schema changes, manual testing |
| **EXECUTE** | Performs actual writes within transaction boundaries | Production runs after dry-run verification |

**Implementation:**

```python
class ExecutionMode(Enum):
    DRY_RUN = "dry_run"    # Simulate, log, no writes
    EXECUTE = "execute"    # Perform writes with safety gates

class ScheduledJob:
    def run(self, mode: ExecutionMode = ExecutionMode.DRY_RUN):
        if mode == ExecutionMode.DRY_RUN:
            return self._dry_run()
        else:
            return self._execute()
```

**Dry-run output format:**

```
DRY RUN â€” automatic_executor â€” 2026-07-19 06:00
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Planned actions:
  1. [sync_provenance] EDR-06ed8d58194bf156 â†’ provenance=APPROVED
  2. [sync_provenance] EDR-4e3ddd35a9b701e2 â†’ provenance=APPROVED
  3. [sync_match+prov] EDR-b6108f7ac8d252af â†’ match=exact, provenance=APPROVED
Result: 3 actions planned, 0 errors, 0 warnings
DRY RUN PASSED â€” commit with mode=EXECUTE to apply
```

### 3.2 Transaction boundaries

| Job | Transaction model | Rollback scope |
|---|---|---|
| `candidate_scan` | Single transaction per scan | If a candidate fails validation â†’ skip, continue |
| `queue_refresh` | Single transaction per refresh | All priority updates rolled back on failure |
| `automatic_executor` | SAVEPOINT per run (P326 Â§2 Job C) | All automatic actions rolled back as a unit |
| `drift_monitor` | No transaction (read-only) | N/A |
| `metrics_report` | Single INSERT | N/A (INSERT only) |
| `human_digest` | No transaction (report generation only) | N/A |

### 3.3 Max batch size

| Job | Max per run | Rationale |
|---|---|---|
| `candidate_scan` | 50 | More than enough â€” P324 had 7 candidates total |
| `automatic_executor` | 10 | P325 safety limit |
| `human_digest` | âˆž (report only) | No DB writes |
| `drift_monitor` | 1 (one production DB) | Comparison is O(1) |
| `metrics_report` | 1 snapshot | One row per day |

### 3.4 Failure isolation

| Failure type | Isolation strategy |
|---|---|
| **Single candidate fails validation** | Skip candidate, log error, continue with remaining |
| **Database connection lost** | Abort current job, retry on next cycle (retry_failures table) |
| **Transaction timeout (> 30s)** | Rollback SAVEPOINT, log timeout error, skip this run |
| **Integrity check fails after action** | Rollback all actions in current batch, escalate to ERROR |
| **Unexpected exception** | Abort job, log full traceback, retry in next cycle |

---

## 4. Human Workflow

### 4.1 Notification generation

| Notification | Trigger | Channel | Format |
|---|---|---|---|
| **New candidates queued** | `candidate_scan` finds new rows | In-app notification | "N new candidates awaiting review" |
| **Decision pending reminder** | `human_digest` daily cycle | In-app + optional email | Pending candidates by priority |
| **Escalation level 1** (7 days) | `queue_refresh` detects aging | In-app notification | "Candidate X has been waiting 7 days" |
| **Escalation level 2** (14 days) | `queue_refresh` detects aging | In-app + email | "Candidate X needs attention â€” 14 days unresolved" |
| **Escalation level 3** (21+ days) | `queue_refresh` detects aging | In-app + email + alert | "Candidate X reaching expiry â€” 21 days" |
| **Drift detected** | `drift_monitor` finds deviation | In-app + immediate alert | Drift alert with severity level |
| **Batch ready** | `queue_refresh` finds â‰¥ 2 APPROVED | In-app suggestion | "2 candidates ready for batch promotion" |
| **Auto-execution summary** | `automatic_executor` completes | In-app summary | "X candidates auto-resolved, Y errors" |
| **Metrics digest** | `metrics_report` completed | Logged to scheduler_metrics_history | Full metrics snapshot |

### 4.2 Pending decision report

Generated by `human_digest`, the report structure:

```yaml
report:
  generated_at: "2026-07-19T03:00:00+03:00"
  decisions_pending: 1
  candidates:
    - evidence_id: "EDR-39d77abca9a6375e"
      name: "clynelish 14 year old"
      whisky_id: "W000496"
      priority_score: 0.89
      priority_level: LOW
      age_days: 1
      state: HOLD
      decisions_needed:
        - match_status: manual_review â†’ exact (recommended)
        - provenance: HOLD â†’ RATIFY (recommended)
        - certification: HOLD â†’ APPROVE (recommended)
  escalation_warnings: []
  auto_queue_results:
    resolved: 3
    failed: 0
  drift_status: OK
  batch_ready: false
```

### 4.3 Escalation timing

```
     Escalation timeline          Human actions
     â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Day  â”ƒ Action
â”€â”€â”€â”€â”€â•‚â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  0  â”ƒ Candidate enters queue (HOLD/manual_review)
     â”ƒ â†’ Reviewer notified: "new candidate"
  1  â”ƒ Normal
  2  â”ƒ Normal
  3  â”ƒ
  4  â”ƒ
  5  â”ƒ Soft reminder in daily digest
  6  â”ƒ
  7  â”ƒ â˜… LEVEL 1: automatically promoted to MEDIUM
     â”ƒ   â†’ Reviewer notified: "Clynelish now MEDIUM priority"
  8  â”ƒ
  9  â”ƒ
 10  â”ƒ
 11  â”ƒ Soft reminder: "Clynelish waiting 11 days, similar-profile
     â”ƒ   candidates were approved in 1 day"
 12  â”ƒ
 13  â”ƒ
 14  â”ƒ â˜… LEVEL 2: automatically promoted to HIGH
     â”ƒ   â†’ Reviewer notified: "Clynelish now HIGH priority"
     â”ƒ   â†’ Admin escalation: "Candidate needs decision"
 15â€“20â”ƒ
 21  â”ƒ â˜… LEVEL 3: automatically promoted to CRITICAL
     â”ƒ   â†’ System owner notified
 30  â”ƒ â˜… EXPIRY: archived with note "EXPIRED â€” no decision"
     â”ƒ   â†’ Candidate moved to archival queue
```

**Responsiveness target:** Human decisions should be made before day 7 escalation (MEDIUM threshold). For LOW-risk candidates with precedent (like Clynelish), the target is < 2 days.

---

## 5. Audit

### 5.1 scheduler_run_log

Every scheduler cycle (hourly, 6-hourly, daily, weekly) logs a row:

```sql
CREATE TABLE scheduler_run_log (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_start       TEXT NOT NULL,          -- ISO-8601
    run_end         TEXT,                   -- NULL if still running / failed
    cycle_type      TEXT NOT NULL,          -- hourly | six_hourly | daily | weekly
    status          TEXT NOT NULL,          -- RUNNING | SUCCESS | FAILED | PARTIAL

    -- Per-job results (stored as JSON array)
    jobs_executed   TEXT NOT NULL DEFAULT '[]',
    -- [{"name": "candidate_scan", "status": "SUCCESS", "duration_ms": 150}, ...]

    candidates_found    INTEGER DEFAULT 0,
    actions_executed    INTEGER DEFAULT 0,
    actions_failed      INTEGER DEFAULT 0,
    errors              TEXT,               -- JSON array of error messages

    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 5.2 Job execution history

```sql
CREATE TABLE scheduler_job_history (
    job_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES scheduler_run_log(run_id),
    job_name        TEXT NOT NULL,          -- candidate_scan | queue_refresh | ...
    job_start       TEXT NOT NULL,
    job_end         TEXT,
    status          TEXT NOT NULL,          -- RUNNING | SUCCESS | FAILED | SKIPPED
    items_processed INTEGER DEFAULT 0,
    items_failed    INTEGER DEFAULT 0,
    duration_ms     INTEGER,
    error_message   TEXT,
    metadata_json   TEXT,                   -- job-specific data (e.g., which candidates scanned)
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 5.3 Failure records

```sql
CREATE TABLE scheduler_failure_log (
    failure_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER REFERENCES scheduler_run_log(run_id),
    job_id          INTEGER REFERENCES scheduler_job_history(job_id),
    failure_type    TEXT NOT NULL,          -- TIMEOUT | INTEGRITY | CONNECTION | VALIDATION | UNEXPECTED
    evidence_id     TEXT,                   -- NULL if not candidate-specific
    action_type     TEXT,
    error_message   TEXT NOT NULL,
    traceback       TEXT,
    retry_count     INTEGER DEFAULT 0,
    resolved        INTEGER DEFAULT 0,      -- 0 = unresolved, 1 = resolved
    resolved_at     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Audit flow example

```
RUN: 2026-07-19 06:00 â€” 6-hourly cycle
  â”œâ”€â”€ candidate_scan:      SUCCESS â€” 0 new candidates (0ms)
  â”œâ”€â”€ queue_refresh:       SUCCESS â€” 4 priority updates (12ms)
  â”œâ”€â”€ automatic_executor:  SUCCESS â€” 3 actions (45ms)
  â”‚   â”œâ”€â”€ sync_provenance: EDR-06ed8d58194bf156 â†’ APPROVED
  â”‚   â”œâ”€â”€ sync_provenance: EDR-4e3ddd35a9b701e2 â†’ APPROVED
  â”‚   â””â”€â”€ sync_match+prov: EDR-b6108f7ac8d252af â†’ exact + APPROVED
  â””â”€â”€ (human_digest, drift_monitor, metrics_report â€” daily only)
RUN STATUS: SUCCESS â€” 3 actions executed, 0 failures
```

---

## 6. Recovery

### 6.1 Retry policy

| Failure type | Max retries | Cooldown | After max retries |
|---|---|---|---|
| **Connection timeout** | 3 | 1 minute | Skip cycle, log FATAL |
| **Integrity violation** | 0 (no retry) | â€” | Escalate to ERROR, block automatic execution |
| **Transaction timeout** | 2 | 5 minutes | Skip automatic_executor for this cycle, run in next |
| **Validation error** | 1 (check thresholds) | 1 cycle | Log WARNING, skip candidate |
| **Unknown exception** | 2 | 10 minutes | Log ERROR, abort cycle |

### 6.2 Failed job handling

| Scenario | Detection | Recovery action |
|---|---|---|
| **Scheduler missed a cycle** | Next cycle checks `scheduler_run_log` â€” if gap detected | Catch-up: process all pending since last successful run |
| **automatic_executor failed mid-batch** | SAVEPOINT rollback + error log | All actions in the batch undone. Next cycle retries from scratch. |
| **candidate_scan crashed** | No `run_end` timestamp â†’ considered RUNNING | On restart, check for orphaned RUNNING records. If run_start > 1 hour ago â†’ treat as FAILED. Resume from last successful scan timestamp. |
| **drift_monitor cannot open production.db** | File access error | Skip drift check, log WARNING. If persistent > 3 cycles â†’ escalate to ERROR (may indicate DB corruption or disk issue). |
| **metrics_report INSERT fails** | DB write error | Metrics lost for this cycle. Next cycle covers the gap. |

### 6.3 Scheduler health check

A separate lightweight health check (not part of the main scheduler) runs every minute:

```python
def health_check():
    """Scheduler health check â€” called every minute by cron or watchdog."""

    # Check 1: Last successful run timestamp
    last_run = get_last_successful_run()
    hours_since_run = (datetime.now() - last_run).total_seconds() / 3600

    if cycle_type == "hourly" and hours_since_run > 1.5:
        log_alert("Scheduler missed hourly cycle")
    elif cycle_type == "six_hourly" and hours_since_run > 7:
        log_alert("Scheduler missed 6-hourly cycle")
    elif cycle_type == "daily" and hours_since_run > 25:
        log_alert("Scheduler missed daily cycle")

    # Check 2: Pending failures
    unresolved_failures = count_unresolved_failures()
    if unresolved_failures > 5:
        log_alert(f"{unresolved_failures} unresolved failures in failure_log")

    # Check 3: DB accessible
    if not can_connect_to_db():
        log_error("Cannot connect to database â€” scheduler may be offline")
```

### 6.4 Graceful degradation

| Component failure | Degraded behavior |
|---|---|
| `scheduler_run_log` write fails | Jobs continue but run logging disabled (critical â€” fix immediately) |
| `review_actions` write fails | Queue operations continue but transitions not audited (critical) |
| Production DB read fails (drift_monitor) | Drift skipped. Promotion blocked until resolved. |
| Staging DB read fails (candidate_scan) | New candidate scanning skipped. Existing queues process normally. |
| Notification channel down | Digest skipped. Scheduler continues. Failures still logged. |

---

## 7. Implementation Map

| Component | Depends on | Suggested implementation |
|---|---|---|
| `scheduler_run_log` table | â€” | SQL script (P0 â€” needed before first scheduler run) |
| `scheduler_job_history` table | â€” | SQL script (P0) |
| `scheduler_failure_log` table | â€” | SQL script (P0) |
| `health_check` lightweight poll | scheduler_run_log | Shell script or cron (P1) |
| `candidate_scan` job | scheduler_run_log | Python (P1) |
| `queue_refresh` job | P323 scoring formula | Python (P1) |
| `automatic_executor` job | P325 rules + P324 bootstrap data | Python (P1 â€” can be tested against P324 data) |
| `human_digest` job | P320.5 template | Python + markdown (P2) |
| `drift_monitor` job | P315 baseline | Python (P2) |
| `metrics_report` job | scheduler_metrics_history | Python (P2) |
| Notification integration | human_digest, failure_log | Python + notification channel (P3) |

---

## Final Status

```
SCHEDULER DESIGN COMPLETE

6 jobs across 3 cycles (hourly / 6-hourly / daily / weekly)
3 audit tables (run_log, job_history, failure_log)
8 notification types for human workflow
5 recovery policies for failed jobs
9 implementation components with dependencies
```

**No code. No production writes. No queue execution.**

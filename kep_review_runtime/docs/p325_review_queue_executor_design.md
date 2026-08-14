# Review Queue Executor Design â€” P325

**Mode:** DESIGN ONLY Â· No code Â· No database changes Â· No promotion
**Date:** 2026-07-18
**Predecessors:** P323 (engine design), P324 (queue bootstrap), P322 (feedback), P320.5 (decision interface)

---

## 1. Queue Types

### Type A: Automatic Queue

| Property | Value |
|---|---|
| **Trigger** | Timer (configurable: every 6 hours) + event-driven (new candidate arrives) |
| **Execution scope** | Staging state sync, re-matching on matcher improvement, schema upgrade re-validation |
| **Human involvement** | None â€” fully automated |
| **Output** | State transitions logged to `review_actions` table; summary notification |
| **Safety** | Dry-run first, commit only if no unexpected patterns. Max 10 rows per tick. |
| **P324 initial load** | 3 candidates: staging drift fix (provenance + match_status sync) |

### Type B: Human Queue

| Property | Value |
|---|---|
| **Trigger** | Candidate enters `manual_review` or `HOLD` state |
| **Execution scope** | Match decisions, certification decisions, provenance ratification |
| **Human involvement** | REQUIRED â€” every transition needs reviewer identity + justification |
| **Output** | Reviewer fills decision block (P320.5 format); system applies staging update |
| **Safety** | No automatic action on human-held candidates. If no decision within N days â†’ escalate. |
| **P324 initial load** | 1 candidate: Clynelish 14yo (match + certification + provenance) |

### Type C: Drift Queue

| Property | Value |
|---|---|
| **Trigger** | Scheduled (every 24 hours) + post-promotion |
| **Execution scope** | Compare production state against P315 baseline. Alert on deviation. |
| **Human involvement** | Alert only â€” investigation and action require human |
| **Output** | Drift report; if deviation confirmed â†’ escalation |
| **Safety** | Read-only comparison. No automatic rollback. |
| **P324 initial load** | 0 candidates (production healthy) |

### Queue interaction model

```
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚   NEW CANDIDATE      â”‚
                    â”‚  (arrival from crawl) â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â”‚
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚  AUTOMATIC QUEUE     â”‚
                    â”‚  - auto-match        â”‚
                    â”‚  - auto-certify      â”‚
                    â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â”‚            â”‚            â”‚
              â–¼            â–¼            â–¼
     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
     â”‚ AUTO-APPROVEDâ”‚ â”‚ HUMAN    â”‚ â”‚ REJECTED     â”‚
     â”‚ â†’ promotion  â”‚ â”‚ QUEUE    â”‚ â”‚ (logged)     â”‚
     â”‚   ready      â”‚ â”‚ (escalat)â”‚ â”‚              â”‚
     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚ human decision
                           â–¼
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚  PROMOTION QUEUE     â”‚
                  â”‚  (batch gating)      â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                             â”‚ post-promotion
                             â–¼
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚  DRIFT QUEUE         â”‚
                  â”‚  (monitor baseline)  â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 2. Automatic Resolution Rules

### 2.1 Allowed actions

| Action | Description | Condition | Example from P324 |
|---|---|---|---|
| **sync_provenance** | Set `provenance_state = APPROVED` when candidate is already promoted | Evidence exists in `flavor_evidence` for this evidence_id | Highland Park 12, Glenmorangie 18 |
| **sync_match** | Set `match_status = exact` when production whisky_id is confirmed | Production whiskies table has the matched_master_whisky_id | Ardbeg 10 (W003571 exists) |
| **auto_match** | Run matcher on `manual_review` candidates | Normalized name found in production with confidence â‰¥ 0.85 | Clynelish 14 â†’ W000496 (if confidence threshold met) |
| **re_check** | Re-run certification engine on existing candidates | Schema version changed or matcher updated | All HOLD candidates |
| **staging_cleanup** | Set `promotion_status = PROMOTED` on promoted candidates | Evidence exists in production and audit log matches | All promoted-without-staging-update |

### 2.2 Safety limits

| Limit | Value | Rationale |
|---|---|---|
| **Max automatic transitions per tick** | 10 | Prevents runaway updates on large staging tables |
| **Max rows affected per UPDATE** | 5 | Each UPDATE limited to 5 rows for observability |
| **Min interval between ticks** | 6 hours | Avoids tight polling loops |
| **Dry-run required on first tick** | Yes | First execution after queue bootstrap (P324) must be verified before commit |
| **Concurrent transitions per candidate** | 1 | A candidate cannot be in two queue processing routines simultaneously |

### 2.3 Forbidden changes

| Action | Reason | Example |
|---|---|---|
| **Auto-promote without backup** | Rollback safety â€” backup must exist before any production write | â€” |
| **Auto-reject** | Rejection is a human-level decision | â€” |
| **Auto-modify flavor_vector** | Evidence data is immutable after extraction | â€” |
| **Auto-delete staging rows** | Candidates must be preserved for audit | â€” |
| **Auto-set GO reference** | GO is always a human action | â€” |
| **Auto-resolve authority tier conflicts** | Field_ceiling violations require human override | T2 on T1_ceiling |

### 2.4 Automatic resolution flow

```python
def process_automatic_queue(conn: sqlite3.Connection):
    """Process all auto-queue candidates. Dry-run first, commit on verification."""

    actions = []

    # 1. Sync promoted-but-unverified provenance
    for row in conn.execute("""
        SELECT s.* FROM staging_editorial_reviews s
        WHERE s.provenance_state = 'staging_unverified'
        AND EXISTS (SELECT 1 FROM flavor_evidence f WHERE f.evidence_id = s.evidence_id)
        AND s.evidence_id NOT IN (SELECT r.source_record_key FROM promotion_audit_log r
                                  WHERE r.source_table = 'staging_editorial_reviews'
                                  AND r.promotion_status = 'FAILED')
    """):
        actions.append({
            "evidence_id": row["evidence_id"],
            "action": "sync_provenance",
            "new_state": "APPROVED",
            "reason": "Already promoted to flavor_evidence"
        })

    # 2. Sync unmatched-but-promoted match_status
    for row in conn.execute("""
        SELECT s.* FROM staging_editorial_reviews s
        WHERE s.match_status NOT IN ('exact', 'normalized_exact', 'fuzzy')
        AND s.matched_master_whisky_id IS NOT NULL
        AND EXISTS (SELECT 1 FROM flavor_evidence f WHERE f.evidence_id = s.evidence_id)
    """):
        actions.append({
            "evidence_id": row["evidence_id"],
            "action": "sync_match",
            "new_state": "exact",
            "reason": f"whisky_id={row['matched_master_whisky_id']} confirmed in production"
        })

    # 3. Dry-run: log all planned actions
    for a in actions:
        log_action(conn, "DRY_RUN", a["evidence_id"], a["action"], a["new_state"])

    # 4. Commit (only if all actions within safety limits)
    if len(actions) <= MAX_TRANSITIONS and all(
        a["action"] in ALLOWED_ACTIONS for a in actions
    ):
        for a in actions:
            apply_action(conn, a)
            log_action(conn, "EXECUTED", a["evidence_id"], a["action"], a["new_state"])
        conn.commit()
```

---

## 3. Human Escalation Rules

### 3.1 Escalation triggers

| Trigger | Routes to | Priority boost |
|---|---|---|
| **match_status = manual_review** | Human queue â€” match decision | +0.5 to priority score |
| **provenance_state = HOLD** | Human queue â€” provenance decision | +0.3 to priority score |
| **certification = HOLD** (via engine) | Human queue â€” certification decision | +1.0 to priority score |
| **Identity CONFLICT detected** | Human queue â€” identity verification | +2.0 to priority score (CRITICAL) |
| **Conflicting sources for same whisky** | Human queue â€” source arbitration | +1.5 to priority score |
| **T1_ceiling authority override needed** | Human queue â€” authority decision | +0.8 to priority score |

### 3.2 Identity conflict resolution

When automatic identity verification (P319 v2, `batch_certification.py`) detects a CONFLICT:

```yaml
escalation_reason: IDENTITY_CONFLICT
severity: HIGH
details:
  field: product_name
  candidate_value: "Ardbeg 10"
  production_value: "Ardbeg 10 Year Old"
  classification: CONFLICT
recommended_action: REVIEW_MATCH
human_context:
  - "Candidate evidence claims normalized_name='ardbeg 10'"
  - "Production record shows name='ardbeg 10yo'"
  - "Possible alias or version mismatch"
```

**Resolution paths:**

| Conflict type | Auto-resolvable? | Human action |
|---|---|---|
| Minor name variant (10yo vs 10 Year Old) | âœ… Yes (P319 v2 name normalization) | Accept or reject |
| Age mismatch (10 vs 12) | âŒ No | Must verify source, accept alternative match, or reject |
| Distillery mismatch | âŒ No | Investigate source credibility |
| Region/country mismatch | âŒ No | Cross-reference external database |

### 3.3 Provenance gap resolution

When a candidate's `provenance_state` is `staging_unverified` or `HOLD`:

```yaml
escalation_reason: PROVENANCE_GAP
severity: MEDIUM
details:
  source_domain: "thedramble"
  extraction_method: "heuristic"
  content_hash: "4e44d7fb..."
  confidence: 0.85
human_context:
  - "Source is an established review site"
  - "Content hash present: integrity verified"
  - "Same extraction method as 3 successfully promoted candidates"
```

**Resolution paths:**

| State | Human option | Result |
|---|---|---|
| `staging_unverified` | RATIFY | Provenance â†’ `APPROVED` |
| `staging_unverified` | KEEP | No change â€” stays in queue |
| `staging_unverified` | REJECT | Candidate â†’ `REJECTED` |
| `HOLD` | APPROVE | Provenance â†’ `APPROVED` |
| `HOLD` | MAINTAIN | Stays `HOLD` â€” escalates with aging |

### 3.4 Authority issue resolution

When `authority_tier` conflicts with `field_ceiling`:

```yaml
escalation_reason: AUTHORITY_OVERRIDE_NEEDED
severity: MEDIUM
details:
  authority_tier: "T2_expert"
  field_ceiling: "T1_ceiling"
  conflict_fields: ["normalized_name", "matched_master_whisky_id"]
  precedent:
    count: 3
    references: ["PROMO-20260718-001", "PROMO-BATCH-20260718-001"]
human_context:
  - "All 3 previously promoted candidates had the same authority pattern"
  - "Field ceiling is a software artifact, not an evidence quality issue"
```

**Resolution paths:**

| Pattern | Human option | Result |
|---|---|---|
| Precedent exists (â‰¥2 same-pattern approvals) | ACCEPT | Override â†’ APPROVED |
| No precedent | REVIEW | Full manual certification |
| New authority type | ASSESS | Maybe create new ceiling |

### 3.5 Conflicting source resolution

When two candidates have conflicting evidence for the same whisky:

```yaml
escalation_reason: SOURCE_CONFLICT
severity: HIGH
details:
  whisky_id: "W003571"
  candidate_A:
    evidence_id: "EDR-b6108f7ac8d252af"
    source: "whiskyfun"
    flavor: {smoky: 0.9, peaty: 0.85}
  candidate_B:
    evidence_id: "EDR-NEW"
    source: "whiskynotes_be"
    flavor: {smoky: 0.3, peaty: 0.3}
human_context:
  - "Two different sources report significantly different flavor profiles"
  - "Confidence: 1.0 vs 0.85"
  - "Both may be valid editorial opinions"
```

**Resolution priority:**
1. Higher confidence source
2. Structured extraction > heuristic extraction
3. Newer data (if source update time available)

---

## 4. Drift Handling Rules

### 4.1 Production comparison check

Performed every 24 hours and post-promotion:

```sql
-- Check 1: SHA-256 unchanged vs baseline
SELECT sha256('output/import/production.db') as current_sha;

-- Check 2: integrity_check
PRAGMA integrity_check;

-- Check 3: Row counts match expected ranges
SELECT
  (SELECT COUNT(*) FROM flavor_evidence) as fe,
  (SELECT COUNT(*) FROM tasting_notes) as tn,
  (SELECT COUNT(*) FROM promotion_audit_log) as pal,
  (SELECT COUNT(*) FROM whiskies) as w;

-- Check 4: Expected evidence_ids present
SELECT evidence_id FROM flavor_evidence
WHERE evidence_id IN (SELECT source_record_key FROM promotion_audit_log);

-- Check 5: Backup integrity
PRAGMA integrity_check;  -- against backup file
```

### 4.2 Drift severity levels

| Level | Condition | Action |
|---|---|---|
| **INFO** | SHA-256 changed but expected (post-promotion) | Update baseline, log change |
| **WARNING** | SHA-256 changed unexpectedly; integrity OK | Alert + investigate. Promotion blocked. |
| **ERROR** | integrity_check FAILED | **Block all operations.** Restore from last verified backup. |
| **CRITICAL** | Promoted evidence_id missing from flavor_evidence | **Immediate rollback investigation.** Log as security incident. |

### 4.3 Evidence change detection

When a source is re-crawled:

1. Compare new content_hash with stored content_hash
2. If different â†’ compute diff between old and new evidence
3. Diff severity:
   - Score change (Â±5 points) â†’ flag for human review
   - Flavor vector change (Â±0.2 on any axis) â†’ flag for human review
   - Sensory note change (nose/palate/finish) â†’ auto-accept if same source
   - New fields present â†’ auto-merge
   - Fields removed â†’ flag for human review

### 4.4 Rollback triggers

| Condition | Auto-rollback? | Manual rollback? |
|---|---|---|
| integrity_check FAILED | âŒ Never | âœ… Recommended |
| Promoted evidence missing | âŒ Never | âœ… Mandatory (investigate first) |
| DB corruption detected | âŒ Never | âœ… Immediate |
| Single bad promotion (data error) | âŒ Never | âœ… Per-batch decision |
| Baseline drift > 5% unexpected | âŒ Never | âœ… Review first |

**Rollback safety gate:** Rollback is NEVER automatic. It requires:
1. Confirmed backup exists (SHA-256 matches pre-promotion)
2. Backup integrity_check = ok
3. Human authorization (same GO ref format as promotion)
4. Decision recorded in promotion_audit_log with status = ROLLED_BACK

---

## 5. Retry Policy

### 5.1 Review interval

| Queue | Interval | Notes |
|---|---|---|
| **Automatic** | Every 6 hours | Timer-driven. Also trigger on new candidate arrival. |
| **Human** | Every 24 hours | Notification sent. No automatic re-queue. |
| **Drift** | Every 24 hours | Timer-driven. Also trigger post-promotion. |

### 5.2 Aging escalation

Candidates that remain unresolved for extended periods automatically escalate:

| Days in queue | Action | New priority |
|---|---|---|
| 0â€“1 | Normal processing | As calculated (P323 formula) |
| 2â€“3 | No escalation | Same |
| 4â€“7 | Soft reminder | +0.5 to priority score |
| 7â€“14 | **Escalation level 1** | Promoted to MEDIUM, notification sent |
| 14â€“21 | **Escalation level 2** | Promoted to HIGH, escalation notification to reviewer |
| 21â€“30 | **Escalation level 3** | Promoted to CRITICAL, admin notification |
| 30+ | **Expiry review** | Candidate auto-demoted to LOW, moved to archival queue with "EXPIRED" note |

### 5.3 Escalation matrix

```
Day  0 â”€â”€â”€ Candidate enters queue (LOW / MEDIUM / HIGH / CRITICAL)
        â”‚
Day  7 â”€â”€â”€ If still unresolved â†’ soft escalation (+0.5 score)
        â”‚
Day 14 â”€â”€â”€ If still unresolved â†’ level 1 escalation (MEDIUM minimum, notification)
        â”‚
Day 21 â”€â”€â”€ If still unresolved â†’ level 2 escalation (HIGH minimum, admin notify)
        â”‚
Day 30 â”€â”€â”€ If still unresolved â†’ level 3 (CRITICAL, escalate to system owner)
        â”‚
        â””â”€â”€â†’ 35 days expiry â†’ auto-demote to LOW, archival queue
```

### 5.4 Retry limits

| Operation | Max retries | Cooldown | After max retries |
|---|---|---|---|
| Auto-match | 3 | 6 hours | Candidate moved to manual_review permanently |
| Auto-certify | 3 | 6 hours | Candidate moved to HOLD permanently |
| Staging sync | 5 | 1 hour | Log error, requires manual investigation |
| Drift check | 3 (per day) | 4 hours | After 3 failures â†’ escalate to ERROR |

---

## 6. Audit Requirements

### 6.1 Every queue transition logged

Every state change across all three queues must be recorded in the `review_actions` table (or equivalent audit destination).

### Required audit fields

```sql
CREATE TABLE review_actions (
    action_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id      TEXT NOT NULL,
    whisky_id        TEXT,
    queue_type       TEXT NOT NULL,        -- automatic | human | drift
    action_type      TEXT NOT NULL,        -- see below
    from_state       TEXT,
    to_state         TEXT,
    reviewer         TEXT,                 -- NULL for automatic actions
    justification    TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    -- For automatic actions
    auto_rule        TEXT,                 -- which rule triggered this?
    auto_score       REAL,                -- priority score at time of action
    -- For human actions
    human_interface  TEXT,                 -- reference to decision document
    review_duration  INTEGER,              -- seconds from queue entry to decision
    -- Cross-reference
    promotion_id     TEXT,                 -- link to audit_log if promoted
    rollback_ref     TEXT                  -- link to rollback log if rolled back
);
```

### Action types

| action_type | Used by | Description |
|---|---|---|
| `QUEUED` | All | Candidate entered a queue |
| `REMATCHED` | Automatic | Auto-matcher re-ran |
| `STAGING_SYNCED` | Automatic | Staging state updated to match production |
| `CERTIFIED` | Automatic | Certification engine passed |
| `HELD` | Automatic | Certification engine flagged field_ceiling |
| `HUMAN_APPROVED` | Human | Human approved match/provenance/certification |
| `HUMAN_HELD` | Human | Human chose to hold |
| `HUMAN_REJECTED` | Human | Human rejected candidate |
| `PROMOTED` | Automatic (post-execution) | Candidate written to production |
| `ROLLED_BACK` | Human | Promotion rolled back |
| `DRIFT_DETECTED` | Drift | Production deviation found |
| `DRIFT_CLEARED` | Drift | Deviation resolved |
| `BASELINE_UPDATED` | Drift | Baseline updated after expected change |
| `EXPIRED` | Automatic | Aging limit reached, moved to archival |

### Logging rules

| Rule | Implementation |
|---|---|
| Every queue entry â†’ `action_type=QUEUED` | On `INSERT` into queue |
| Every state change â†’ log with from/to | Before `UPDATE` on staging row |
| Every automatic action â†’ `reviewer=NULL, auto_rule=rule_name` | After execution, before commit |
| Every human action â†’ `reviewer=<identity>, justification=<text>` | After human decision form submission |
| Every drift detection â†’ log current values | On drift check completion |
| Every rollback â†’ `action_type=ROLLED_BACK, rollback_ref=<backup_path>` | Before restore, after authorization |

### Audit trail example (Clynelish 14yo lifecycle)

```
QUEUED              â†’ Clynelish entered human queue (match=manual_review, prov=HOLD)
  (waiting for human decision)
MATCH_REMATCHED     â†’ Automatic queue tried re-match â†’ still ambiguous
  (day 7: soft escalation)
  (day 14: level 1 escalation)
HUMAN_APPROVED      â†’ Reviewer: eltun â€” "Same evidence profile as approved batch"
STAGING_SYNCED      â†’ match_status=exact, provenance=APPROVED
PROMOTED            â†’ Written to flavor_evidence + tasting_notes (next batch)
BASELINE_UPDATED    â†’ Production SHA updated: cd87bb98... â†’ [new hash]
```

This audit trail is complete and self-verifying: every transition has a timestamp, actor, and justification.

---

## 7. Implementation Priority

| Component | Priority | Depends on | Effort estimate |
|---|---|---|---|
| `review_actions` table creation | **P0** | â€” | Low (1 SQL script) |
| Automatic queue: staging sync queries | **P0** | review_actions | Low (3 SQL UPDATEs) |
| Human queue: P320.5 decision integration | **P1** | review_actions | Medium |
| Drift queue: scheduled check | **P1** | review_actions, P315 baseline | Medium |
| Aging escalation scheduler | **P2** | review_actions | Medium |
| Expiry handler | **P3** | review_actions | Low |
| Source conflict detection | **P3** | flavor_evidence | High |

---

## Final Status

```
DESIGN COMPLETE

3 queue types with execution rules:
  Automatic:   6 allowed actions, 5 safety limits, 5 forbidden changes
  Human:       5 escalation triggers, 4 conflict resolution paths
  Drift:       4 severity levels, 4 rollback rules (never automatic)

Retry policy: 6-hour intervals, 4 escalation levels, 35-day expiry
Audit:        Every transition logged to review_actions table
              15 action types, 6 logging rules, complete audit trail
```

**No code. No database changes. No promotion.**

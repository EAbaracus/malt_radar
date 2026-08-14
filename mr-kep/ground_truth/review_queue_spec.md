# Review Queue Specification
## GSD Human Certification · Malt Radar MR-KEP

> **Document type:** Design specification — documentation only  
> **Authority:** P69 §6 (Review Workflow) · P70 §5 (Review Queue Workflow) · P70 §6 (Retirement Policy)  
> **Contracts reused:** Sprint 1 (frozen). No new schemas.  
> **No implementation. No production writes.**

---

## 1. Purpose

The Review Queue is the **controlled staging area** for GSD entries that are
under active human review or are blocked on a HOLD condition.

It enforces two guarantees:
1. No HOLD entry is accidentally treated as CERTIFIED.
2. No modification is ever applied directly to a CERTIFIED entry — updates
   always go through the queue first.

---

## 2. Directory Structure

```
mr-kep/ground_truth/
└── review_queue/
    │
    ├── GSD-0042_r2_PENDING.json        ← working copy (HOLD or active review)
    ├── GSD-0017_r1_PENDING.json        ← under first-time review
    ├── GSD-0093_r3_PENDING.json        ← post-certification update in progress
    │
    └── _queue_index.yaml               ← machine-readable queue manifest (human-maintained)
```

### 2.1 File Naming

Pattern: `GSD-{NNNN}_r{N}_PENDING.json`

| Part | Meaning |
|------|---------|
| `GSD-{NNNN}` | The permanent GSD entry ID |
| `r{N}` | The revision this PENDING copy will become on certification |
| `PENDING` | Marks the file as a working copy — not certified |

A PENDING file is the working copy. The live CERTIFIED file in `entries/` is
never modified while a PENDING copy exists.

### 2.2 _queue_index.yaml

Maintained manually by the reviewer after each session. Format:

```yaml
generated_at:   "ISO 8601 datetime"
total_in_queue: 3

entries:
  - gsd_id:            "GSD-0042"
    pending_file:      "review_queue/GSD-0042_r2_PENDING.json"
    review_status:     "HOLD"
    hold_gate:         "G7"
    hold_reason:       "source_url for abv field returned 404"
    hold_since:        "2026-07-14T10:00:00Z"
    session_count:     2
    reviewer:          "ELT"
    last_touched:      "2026-07-16T14:00:00Z"

  - gsd_id:            "GSD-0017"
    pending_file:      "review_queue/GSD-0017_r1_PENDING.json"
    review_status:     "PENDING_REVIEW"
    hold_gate:         null
    hold_reason:       null
    hold_since:        null
    session_count:     1
    reviewer:          "ELT"
    last_touched:      "2026-07-14T09:00:00Z"

  - gsd_id:            "GSD-0093"
    pending_file:      "review_queue/GSD-0093_r3_PENDING.json"
    review_status:     "REQUIRES_UPDATE"
    hold_gate:         null
    hold_reason:       "Producer corrected ABV on official page"
    hold_since:        null
    session_count:     0
    reviewer:          "ELT"
    last_touched:      "2026-07-18T11:00:00Z"
```

---

## 3. Entry States and Queue Membership

| State | In review_queue/? | In entries/? | Notes |
|-------|-----------------|-------------|-------|
| DRAFT | No | Yes (draft version) | Entry created; not yet submitted for review |
| PENDING_REVIEW | Yes | No (not certified yet) | First-time review in progress |
| HOLD | Yes | No (for first review) / Yes (for updates) | Blocked; PENDING copy is the working copy |
| VERIFIED | Yes | No | All 41 checklist items passed; computing confidence |
| CERTIFIED | No | Yes | Queue entry deleted; live file in entries/ |
| REQUIRES_UPDATE | Yes | Yes | PENDING copy is update; live file untouched until promoted |
| REJECTED | No | No (moved to rejected/) | Queue entry deleted; rejected/ has final snapshot |

**The queue contains only: PENDING_REVIEW, HOLD, REQUIRES_UPDATE entries.**  
DRAFT entries remain in `entries/` with `review_status: DRAFT` — they do not move
to the queue until submitted.

---

## 4. Queue Lifecycle

### 4.1 First-Time Certification (DRAFT → CERTIFIED)

```
Reviewer creates entry → entries/GSD-NNNN.json (DRAFT)
         │
         │ Reviewer submits for review
         ▼
Reviewer creates PENDING copy:
  cp entries/GSD-NNNN.json review_queue/GSD-NNNN_r1_PENDING.json
  Sets review_status = PENDING_REVIEW in PENDING copy
  Adds to _queue_index.yaml
         │
         │ Works on PENDING copy only
         ▼
All 41 checklist items PASS
All 10 gates PASS
         │
         ▼
PROMOTION (Stage 8 of certification_workflow.md):
  Set certification_status = CERTIFIED in PENDING copy
  mv review_queue/GSD-NNNN_r1_PENDING.json → entries/GSD-NNNN.json
  (overwrites the DRAFT version)
  Create change_history/GSD-NNNN_history.jsonl (empty stub)
  Update gsd_corpus_index.yaml → certified
  Remove PENDING file (implicit in mv)
  Remove from _queue_index.yaml
```

### 4.2 Post-Certification Update (REQUIRES_UPDATE)

```
Event triggers REQUIRES_UPDATE (see P69 §12.2)
         │
         │ Reviewer responds
         ▼
Reviewer creates PENDING copy of current live entry:
  cp entries/GSD-NNNN.json review_queue/GSD-NNNN_r{N+1}_PENDING.json
  Sets review_status = REQUIRES_UPDATE in PENDING copy
  Increments revision in PENDING copy: r{N} → r{N+1}
  Adds to _queue_index.yaml
         │
         │ Works on PENDING copy ONLY
         │ entries/GSD-NNNN.json is UNTOUCHED during this period
         ▼
Affected gates re-evaluated (only gates relevant to the change)
All relevant gates PASS
Confidence recomputed
         │
         ▼
PROMOTION:
  Snapshot current live entries/GSD-NNNN.json (the r{N} version)
  Append snapshot + change_record to change_history/GSD-NNNN_history.jsonl
  mv review_queue/GSD-NNNN_r{N+1}_PENDING.json → entries/GSD-NNNN.json
  Update gsd_corpus_index.yaml → current_revision = r{N+1}
  Remove from _queue_index.yaml
```

### 4.3 HOLD Protocol in Queue

```
Any gate fails during PENDING_REVIEW
         │
         ▼
Update PENDING copy:
  review_status = HOLD
  hold_gate = "G{N}"
  hold_reason = "description of blocking issue"
  hold_since = current ISO datetime
Update _queue_index.yaml
         │
         │ Entry waits in queue
         │ Reviewer researches blocking issue in separate sessions
         ▼
Issue resolved → return to PENDING_REVIEW state:
  review_status = PENDING_REVIEW
  hold_gate = null
  (hold_reason retained for traceability)
Re-run checklist from failing gate onward
```

---

## 5. Queue Capacity Rules

| Rule | Limit | Reason |
|------|-------|--------|
| Maximum simultaneous PENDING entries per reviewer | 5 | Prevents reviewer context-switching overhead |
| Maximum simultaneous HOLD entries | No hard limit | HOLDs may age while sources are researched |
| HOLD age before escalation check | 5 sessions | Triggers ESCALATION_DECISION in decision tree |
| REQUIRES_UPDATE age before escalation check | 30 days | Long-running updates require project owner review |

If queue exceeds 5 PENDING entries for a single reviewer, new entries should not be
started until the backlog drops to ≤ 3.

---

## 6. Review Session Protocol

A **review session** is a contiguous period of work on one or more GSD entries.

### 6.1 Session Start Checklist

```
[ ] Read AGENTS.md (if more than 7 days since last session)
[ ] Read mr-kep/authority/confidence.yaml (confirm threshold values unchanged)
[ ] Open _queue_index.yaml — note current HOLD counts and ages
[ ] Select target entry (use batch certification order from certification_workflow.md §8)
[ ] Open PENDING copy (or create one if starting fresh)
[ ] Note session_start time
```

### 6.2 Session End Checklist

```
[ ] Save PENDING copy with all changes for this session
[ ] Update session_count in _queue_index.yaml
[ ] Update last_touched in _queue_index.yaml
[ ] Note session_end time in entry header (optional but recommended)
[ ] Update review_status and hold_gate if state changed
[ ] If CERTIFIED: complete Stage 8 promotion steps
[ ] If REJECTED: move to rejected/, update index, retire ID
```

---

## 7. Retirement Policy (from P70 §6)

An entry is retired (rejected) when it cannot be certified after sufficient effort.

### 7.1 Retirement Triggers

| Trigger | Required Evidence | Action |
|---------|-----------------|--------|
| 5+ HOLD sessions on same gate | Session count in _queue_index.yaml | Escalation decision |
| No T1 source exists for identity fields | Documented search history | REJECTED |
| T1 source permanently unreachable; no archive exists | HTTP status check + archive search | REJECTED |
| Entry was a duplicate of an already-CERTIFIED entry | Cross-reference to certified ID | REJECTED with duplicate_of field |
| Reviewer determines entry is out of scope | Documented rationale | REJECTED |

### 7.2 Retirement Procedure

```
1. Set final review_status = REJECTED in PENDING copy.
2. Add rejection fields:
     rejection_reason: "string — specific reason"
     rejected_at: "ISO 8601 datetime"
     rejected_by: "reviewer identifier"
     duplicate_of: "GSD-NNNN" (or null)
3. mv review_queue/GSD-NNNN_rN_PENDING.json → rejected/GSD-RJCT-NNNN.json
   (rename: NNNN stays the same; GSD-RJCT prefix marks it as retired)
4. Update gsd_corpus_index.yaml:
     certification_status: REJECTED
     file: rejected/GSD-RJCT-NNNN.json
5. Remove from _queue_index.yaml.
6. Mark GSD-NNNN as permanently retired: id_retired: true in index entry.
7. Select replacement candidate from candidate_list.csv.
   Add replacement as new GSD entry with next available NNNN.
```

### 7.3 ID Retirement Rule

Once a GSD-NNNN ID is retired (REJECTED), it is **permanently retired**.
It is never reassigned to a new entry, even after the rejected file is archived.
The ID gap in the sequence is permanent and expected.

---

## 8. Integrity Checks

The reviewer should perform these checks at the start of each working week:

### 8.1 Queue Integrity Check

```
Verify:
[ ] Every file in review_queue/ appears in _queue_index.yaml
[ ] Every entry in _queue_index.yaml has a file in review_queue/
[ ] No file in review_queue/ has certification_status = CERTIFIED
    (CERTIFIED entries must be in entries/, not review_queue/)
[ ] No PENDING file has a revision that already exists in the live entries/ file
    (would indicate promotion was partially executed)
```

### 8.2 History Integrity Check

```
For every CERTIFIED entry:
[ ] A companion GSD-NNNN_history.jsonl exists in change_history/
[ ] If revision ≥ r2, the history file has (revision - 1) lines at minimum
[ ] No history line was edited (append-only — last line should be newest)
```

### 8.3 Index Integrity Check

```
[ ] Count of certified_entries in index matches files in entries/ with certification_status=CERTIFIED
[ ] Count of hold_entries matches entries in _queue_index.yaml with review_status=HOLD
[ ] Count of rejected_entries matches files in rejected/
[ ] sha256_of_entries_dir in index is current (recompute and compare)
```

---

## 9. Definition of Done

The review queue design is **done** when:

```
[ ] This document approved by project owner
[ ] certification_workflow.md cross-references this document at HOLD and update steps
[ ] _queue_index.yaml template instantiated (empty, with structure only)
[ ] Integrity check procedures are understood by all reviewers
[ ] No test entries created yet (corpus population not started)
```

---

## 10. GO / NO-GO

### Specification Verification

| Check | Status |
|-------|--------|
| Only Sprint 1 contracts used | ✅ PASS |
| No new schemas | ✅ PASS |
| No implementation code | ✅ PASS |
| No production writes | ✅ PASS |
| Deterministic state machine | ✅ PASS |
| Human-only certification authority | ✅ PASS |
| Evidence-first (queue records all evidence) | ✅ PASS |
| All P70 §5 queue requirements addressed | ✅ PASS |
| All P70 §6 retirement requirements addressed | ✅ PASS |
| production.db SHA-256 unchanged | ✅ PASS |

```
STATUS: GO — Review queue specification complete.
```

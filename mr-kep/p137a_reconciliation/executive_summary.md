# P137A — Executive Summary (contract for P137B)

- doc_version: P137A-1
- date_utc: 2026-07-17
- this task: DOCUMENTATION + DECISION RECORD only. No schema mutation needed.
  knowledge.db already satisfies the contract; P137B may proceed.

## What P137B should assume (ground truth, proven this session)

### Schema
- Canonical source column = **`source_id`** (FK→sources). `source_key` does NOT exist
  and is NOT required. See `mr-kep/CANONICAL_SCHEMA.md` §1.
- knowledge.db has all 14 tables, populated: `normalized_metadata`=724,
  `canonical_flavor_vectors`=791, `citations`=2.246, `evidence`=724,
  `promotion_queue`=2.664, `review_queue`=1.431, `merge_history`=0.
- `official_source_references` lives in **production.db** (96 rows), NOT knowledge.db.
  D2's "osr reuse" means promotion (P138) reads production.osr — it is not
  duplicated into knowledge.db.

### The real ready set (NOT 726)
- **2.664 promotion_queue rows over 724 whiskies**, all citation-backed, confidence ≥0.90.
- Breakdown: age 724 + abv 707 + cask_type 627 + region 606.
- 726 is the book-PDF MERGE count (different population) — ignore for SMWS promotion.

### Crosswalk
- **Not required** for P137B (SMWS path uses promotion_queue.entity_key = production
  whisky_id directly). Deferred to a future book-promotion task (D5).

### Decisions recorded
- `mr-kep/decision_log.jsonl` now contains D1–D5 (target DB, source_id canonical,
  consensus-vector load, count relationship, crosswalk deferral).

## Is the ground solid for P137B?
**YES for the SMWS promotion path.** The earlier "P136 COMPLETE" claim is now
*evidenced*, not asserted: live counts + a canonical-schema contract + D1–D5 decision
log all exist. The only open items (osr-in-knowledge.db, crosswalk integration,
book-UUID promotion) are explicitly deferred, not silently assumed.

## Constraints honored
- production.db: read-only (hash `d842b118…ec62961` unchanged this session).
- knowledge.db: no mutation performed by P137A (documentation only).
- No commit/push. No DROP/RENAME. Temp scripts cleaned.

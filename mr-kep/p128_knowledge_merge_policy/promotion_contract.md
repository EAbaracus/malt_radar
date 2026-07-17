# P128 — Promotion Contract (READ-ONLY policy)

The binding contract every book-knowledge promotion MUST satisfy before any future write to
`production.db`. Grounded in real tables: `staging_manual_review_queue`, `review_actions`,
`review_status_transitions`, `review_conflict_log`, `promotion_audit_log`, and the P121 write-gate.
**Specification only — no staging, no production writes, no promotion performed here.**

## Preconditions (ALL must hold before promotion)
1. **P121 write-gate** is the sole write chokepoint; production.db opened RW only through the gate.
2. **Backup taken** (AGENTS.md: backup → inspect → apply → verify).
3. Candidate carries a **resolver classification** (P127: MERGE / CREATE / AMBIGUOUS) + confidence.
4. Candidate satisfies its **field class rule** (`field_merge_matrix.md`).
5. Candidate has ≥ 1 **citation** ready for `official_source_references`. No citation → no promotion.

## Promotion eligibility by bucket
| Bucket | Eligible to auto-promote? | Path |
|---|---|---|
| MERGE, conf ≥ 0.90, APPEND/REPLACEABLE field | Yes (with citation) | direct enrich via gate |
| MERGE, REVIEW-REQUIRED field | No | staging_manual_review_queue |
| CREATE, conf ≥ 0.70, non-review entity | Conditional | review for distillery/brand/bottler; else stage |
| CREATE distillery/brand/bottler | No | human review mandatory |
| AMBIGUOUS (all 3,556) | No | 100% human review |
| conf < 0.50 | No | REJECT |
| any price field | Never | excluded entirely |

## Contract clauses
### C1 — Citation completeness
Every promoted field change writes exactly one `official_source_references` row: `entity_type, entity_id, source_category, source_name, field_name, field_value, confidence, license_risk, copyright_risk`. Missing any → promotion rejected.

### C2 — Idempotency
Re-running promotion for the same (entity, field, source_hash) is a no-op. Dedupe on citation `source_hash` + field. Prevents double-append (e.g. #11/#42 byte-duplicate books).

### C3 — Field-class enforcement
Promotion engine reads `field_merge_matrix.md` classes at runtime:
- IMMUTABLE → reject write, cite only.
- APPEND-ONLY → append, never overwrite.
- REPLACEABLE → overwrite only if conf ≥ threshold AND authority ≥ incumbent.
- REVIEW-REQUIRED → divert to queue.

### C4 — Conflict handling
Any conflict (per `conflict_resolution_rules.md`) logs to `review_conflict_log` and blocks auto-promotion of that field until resolved via `review_actions`.

### C5 — Audit trail
Every promotion action logs to `promotion_audit_log` (knowledge.db `audit_logs` mirrors run-level). Status transitions recorded in `review_status_transitions`. Fully reversible via backup.

### C6 — License/copyright gate
`license_risk` / `copyright_risk` assessed at ingest are IMMUTABLE. HIGH-risk book text is NOT promoted verbatim to user-facing fields — only derived facts (dates, ABV, region), never copyrighted prose. Tasting-note prose stays in evidence layer, surfaced only as derived flavor vectors.

### C7 — Price firewall (AGENTS.md Product Rule)
No promotion path may write `production_price`, `price_history`, or expose price in UI/API. Enforced at contract level, not just field level.

## Optimal promotion order (from P126/P127)
1. **MERGE** enrichments (16,725) — lowest risk, fills gaps in existing entities.
2. **CREATE non-review** (expressions, terminology) — conf ≥ 0.70.
3. **CREATE distillery/brand/bottler** (incl. 536 B4b) — after human review.
4. **AMBIGUOUS** (3,556) — human decision, batched by entity type.
5. **Flavor vectors** — only via knowledge.db consensus, never direct.

## Verification gate (post-promotion, per AGENTS.md Completion)
Before declaring any future promotion successful:
- verify row counts changed as expected;
- verify no IMMUTABLE/price field mutated (hash-compare price columns);
- verify citation count == applied-change count;
- verify canonical_vectors only changed via consensus;
- check git status; check `promotion_audit_log` completeness.

## Contract status
**This contract is DESIGN-COMPLETE and READ-ONLY.** No entity has been promoted. Execution is deferred to a future explicitly-approved promotion task operating through the P121 write-gate.

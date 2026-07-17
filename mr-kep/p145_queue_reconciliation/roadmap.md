# P145 — Roadmap (Phase 6)

Evidence-backed next phases only. No invented work.

## 1. P146 (optional, authorized WRITE) — Promote the 3 READY_NULL_FILL rows
   - 2 abv + 1 age, guarded NULL_FILL (reuse P139/P142 harness).
   - Exclude the 3 INVALID age rows (111/63/100).
   - Expected gain: +3 fields (marginal). Closes promotion_queue NULL_FILL entirely.

## 2. P147 (optional) — Triage REVIEW_REQUIRED (78 rows)
   - 75 are benign region format diffs (already in production) -> mark resolved, no write.
   - 3 (abv/age) are genuine diffs -> manual/LLM review before any overwrite decision.
   - Overwrite is FORBIDDEN by STRICT RULES; these need explicit human adjudication.

## 3. P148 (future, requires NEW sources) — External/LLM enrichment
   - cask_type 4,068 NULLs, region 3,802 NULLs, country 4,614 NULLs have NO queue evidence.
   - Gains require downloading/extracting NEW sources (books LLM, external API, OCR).
   - Out of scope for promotion_queue; needs a sourcing task.

## 4. P149 (optional WRITE) — Prune knowledge.db promotion_queue
   - After P146/P147, remove NO_CHANGE+INVALID (2,583 rows) -> 81 live rows.
   - Keeps knowledge.db accurate. Separate authorized WRITE.

## Verdict on promotion_queue
**The promotion_queue is effectively EXHAUSTED for automated NULL_FILL** (3 rows remain).
No further large promotion is possible from existing evidence. Do not invent promotion work.

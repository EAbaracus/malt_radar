# P203 — Roadmap

Maps the canonical entity model to upcoming epics. Design phase complete; execution is
a separate (future) task — no code/DB changes made here.

## Now (P203, this phase — DONE)
- [x] READ-ONLY audit of production.db + knowledge.db + matcher + adapters + crosswalk.
- [x] 13 evidence-backed deliverables under `mr-kep/p203_entity_resolution/`.
- [x] Verdict: **WARN_GO** (design-complete, implementation-gated).

## Next — Implementation task (proposed P203-B / P210-ish)
1. Unify normalizer (B4b OCR rules → `normalize_text`); add token + phonetic scorers.
2. Extend `entity_aliases` enum + add `alias_class`; make matcher alias-aware + multi-entity.
3. Activate P129 crosswalk under the gated policy (exact/strong+check/human-reviewed).
4. Add `series` / `edition` staging entities.

## P300 — External Source Expansion
- All new sources resolve through the canonical matcher; external IDs →
  `external_entities` + `entity_external_links` (crosswalk-gated).

## P400 — LLM Knowledge Extraction
- LLM `normalized_name` / distillery / bottler guesses routed through the multi-entity
  matcher; book UUID `entity_key` upgraded via activated crosswalk before promotion.

## P500 — Production Quality & Release
- Close coverage gaps (`distillery_id`, `country`, `region`, …) via `promotion_queue`
  (reuse P139 harness from `p143`).
- `review_queue` + `merge_history` + `confidence` ledger provide release audit trail.

## Gate between phases
- No phase may write production.db/knowledge.db without AGENTS.md DB-safety
  (backup → impact → apply → verify) and the price-never-exposed rule.
- Crosswalk auto-activation stays forbidden until exact/strong matches exist or human
  review clears the 475 weak rows (D5).

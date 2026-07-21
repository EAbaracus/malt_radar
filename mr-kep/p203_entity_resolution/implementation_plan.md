# P203 — Implementation Plan (read-only this phase; execution deferred)

This phase is **design only**. Below is the ordered execution plan for the follow-on
implementation task (not performed here — no code changes, no DB writes).

## Phase A — Normalizer unification (reuse)
1. Promote `B4b/classify_unresolved.py` OCR rules (`OCR_JUNK_RE`, `DIST_SINGULAR_RE`)
   into the single `normalize_text` used by `matching.py`.
2. Add `token_set_ratio` + a phonetic signal (soundex/metaphone) as *supplementary*
   scorers alongside `SequenceMatcher` (thresholds 0.94/0.88/0.82 preserved).

## Phase B — Alias-aware matcher
3. Extend `entity_aliases.entity_type` enum to include `'whisky'` (and `'series'`,
   `'edition'`) — DDL migration (AGENTS.md DB-safety: backup → impact → apply → verify).
4. Add `alias_class` column (official/historical/ocr/editorial/book/csv/smws/community).
5. Make `WhiskyRegistryMatcher` consult `entity_aliases` (class-weighted boost) BEFORE
   fuzzy fallback, and mirror the matcher for distillery/brand/bottler.

## Phase C — Crosswalk activation (gated)
6. Load P129 crosswalk rows ONLY where EXACT / STRONG+expression-check / human-reviewed.
7. Persist activated links as `entity_external_links` + `merge_history` (dedupe_key).
8. Any collision → `review_queue` issue_type `conflict`.

## Phase D — New entity types
9. Add `series` / `edition` staging tables in knowledge.db; promote via `promotion_queue`.

## Phase E — Coverage closure (P500)
10. Promote high-confidence `distillery_id` / `country` / `region` candidates
    (reuse P139 harness per `p143`) through `promotion_queue` field_class gating.

## Verification gates (each step)
- Idempotency: re-run yields identical `evidence_id` / `match_status` (proven in P202).
- DB safety: `production.db` / `knowledge.db` hashes unchanged except intentional writes,
  which follow backup→impact→apply→verify.
- No price exposure: matcher/extractor never surface price fields (AGENTS.md product rule).

## Reuse checklist (do NOT reinvent)
- `normalize_text` logic (matching.py) — extend, don't rewrite.
- `scripts/external_sources/match_structured_ml_whiskey_source_to_production.py` — proven origin.
- `authority/*.yaml` + `resolution/source_resolution_model.yaml` — source tier → confidence weight.
- `p129_crosswalk/` CSV + validation — canonical crosswalk artifact.
- `B4b` OCR rules — canonical OCR normalizer seed.
- `knowledge.review_queue` / `merge_history` / `promotion_queue` — the human/audit gates.

# P203B — Implementation

> WRITE phase implementing the approved P203 design (architecture unchanged).
> Crosswalk lives in `knowledge.db` (reference layer); `production.db` left byte-identical.

## PHASE 1 — Schema
- Implemented `distillery_crosswalk` + `distillery_crosswalk_review` exactly per P203 `crosswalk_schema.md`.
- Append-only (`UNIQUE(entity_id, external_name, source)`); indexed on external_name, entity_id, source.
- Logical FK to canonical `distilleries.distillery_id` (cross-DB, validated — see validation.md).
- Migration is reversible via `rollback.sql` (DROP TABLE both). No unrelated schema touched.

## PHASE 2 — Normalization (approved rules only)
- unicode NFKC-style strip, lowercase, punctuation→space, apostrophe normalize, 'The' prefix drop,
- stop-word removal: distillery/ltd/owner/marketing/region suffixes (identical STOP set to P203).
- **No new heuristic rules introduced.**

## PHASE 3 — Alias Resolution
- Seeded **2144** production self-alias rows (every `distilleries.name` variant → its distillery_id, confidence 1.0).
- Generated external aliases from books/new.csv + P119_6 staging CSVs, each preserving source/method/confidence.
- **No automatic canonical creation** — unmatched names go to review queue, not new entities.

## PHASE 4 — Matching (deterministic order)
- exact → normalized (canonical key) → (no phonetic/embedding/AI; explicitly excluded).
- Resolved 376 external names; queued 55 to manual review.

## PHASE 5 — Confidence (existing policy)
- Auto-resolve threshold = **0.7** (exact 1.0, normalized 0.9, ambiguous 0.85).
- Everything below threshold → `distillery_crosswalk_review` (nothing discarded).

## PHASE 6 — Validation
- Re-ran P202B 17-row sample: **15 resolved / 2 to review** (expected ~15/17).
- FK integrity: 0 bad; duplicate canonical mappings: 0; integrity_check: ok.

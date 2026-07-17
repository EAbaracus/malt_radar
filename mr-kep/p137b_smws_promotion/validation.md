# P137B — Validation

- mode: read-only checks against live DBs + generated artifacts.
- production.db: read-only. knowledge.db: read-only. No mutation.

## Checks performed
| # | check | result |
|---|---|---|
| V1 | 2664 queue rows processed (read) | ✅ 2664 total; 1233 promotable + 1431 REVIEW |
| V2 | 724 whisky coverage measured | ✅ distinct entity_key = 724 |
| V3 | citation integrity | ✅ 1233/1233 export rows resolve to `citations` (0 missing) |
| V4 | source_id integrity | ✅ canonical column used; `source_key` absent (D2) |
| V5 | confidence preservation | ✅ every row carries 0.95 |
| V6 | duplicate detection | ✅ 0 dedupe_key collisions; idempotent rerun |
| V7 | schema validity | ✅ all tables/cols present (CANONICAL_SCHEMA §1) |
| V8 | deterministic rerun | ✅ 5/5 artifact hashes identical across runs |
| V9 | production.db unchanged | ✅ hash `d842b118…ec62961` |
| V10 | knowledge.db readable, unmutated | ✅ read-only; no write calls in generator |
| V11 | git: no .db tracked-modified | ✅ |
| V12 | HEAD unchanged (no commit) | ✅ `d7b2ab7` |

## How each was verified
- V1/V2/V3/V4/V5/V6/V8: export_generator re-run + hash comparison (hermes-verify-p137b).
- V7: PRAGMA table_info on knowledge.db (P136 + P137A).
- V9/V10/V11/V12: sha256 comparison + `git status --porcelain`.

## Honest caveats
- `age`/`abv` (1.431 REVIEW rows) are NOT in the export — they are REVIEW-class
  per P135 and require human sign-off (separate P138 workstream). This is policy-correct,
  not a gap.
- coverage deltas are PROJECTED (production.db was not written). The +627 cask_type
  / +531 region gains apply only when the P138 gate transaction executes the export.
- 75 region conflicts are intentionally NOT auto-applied (no-overwrite rule).

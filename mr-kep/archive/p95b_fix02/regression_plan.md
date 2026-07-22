# P95B-FIX-02 — Regression Plan

**Goal:** prove the full canonical 7-axis contract (`smoky, peaty, fruity, sweet, spicy, maritime,
sherry`) is preserved end-to-end after the Phase 12 blocking fixes, with zero production mutation.

---

## Test suite
`mr-kep/p95b_fix02/test_canonical_axes.py` — **7 tests, all passing** (run:
`python -m pytest mr-kep/p95b_fix02/test_canonical_axes.py -q`).

| Test | Asserts |
|---|---|
| `test_canonical_axes_complete` | the 7 frozen axes are exactly the contract (incl `maritime`) |
| `test_flavor_mapper_covers_all_seven_axes` | every canonical axis reachable by ≥1 descriptor |
| `test_flavor_mapper_maritime_descriptors` | `salt/brine/seaweed/coastal/sea spray/marine/salty` → `maritime` |
| `test_flavor_mapper_no_rich_canonical` | `rich` unmappable; not in canonical set |
| `test_axis_reducer_emits_canonical_seven_incl_maritime` | reducer output keys == canonical 7; maritime populated; `rich` queued ambiguous |
| `test_axis_reducer_no_legacy_vocabulary` | no `Smoke/Medicinal/Woody/Floral` legacy keys |
| `test_db_read_service_exposes_maritime` | `APP_AXES` includes `maritime`; `_normalize_flavor_profile` preserves stored maritime |

## Pre-promotion gate (must pass BEFORE executing migration.sql)
1. **Regression green** — 7/7 pytest passed. ✅ (done this task)
2. **production.db untouched by code edits** — confirmed SHA `8350fe9d…` unchanged. ✅
3. **migration.sql staged, NOT executed** — `vector_maritime` column confirmed absent. ✅

## Post-execution gate (only after explicit human GO + backup, per promotion_rulebook.md §6)
- `vector_maritime` column now exists in `flavor_evidence`.
- Historical rows `vector_maritime IS NULL` (expected; no backfill possible).
- Re-run pytest → still 7/7 (pure-function tests unaffected by DB state).
- A sampled re-promotion of one maritime-bearing evidence row lands `vector_maritime` non-NULL.

## Out-of-scope / deferred
- **0-1 → 0-100 scale normalization** of existing `flavor_evidence` columns: optional, commented
  in `migration.sql`, separate review (higher risk). Not required to close the maritime gap.
- **Backfill of `vector_maritime`** for historical rows: requires re-extraction; not done here.

## Result
All seven canonical axes are represented and preserved across mapper, reducer, and client layers.
`maritime` is no longer dropped at the mapper, the reducer, or the read service. `vector_rich`
remains as deprecated legacy evidence. Regression: **7 passed**. No production DB mutation occurred.

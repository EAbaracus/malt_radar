# P95B Phase 12 — Post-Validation Report

**Mode:** post-execution verification. production.db was mutated under authorization; this
report records the gates that passed and the regression result.

---

## Validation gates (all PASS)
| # | Gate | Expected | Actual |
|---|---|---|---|
| 1 | migration committed | true | ✅ true |
| 2 | `vector_maritime` column exists | true | ✅ true |
| 3 | evidence row count | 791 → 987 | ✅ +196 |
| 4 | `evidence_id` uniqueness | count == distinct | ✅ [987, 987] |
| 5 | no NULL `whisky_id` promoted | 0 | ✅ 0 |
| 6 | promoted profiles = exactly 7 canonical axes | 0 bad | ✅ 0 (0 new profiles) |
| 7 | maritime preserved | >0 non-null | ✅ 196 non-null |
| 8 | `rich` absent from canonical output | not introduced | ✅ (legacy 791 retained, new=NULL) |
| 9 | `PRAGMA integrity_check` | ok | ✅ ok |
| 10 | regression (P95B-FIX-02, 7 tests) | pass | ✅ `7 passed in 0.13s` |

## Scale consistency
New `flavor_evidence.vector_*` values are 0-100 (canonical). Pre-existing 791 rows
remain 0-1 (their own historical scale) — **not** overwritten (authority preserved).
Future backfill of historical `vector_maritime` (NULL for the 791 legacy rows) is a
separate, explicitly-authorized action and was NOT performed here.

## Data integrity
- 196 new `flavor_evidence` rows, all with `source` ∈ {`book`, `tasting_note`}.
- 0 `flavor_profiles` rows inserted (all target `whisky_id`s pre-existed → no overwrite).
- 75 tasting notes correctly skipped (no canonical tokens) and logged for review.

## Regression detail
```
pytest mr-kep/p95b_fix02/test_canonical_axes.py -q  →  7 passed in 0.13s
```
Covers: 7-axis completeness, `maritime` descriptor mapping, `rich` unmappable,
reducer emits canonical 7 incl `maritime`, no legacy vocabulary, `db_read_service`
exposes `maritime`.

## Conclusion
All 10 validation gates + regression pass. The canonical flavor contract is preserved:
`maritime` now flows into production evidence; `rich` remains legacy-only; no
authority data was overwritten.

**Final Status: PASS — Phase 12 completed successfully.**

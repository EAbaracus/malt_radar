# P95B Phase 12 — Production Diff Report

**Before:** `8350fe9de2f1c73d9c4b6930bae607afe64696527910c2709b8b3a4a634c6a3a` (791 evidence rows)
**After:**  `704fee10138560b18492557feb1bd97a4a8dac35256d5dbae57c6c5a607323a1` (987 evidence rows)

---

## Schema diff
| Object | Before | After |
|---|---|---|
| `flavor_evidence.vector_maritime` | absent | **present (REAL, nullable)** |
| `flavor_evidence.vector_rich` | present (legacy) | retained (not dropped) |
| `flavor_evidence` row count | 791 | **987 (+196)** |
| `flavor_profiles` row count | 3467 | 3467 (0 inserted — INSERT skipped where `whisky_id` already had a profile) |

> No existing `flavor_profiles` row was modified (INSERT skipped where
> `whisky_id` already had a profile). Authority data (T1/T2) preserved.

## Evidence diff (sample promoted rows — all 7 canonical axes @0-100)
| whisky_id | source | smoky | peaty | fruity | sweet | spicy | **maritime** | sherry |
|---|---|---|---|---|---|---|---|---|
| W002573 | book | 44 | 55 | 50 | 50 | 35 | **35** | 44 |
| W002442 | book | 44 | 35 | 82 | 70 | 70 | **35** | 62 |
| W001980 | book | 50 | 55 | 50 | 35 | 35 | **35** | 35 |
| W000014 | book | 50 | 55 | 72 | 68 | 59 | **68** | 44 |
| W002288 | book | 62 | 35 | 50 | 65 | 44 | **35** | 44 |
| W001980 | tasting_note | 50 | 55 | 50 | 35 | 35 | **35** | 35 |

`vector_maritime` is now non-NULL for **all 196** new rows (previously impossible).

## Canonical contract vs existing data
- **New rows (196):** exactly the 7 canonical axes, 0-100 scale, `maritime` populated.
- **Pre-existing rows (791):** unchanged (still 0-1 scale, `vector_rich` retained,
  `vector_maritime` NULL). These are historical authority data and were deliberately
  **not** backfilled or rescaled — a separate, explicitly-authorized action.
- **`rich` status:** never introduced into canonical output; legacy `vector_rich` on the
  791 older rows remains as documented provenance.

## Skipped (not promoted) — 75 tasting notes
Reason: `matched_master_whisky_id` resolved + not rejected, but the note free-text
contained **no canonical descriptor tokens** (lexicon: sea/salt/peat/apple/honey/…).
Full list with `whisky_id` + `staging_note_id` in `promotion_audit_log.json`.
These are candidates for lexicon expansion, not data loss.

## Conclusion
The diff is **additive and contract-compliant**: +1 column (`vector_maritime`),
+196 canonical-evidence rows with `maritime` intact, zero authority overwrites,
legacy `vector_rich` preserved.

**Final Status: PASS — Phase 12 completed successfully.**

# P129 — Crosswalk Validation

- validation_version: P129-1
- mode: READ-ONLY; no DB mutation
- deliverables under `mr-kep/p129_crosswalk/`: `uuid_whisky_crosswalk.csv`, `crosswalk_collisions.csv`, `crosswalk_nomatch.csv` (aux), `crosswalk_statistics.md`, this file.

## Validation checklist
| # | check | result |
|---|---|---|
| 1 | 790/790 UUID rows processed (no lost row) | ✅ crosswalk 475 + collisions 0 + no-match 315 = 790 |
| 2 | Every crosswalk row has exactly one `matched_w_id` | ✅ 475/475 single match; collisions separated to own file |
| 3 | Confidence formula transparent (documented in statistics.md) | ✅ |
| 4 | Same fuzzy algorithm/threshold as P127/P127.5 | ✅ `difflib.SequenceMatcher` + stopword normalization, identical to P127.5 manifest |
| 5 | `matched_w_id` FK validity = 100% | ✅ 475/475 present in `whiskies` |
| 6 | Duplicate `uuid_whisky_id` = 0 | ✅ no uuid appears twice in crosswalk |
| 7 | Collisions NOT auto-resolved (separate file) | ✅ 0 collisions; file is header-only valid frame |
| 8 | No-match rows excluded from crosswalk | ✅ 315 in `crosswalk_nomatch.csv`, absent from crosswalk |

## FK validity detail
- Query: `SELECT COUNT(*) FROM whiskies WHERE whisky_id = <matched_w_id>` for each crosswalk row.
- Result: **475/475 valid** (every `matched_w_id` is a real `W…` row in `whiskies`).
- Re-verified live against `production.db` (read-only) during this run.

## Duplicate / inclusion checks
- `uuid_whisky_id` distinct in crosswalk = 475 = row count → **0 duplicates**.
- Sum of (crosswalk + collision + no-match) = 790 = total UUID input → **full coverage, 0 orphan**.

## P128 D3 applicability
- Exact+Strong match total = **0** (0 exact + 0 strong).
- Implication: **B2 is NOT closed.** The crosswalk proves the *structural* path (uuid → W-id → consensus_nodes) exists for 475 rows, but the confidence is uniformly weak (0.50–0.60), below P128 §5's implicit requirement for deterministic, review-free derivation.
- 443 of the 726 P127.5 MERGE uuids are present in the crosswalk (weak); the remaining 283 MERGE uuids are in the 315 no-match set (their distillery_id is absent from the W-set) → those 283 MERGE vectors have **no** bridge at all.

## Verdict input for P128
- This crosswalk is **complete and internally valid** (all 8 checks pass), but it does **not** by itself convert B2 to "ready".
- Recommended path before P128 gate retry: either (a) build a higher-confidence key — e.g. backfill `smws_code` onto `W…` rows and join uuid↔W by SMWS code (the only true shared business key, currently present only on uuid-side), or (b) route the 475 weak + 315 no-match rows to a manual review queue and obtain a policy waiver for the 443 MERGE overlaps.

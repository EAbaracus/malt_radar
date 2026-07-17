# P129 — UUID ↔ whisky_id Crosswalk Statistics

- crosswalk_version: P129-1
- date_utc: 2026-07-16
- mode: READ-ONLY (gate via `get_read_connection`; `?mode=ro` + `query_only=ON`); zero DB mutation
- input: production.db `whiskies` (4,749 rows = 3,959 `W…` + 790 `uuid`)
- purpose: close P128 preflight blocker **B2** (UUID↔W-id crosswalk for D3 consensus-via vector load)

## Counts (deterministic matcher, rules as specified in task)
| bucket | count | confidence |
|---|---|---|
| Total UUID rows | **790** | — |
| Exact match (distillery+age+abv±0.1) | **0** | 1.0 |
| Strong match (distillery+age±1.0 OR distillery+name_fuzzy≥0.85) | **0** | 0.7–0.9 |
| Weak / ambiguous (distillery_id only, or distillery+name_fuzzy 0.5–0.85) | **475** | <0.7 (review required) |
| No match (net-new; not in crosswalk) | **315** | — |
| Collision (≥2 candidates ≥0.7) | **0** | — |

**Coverage proof:** 0 + 0 + 475 + 315 + 0 = **790** ✅ (full coverage, no lost row)

## Weak-match confidence distribution (475 rows)
| confidence | rows | basis |
|---|---|---|
| 0.60 | 423 | distillery_id only (W-row age/abv/name too sparse to corroborate) |
| 0.50–0.53 | 52 | distillery_id + name_fuzzy 0.50–0.85 (partial name overlap) |

All 475 weak rows carry `match_type=weak` and fall below the 0.7 threshold → flagged **"review required"** per task rule 3.

## No-match breakdown (315 rows)
| reason | rows |
|---|---|
| `distillery_id_absent_from_W_set` | 315 |

Every no-match UUID's `distillery_id` does **not** appear in any `W…` row. These 315 are candidates for genuinely net-new entities (or their distillery was only ever ingested via the UUID/SMWS importer). They are excluded from the crosswalk and listed in `crosswalk_nomatch.csv`.

## Why exact/strong = 0 (critical finding)
The task assumed distillery+age+abv or name-fuzzy would yield high-confidence matches. Ground-truth data contradicts this:
- **SMWS-code overlap uuid∩W = 0** (uuid-set has 790 distinct smws_code; W-set has 1). So SMWS code — the one shared business key — is unusable as a join path.
- W-rows are heavily NULL: **age 78.8%**, **abv 64.3%**, **distillery_id 48.8%**, **original_name 85.3%**. With age/abv missing, the exact and strong-A rules cannot fire.
- Only **41 of 94** uuid `distillery_id`s exist in the W-set; 53 uuid distilleries have no W counterpart → those 315 become no-match.
- Where a same-distillery W-row exists, its age/abv/name are usually NULL, so only the "distillery_id only" weak signal remains.

## P128 D3 applicability note
- Of the **726** P127.5 MERGE `uuid` rows, **443** appear in this crosswalk (weak matches), **0** at exact/strong.
- Therefore: **Exact+Strong = 0** of 726 MERGE vectors can be bridged to `consensus_nodes` with confidence ≥0.7 today.
- B2 is **NOT closed** by this crosswalk. The weak-only matches (conf 0.50–0.60) are insufficient to satisfy P128 §5's "derive via consensus_nodes" with deterministic confidence; promoting them would require a human review queue for 475 rows (443 overlapping MERGE) or an alternative key (the missing W-set SMWS linkage).

## Matcher transparency
- Fuzzy algorithm: `difflib.SequenceMatcher.ratio` on **lower-cased, punctuation-stripped, stopword-removed** names — identical preprocessing and algorithm to P127.5 (`resolver_manifest.md`), preserving consistency.
- Confidence formula:
  - exact: 1.0 (distillery_id + age equal + abv within ±0.1)
  - strong-A: 0.80 (distillery_id + age equal + abv within ±1.0)
  - strong-B: 0.70 + min(0.15, (fuzzy−0.85)) (distillery_id + name_fuzzy ≥0.85)
  - weak: 0.60 baseline (distillery_id only), or 0.50 + (fuzzy−0.50)×0.4 for partial name fuzzy 0.50–0.85
- No collision occurred (no uuid had ≥2 candidates ≥0.7), so `crosswalk_collisions.csv` is a valid empty-frame file (header only).

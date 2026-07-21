# P95B-FIX-03 — Production Diff Report

**Mode:** READ-ONLY. Compares in-memory promotion candidates against current `flavor_profiles.flavor_profile`.
No production write occurred (production.db SHA `8350fe9d…` unchanged).

---

## Method
For each candidate from `canonical_profile_samples.json`, the current production `flavor_profile`
(row keyed by `whisky_id`) was normalized through the same `db_read_service._normalize_flavor_profile`
and compared axis-by-axis.

## Key structural finding: scale mismatch
Current `flavor_profiles.flavor_profile` stores axes on a **0-1 scale**
(e.g. `maritime: 0.5`, `smoky: 0.25`). The canonical candidate is **0-100**
(e.g. `maritime: 35.0`, `smoky: 44.0`). Every diff below reflects BOTH the axis-content
change AND this 0-1 → 0-100 scale normalization that promotion must apply
(see optional block in `p95b_fix02/migration.sql`).

## Per-candidate diff (candidate = 0-100 canonical; current = 0-1 stored)

### BUNNAHABHAIN (W002573) — HAS CURRENT
| axis | current(0-1) | candidate(0-100) |
|---|---|---|
| smoky | 0.25 | 44.0 |
| peaty | 0.0 | 55.0 |
| fruity | 0.0 | 50.0 |
| sweet | 0.25 | 50.0 |
| spicy | 0.0 | 35.0 |
| **maritime** | **0.5** | **35.0** ✅ (now full canonical value) |
| sherry | 0.25 | 44.0 |
- Projection keys in current (`smoky_peaty`,`oak_cask`,`malty_cereal`,`floral_herbal`) are
  correctly absent from the canonical candidate (they are client projections, not canonical axes).

### Loch Lomond (W002442) — HAS CURRENT
maritime 0.0 → **35.0** ✅; smoky 0.5→44.0; peaty 0.0→35.0; fruity 0.5→82.0; sweet 0.5→70.0; spicy 0.25→70.0; sherry 0.0→62.0.

### ardbeg (W001980) — HAS CURRENT
maritime 0.0 → **35.0** ✅; smoky 0.25→50.0; peaty 0.375→55.0; fruity 0.125→50.0; sweet 0.375→35.0; spicy 0.25→35.0; sherry 0.0→35.0.

### Glen Scotia (W000014) — HAS CURRENT
maritime 1.8 → **68.0** ✅ (largest maritime lift); smoky 0.09→50.0; peaty (none)→55.0; fruity 0.45→72.0; sweet 1.07→68.0; spicy 0.6→59.0; sherry 0.6→44.0.

### Benriach (W002288) — HAS CURRENT
maritime 0.25 → **35.0** ✅; smoky 0.375→62.0; peaty 0.125→35.0; fruity 0.375→50.0; sweet 0.625→65.0; spicy 0.125→44.0; sherry 0.0→44.0.

### Tasting-note text samples (note_text_1..3) — **NO CURRENT PROFILE**
New candidates (whisky_id NULL in staging — see F2 in promotion_rehearsal.md). Must be bound
to a `whisky_id` (P203B crosswalk) before promotion. Highest maritime: note_text_1 = 100
(real "seaweed / Salty, seaweedy" note).

## Aggregate
- 5/8 candidates overlap an existing `flavor_profiles` row → all 5 gain a properly-scaled canonical
  `maritime` value (previously 0.0–1.8 in 0-1 scale, now 35–68 in 0-100).
- 3/8 are new candidates (tasting-note text, currently unbound to whisky_id).
- **No candidate introduces a non-canonical axis** (no `rich`, no `oak`/`winey`/`waxy`/etc.).
- Every candidate carries all 7 canonical axes.

## Promotion-readiness implications
1. **Scale normalization is REQUIRED** at promotion: current stored values are 0-1; canonical
   contract + candidates are 0-100. Apply the optional ×100 block in `migration.sql` (and/or
   normalize in the promotion writer) so promoted rows are internally consistent.
2. **whisky_id binding** for tasting-note candidates must happen before promotion (F2).
3. After these two steps + the `vector_maritime` schema add (P95B-FIX-02, gated), the
   promotion content is GO.

**No production data was modified.** This is a diff-only report.

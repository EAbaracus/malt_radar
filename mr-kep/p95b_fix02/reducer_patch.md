# P95B-FIX-02 — Reducer Patch

**Scope:** make the canonical reducer the only reducer that participates in promotion, and ensure
it emits the full frozen 7-axis contract including `maritime`.

---

## 1. Problem (from P95B-FIX-01)
Two stale stubs in `mr-kep/d4_reducer/` used a non-canonical vocabulary and omitted `maritime`:

- `flavor_mapper.py` → mapped descriptors to `Smoke / Medicinal / Fruity / Sweetness / Spicy /
  Floral / Woody`.
- `axis_reducer.py` → initialized `vectors` with the same wrong keys and no `maritime`.

Yet the committed `canonical_vectors.json` (7384 items) uses the correct canonical keys
(`smoky, peaty, fruity, sweet, spicy, maritime, sherry`). The stubs were dead/contamination-risk
code that, if wired into promotion, would inject non-canonical axes and drop `maritime`.

## 2. Patch applied

### `flavor_mapper.py` (staging → production promotion mapper)
- Replaced the mapping dict with canonical 7-axis descriptors.
- Added `maritime` descriptors: `salt, brine, seaweed, coastal, sea, sea spray, marine, salty, ocean`.
- Added `CANONICAL_AXES` attribute = the frozen 7 (incl `maritime`) for parity assertions.

### `axis_reducer.py` (canonical reducer)
- `CANONICAL_AXES` now = `["smoky","peaty","fruity","sweet","spicy","maritime","sherry"]`.
- `reduce_entity_flavor` initializes `vectors` from `self.CANONICAL_AXES` (all 7, incl `maritime`).
- Reduction still maps via `FlavorMapper.get_axis` (now canonical) → output keys are canonical.
- Intensity 1-5 → ×20 → 0-100 (unchanged behavior, now on canonical keys).

### `ambiguity_handler.py`
- **No change.** `rich` correctly remains in `unmappable` → preserved as legacy evidence, never
  promoted as canonical (per CANONICAL_SCHEMA.md §5).

## 3. Integration guarantee
`d4_orchestrator.D4Orchestrator` wires `FlavorMapper` + `AxisReducer` + `AmbiguityHandler`. With
both mappers now canonical, the orchestrator's `canonical_vectors` output matches the frozen 7-axis
contract (incl `maritime`) and is consistent with the committed `canonical_vectors.json`.

## 4. Verification
- `test_canonical_axes.py::test_flavor_mapper_maritime_descriptors` — maritime descriptors map correctly.
- `test_axis_reducer_emits_canonical_seven_incl_maritime` — output keys == canonical 7, maritime populated.
- `test_axis_reducer_no_legacy_vocabulary` — no `Smoke/Medicinal/Woody/Floral` keys.
- All 7 tests pass (`pytest mr-kep/p95b_fix02/test_canonical_axes.py -q` → 7 passed).

## 5. Deprecation note
The old vocabulary is fully removed (not merely flagged) because it was never valid against the
canonical contract and would only cause contamination. If any external caller depended on the old
`Smoke/Medicinal/...` keys, it must be updated to the canonical 7 — that is the intended
conformance, not a breaking change we preserve.

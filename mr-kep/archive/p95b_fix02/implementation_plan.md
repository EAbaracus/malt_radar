# P95B-FIX-02 — Implementation Plan

**Objective:** Implement the Phase 12 blocking fixes from P95B-FIX-01.
**Date:** 2026-07-17
**Constraints honored:** implemented only the approved fixes; no unrelated flavor logic touched;
backward compatible (vector_rich retained; read service still read-only); regression run before
any production promotion.

---

## Approved fixes (mapped to P95B-FIX-01 findings)

| # | Fix | File(s) | Status |
|---|---|---|---|
| 1 | Add `vector_maritime` to `flavor_evidence` | `migration.sql` (staged) | WRITTEN, **NOT EXECUTED** (gated) |
| 2 | Preserve `vector_rich` as deprecated legacy | no schema drop; documented | ✅ retained |
| 3 | Staging promotion writes maritime | `d4_reducer/flavor_mapper.py` | ✅ rewritten canonical |
| 4 | `APP_AXES` exposes maritime | `backend/app/services/db_read_service.py` | ✅ edited |
| 5 | Remove maritime loss from read service | `db_read_service.py._normalize_flavor_profile` | ✅ edited |
| 6 | Only canonical reducer participates | `d4_reducer/axis_reducer.py` + `flavor_mapper.py` | ✅ both canonical |
| 7 | Regression tests, 7 canonical axes | `p95b_fix02/test_canonical_axes.py` | ✅ 7 passed |

---

## Changes made (code)

### A. `backend/app/services/db_read_service.py`
- `APP_AXES` now includes `"maritime"` (8th client axis). Maritime is a canonical axis and must
  be exposed, not dropped.
- `_normalize_flavor_profile` `mapped` dict now includes `"maritime": g("maritime")`, so a stored
  maritime value (present in 1942/3467 `flavor_profile` rows) survives to the client.
- Read-only contract preserved (mode=ro; no stored-value mutation).

### B. `mr-kep/d4_reducer/flavor_mapper.py` (staging → production promotion mapper)
- Rewritten vocabulary to the canonical frozen 7 axes (`smoky, peaty, fruity, sweet, spicy,
  maritime, sherry`). Previously used wrong vocab (`Smoke/Medicinal/Fruity/Sweetness/Spicy/Floral/Woody`).
- **Added `maritime` descriptors** (salt, brine, seaweed, coastal, sea spray, marine, salty, ocean)
  — previously absent, causing maritime loss at the mapper.
- Exposes `CANONICAL_AXES` for parity checks.

### C. `mr-kep/d4_reducer/axis_reducer.py` (canonical reducer)
- Initial `vectors` dict now uses canonical axis keys (incl `maritime`). Previously emitted
  `Smoke/Medicinal/Fruity/Sweetness/Spicy/Floral/Woody` and omitted `maritime`.
- Now emits exactly the canonical 7, so the d4 orchestrator chain produces canonical output
  consistent with `canonical_vectors.json`.

### D. `mr-kep/d4_reducer/ambiguity_handler.py`
- **Unchanged** (correct): `rich` remains unmappable → preserved as legacy evidence, never canonical.

---

## Gated step (NOT done in this task — requires human GO)
`migration.sql` adds `vector_maritime` to production `flavor_evidence`. This is a production
mutation and is **staged only**. Execution requires, per `promotion_rulebook.md §6`:
1. Explicit human GO for Phase 12.
2. Backup `production.db` + sha256.
3. Single transaction, rollback-on-error, `promotion_audit_log` row, row-count assert.

Until then, `vector_maritime` does NOT exist in production (verified: column absent), and
production.db SHA `8350fe9d…` is unchanged.

---

## Verification performed (this task)
- `pytest mr-kep/p95b_fix02/test_canonical_axes.py` → **7 passed**.
- production.db / knowledge.db SHA unchanged.
- `vector_maritime` confirmed absent in production (migration not executed).

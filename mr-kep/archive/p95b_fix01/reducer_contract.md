# P95B-FIX-01 — Reducer Contract Validation

**Mode:** READ-ONLY. Traces how evidence vectors flow into the final canonical flavor vector.

---

## 1. Two reducers exist — only one is canonical

| Reducer | File | Axis vocabulary | Canonical? |
|---|---|---|---|
| **REAL** pipeline reducer | `d4_reducer/` → `canonical_vectors.json` (7384 items) | `smoky, peaty, fruity, sweet, spicy, maritime, sherry` | ✅ matches frozen 7 |
| **LEGACY STUB** | `d4_reducer/axis_reducer.py` | `Smoke, Medicinal, Fruity, Sweetness, Spicy, Floral, Woody` | ❌ wrong vocabulary, no maritime |

`axis_reducer.py` is a **simulation stub** (docstring: "Mathematical reduction simulation").
It emits 7 axes that do NOT match the canonical contract (e.g. `Medicinal`≠`peaty`,
`Floral`/`Woody` are not canonical, `maritime` absent). **It must not be used for any promotion.**
The real reducer (`canonical_vectors.json`) is canonical-correct and includes `maritime`.

## 2. Evidence → canonical flow (verified)

```
source text
  └─ d4 reducer / editorial extractor  (lexicon: maritime = salt/brine/seaweed/coastal…)
       └─ canonical_vectors.json  →  {smoky, peaty, fruity, sweet, spicy, MARITIME, sherry} @0-100
            ├─ flavor_profiles.flavor_vector  (raw term-bag, incl. "salty"/"maritime" tokens)
            └─ flavor_profiles.flavor_profile (7-axis JSON; 1942/3467 rows carry maritime)
                  └─ db_read_service._normalize_flavor_profile
                       └─ APP_AXES projection → Flutter radar
```

## 3. No canonical axis lost? — PARTIAL FAIL

- **At reducer:** ✅ the real reducer preserves all 7 canonical axes including `maritime`.
- **At flavor_evidence storage:** ❌ `vector_maritime` column is absent → if evidence is persisted
  to `flavor_evidence` scalars, `maritime` has no target and is dropped.
- **At client (db_read_service):** ❌ `APP_AXES` = `[fruity, sweet, spicy, smoky_peaty,
  oak_cask, malty_cereal, floral_herbal]` — `maritime` is **explicitly dropped** (line 79:
  *"maritime is dropped as it is not an app axis"*). So even stored maritime never reaches the UI.

## 4. No legacy axis contaminates canonical output? — ✅ (mostly)

- `vector_rich` is never emitted by the canonical extractor (verified: `extract().record['flavor_vector']`
  keys = the 7 canonical axes, no `rich`). It exists only as legacy evidence in `flavor_evidence`.
- The legacy `axis_reducer.py` WOULD contaminate (emits `Floral`/`Woody`/`Medicinal`), but it is a
  stub not wired into promotion. **Risk:** if any future task accidentally imports `axis_reducer`,
  it would inject non-canonical axes. Recommendation: mark it deprecated / remove before Phase 12.

## 5. Verdict
- Real reducer contract: **VALID** (maritime preserved).
- Evidence-storage + client-projection: **FAIL** on maritime preservation.
- Legacy stub: **contamination risk** — must be excluded from the promotion path.

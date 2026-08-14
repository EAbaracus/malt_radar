# P95B-FIX-01 — Canonical Authority Audit

**Mode:** READ-ONLY. No DB/code writes, no migrations executed, no commit/push/tag.
**Date:** 2026-07-17
**Scope:** canonical flavor contract vs evidence schema vs reducer vs client layer.

---

## 1. Authoritative canonical contract (verified)

The single source of truth is **`mr-kep/output/p95b/canonical_flavor_standard.md`** (P95-B Phase 2),
corroborated by `mr-kep/CANONICAL_SCHEMA.md §5` and `mr-kep/output/p95b/promotion_rulebook.md`.

- **Frozen 7 axes (immutable):** `smoky, peaty, fruity, sweet, spicy, maritime, sherry`
- **Scale:** 0–100 (inputs in 0–1 are ×100).
- **Storage:** `flavor_profiles.flavor_vector` as a JSON dict `{axis: number}` (per the standard).
  > NOTE (imprecision found): the live `flavor_profiles` table actually stores the canonical
  > 7-axis JSON in column **`flavor_profile`**, while **`flavor_vector`** holds the *raw term-bag*
  > (e.g. `{"smokey":2.0,"malty":1.0,...}`). See §2. The doc naming is stale; the *intent*
  > (canonical 7-axis JSON) is unambiguous and matches `flavor_profile`.

The contract is explicit: *"The 7-axis contract is frozen; adding an axis is a schema decision,
not a pipeline decision."* → `maritime` is already canonical; `rich` is explicitly **NOT**
canonical (*"`rich` (SMWS) maps to sweet-side; it is NOT the `maritime` axis"*).

---

## 2. Layer-by-layer comparison (mismatches)

| Layer | Representation | Match to canonical 7? | Mismatch |
|---|---|---|---|
| **Canonical doc** | smoky, peaty, fruity, sweet, spicy, maritime, sherry @0-100 | ✅ authority | — |
| **flavor_evidence** (production) | scalar `vector_smoky…vector_sweet` + `vector_rich` | ❌ | **`vector_maritime` MISSING**; `vector_rich` surplus (non-canonical) |
| **flavor_profiles.flavor_profile** (app JSON) | fruity, sweet, spicy, **smoky_peaty, oak_cask, malty_cereal, floral_herbal** | ❌ | projection axes, NOT canonical names; `maritime` absent from keyset |
| **flavor_profiles.flavor_vector** (raw term-bag) | free-term bag (`smokey, malty, rich, salty…`) | n/a | raw evidence, not canonical (expected) |
| **d4 reducer (REAL)** — `canonical_vectors.json` | smoky, peaty, fruity, sweet, spicy, **maritime**, sherry @0-100 | ✅ | correct |
| **d4 reducer (LEGACY STUB)** — `axis_reducer.py` | Smoke, Medicinal, Fruity, Sweetness, Spicy, **Floral, Woody** | ❌ | 7 DIFFERENT axes; no maritime; wrong names |
| **client read layer** — `db_read_service.APP_AXES` | fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal | ❌ | projection; **drops maritime** (line 79) |
| **P96 book pipeline** | smoky, peaty, fruity, sweet, spicy, **maritime**, sherry | ✅ | correct (descriptor coverage incl. maritime:484) |

### Mismatches identified
1. **`flavor_evidence` lacks `vector_maritime`** while canonical + reducer + P96 all produce `maritime`.
   → maritime evidence is silently dropped if promoted to the scalar evidence schema.
2. **`flavor_evidence.vector_rich`** is non-canonical surplus (legacy/unmappable; see §evidence).
3. **Legacy `d4_reducer/axis_reducer.py`** uses a wrong 7-axis vocabulary and must NOT be used for
   promotion (it is a stub; the real reducer emits canonical vectors).
4. **`db_read_service` drops `maritime`** and emits a *projection* vocabulary
   (`smoky_peaty`, `oak_cask`, `malty_cereal`, `floral_herbal`) — presentation-only, but the
   maritime drop is a real client-compat gap.
5. **Doc imprecision:** canonical standard says storage column is `flavor_vector`; live canonical
   7-axis JSON is in `flavor_profile`. Intent is clear; doc should be corrected.

---

## 3. Evidence integrity (verified live)

| Check | Result |
|---|---|
| flavor_evidence rows / whiskies | 791 / 791 |
| flavor_profiles rows / whiskies | 3467 / 2999 |
| evidence rows with matching profile (FK link) | 791 (full overlap) |
| flavor_profiles with `maritime` in raw `flavor_vector` | 1754 / 3467 |
| flavor_profiles with `maritime` in app `flavor_profile` JSON | 1942 / 3467 (but stripped by read service) |
| any code WRITING `vector_maritime` | none (only READ-ONLY P95B docs reference it) |

**Conclusion:** maritime signal *exists* in evidence (1754 raw term-bag rows + 1942 app-profile rows)
but is **not preserved end-to-end**: it is absent from `flavor_evidence` scalar columns and is
**stripped by `db_read_service`** before the client sees it.

---

## 4. Authoritative decision

**`mr-kep/output/p95b/canonical_flavor_standard.md` is the single source of truth.**
The canonical frozen 7-axis set is `smoky, peaty, fruity, sweet, spicy, maritime, sherry` @ 0-100.
All other representations (flavor_evidence scalars, db_read_service projections, legacy axis_reducer)
are either (a) evidence/staging storage, (b) presentation projections, or (c) stale stubs — and must
conform to this contract, never the reverse.

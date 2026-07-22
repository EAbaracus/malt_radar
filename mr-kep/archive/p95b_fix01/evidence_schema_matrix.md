# P95B-FIX-01 — Evidence Schema Matrix & Classification

**Mode:** READ-ONLY. Classification derived from verified live schema + source code.

---

## 1. Why `vector_rich` exists (verified)

`mr-kep/d4_reducer/ambiguity_handler.py:7` lists:
```python
unmappable = ["rich", "complex", "smooth", "balanced", "intense"]
```
`rich` is a **known-unmappable descriptor** — it does not resolve to any of the 7 canonical axes.
When the d4 reducer encounters `rich` in source text it cannot place it on a canonical axis, so the
value is captured as `vector_rich` in `flavor_evidence` as **raw evidence** rather than silently
discarded. It is a faithful "we saw this but can't canonicalize it" signal.

Corroborated by `CANONICAL_SCHEMA.md §5`: *"`rich` (SMWS) maps to sweet-side; it is NOT the maritime
axis."* → `rich` has a partial (sweet-side) intuition but is **not** a canonical axis and must never
be promoted as one.

## 2. Should `vector_maritime` exist? (verified)

**YES.** Evidence that `maritime` is a legitimate, produced canonical axis:
- Canonical standard: frozen 7th axis `maritime`.
- `d4_reducer` real output `canonical_vectors.json` (7384 items) includes `maritime` (e.g. `{"sweet":85,"sherry":50,"smoky":12,"fruity":100,"spicy":57,"peaty":18,"maritime":32}`).
- P96 book pipeline descriptor coverage includes `maritime: 484`.
- Editorial extractor lexicon (`editorial_knowledge_extractor.py`) defines `maritime` =
  salt, brine, seaweed, coastal, sea spray, marine, and emits it in `flavor_vector`.
- 1754/3467 `flavor_profiles` raw `flavor_vector` rows contain `maritime`; 1942/3467 app
  `flavor_profile` rows contain `maritime`.

`flavor_evidence` is the ONLY canonical layer missing `vector_maritime`. Its absence means maritime
evidence cannot be persisted there → silent drop at the evidence-storage boundary.

## 3. Classification of every evidence vector (verified)

| Vector | Layer | Class | Rationale |
|---|---|---|---|
| vector_smoky | flavor_evidence | **canonical** | in frozen 7 |
| vector_peaty | flavor_evidence | **canonical** | in frozen 7 |
| vector_fruity | flavor_evidence | **canonical** | in frozen 7 |
| vector_sweet | flavor_evidence | **canonical** | in frozen 7 |
| vector_spicy | flavor_evidence | **canonical** | in frozen 7 |
| vector_sherry | flavor_evidence | **canonical** | in frozen 7 |
| **vector_maritime** | flavor_evidence | **MISSING (should be canonical)** | produced everywhere else; absent here → gap |
| vector_rich | flavor_evidence | **legacy / evidence-only / unmappable** | `ambiguity_handler` unmappable list; not canonical; never produced by canonical extractor |
| flavor_vector (term-bag) | flavor_profiles | **evidence-only (raw)** | free-term bag; not canonical; expected as provenance |
| flavor_profile (7-axis projection) | flavor_profiles | **canonical-target / presentation** | canonical 7-axis JSON but with projection keyset (smoky_peaty etc.) |

## 4. Disposition
- **Canonical (keep):** smoky, peaty, fruity, sweet, spicy, sherry + **add maritime**.
- **Legacy (keep, deprecate, NEVER promote as canonical):** vector_rich — retains "unmappable"
  evidence signal; do not map to maritime or any canonical axis.
- **Missing (add):** vector_maritime — required for evidence-storage parity with the canonical contract.

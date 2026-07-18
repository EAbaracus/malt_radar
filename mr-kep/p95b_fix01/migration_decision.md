# P95B-FIX-01 — Migration Impact Analysis & Decision

**Mode:** READ-ONLY. **No migration executed.** Dry-run SQL only.

---

## 1. Is `vector_maritime` required? → YES

Verified: `maritime` is a frozen canonical axis, produced by the real reducer, P96, and the editorial
extractor, and present in 1754 raw / 1942 app `flavor_profiles` rows. `flavor_evidence` is the only
canonical layer missing it → maritime evidence is silently dropped at the evidence-storage boundary.
**Required to close the gap.**

## 2. Should `vector_rich` remain? → YES (as legacy, never canonical)

`rich` is in `ambiguity_handler.unmappable` (cannot map to a canonical axis) and is explicitly
non-canonical per `CANONICAL_SCHEMA.md §5`. It is valuable **evidence** ("we observed this descriptor
but could not canonicalize it") and is present in all 791 `flavor_evidence` rows. Dropping it would
lose provenance. **Keep it; mark deprecated; never promote as canonical; never derive `maritime` from it.**

## 3. Should the canonical contract change? → NO

The 7-axis frozen contract (`smoky, peaty, fruity, sweet, spicy, maritime, sherry` @0-100) is correct
and well-supported. The defects are in *storage schema* and *client projection*, not the contract.
Changing the contract (e.g. removing maritime, or adding rich) would be wrong. The contract wins;
layers conform to it.

## 4. RECOMMENDED SINGLE ARCHITECTURE

**Canonical axis set (frozen, authoritative):** `smoky, peaty, fruity, sweet, spicy, maritime, sherry` @ 0-100.

**Layer conformance:**

1. **`flavor_profiles.flavor_profile`** = canonical 7-axis JSON (already the de-facto source of truth
   for the app). Keep `flavor_profiles.flavor_vector` as the **raw term-bag** (evidence provenance,
   never canonical). → *Doc fix:* canonical standard should reference `flavor_profile`, not `flavor_vector`.

2. **`flavor_evidence`** = add **`vector_maritime REAL`** to achieve parity with the canonical 7.
   Keep `vector_rich` (legacy/evidence-only, deprecated). Do **NOT** add any other axis.
   *(Minimal-change option — recommended. Avoids a risky column-type redesign.)*

3. **Reducer:** use ONLY the real `d4_reducer` pipeline (emits canonical 7 incl `maritime`).
   **Deprecate / remove `d4_reducer/axis_reducer.py`** (wrong vocabulary; contamination risk).

4. **Client (`db_read_service`):** keep the presentation projection, BUT **add `maritime` to
   `APP_AXES`** (or map it explicitly) so the canonical 7th axis is not dropped before the UI.
   The `smoky_peaty`/`oak_cask`/`malty_cereal`/`floral_herbal` projection is acceptable as a
   presentation vocabulary — it must remain read-only and must not mutate stored values.

**Why this architecture (not a full flavor_evidence redesign):** the divergence is narrow
(one missing column + one surplus + a client drop). A full migration of `flavor_evidence` to a
JSON-vector column (Option B) would align storage shapes but carries high risk and is unnecessary to
satisfy the contract. Minimal, targeted changes close every identified gap.

---

## 5. Dry-run migration (NOT executed)

See `dry_run_migration.sql`. Contains:
- `ALTER TABLE flavor_evidence ADD COLUMN vector_maritime REAL;` (closes the canonical gap).
- Explicit note: **no backfill possible** — `maritime` was never stored; `vector_rich` is semantically
  distinct (sweet-side, not maritime) and MUST NOT be used to derive it.
- Optional, commented ×100 scale-normalization (canonical is 0-100; current evidence is 0-1) — left
  commented as a separate, higher-risk review item.
- `vector_rich` retained (deprecated, not dropped).
- Rollback + verification queries.

**Nothing executed. production.db SHA unchanged (`8350fe9d…`).**

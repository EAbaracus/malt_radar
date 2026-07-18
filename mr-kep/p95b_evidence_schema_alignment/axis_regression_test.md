# P95B Phase 9.9 — Axis Regression Test

**Purpose:** Define the acceptance tests that must pass after the (future, authorized) schema
alignment fix. These are SPECIFICATIONS only — no test was executed, no migration applied.
They guard against reintroducing the `maritime` gap or the `rich` confusion.

**Contract under test:** CANONICAL_SCHEMA.md:52-54 + `editorial.CANONICAL_AXES`
= `smoky, peaty, fruity, sweet, spicy, maritime, sherry` @ **0-100** scale.

---

## R1 — Schema axis parity (structural)

**Given** `flavor_evidence` after applying the dry-run migration.
**Then** the set of `vector_*` scalar columns MUST equal the canonical 7 axes:
```
vector_smoky, vector_peaty, vector_fruity, vector_sweet, vector_spicy,
vector_maritime, vector_sherry
```
**Assertions:**
- `vector_maritime` column EXISTS (closes GAP 1).
- No `vector_rich` column is *required* by the canonical contract
  (rich retained as deprecated/legacy, must not block the test).
- Column count of canonical axes in `flavor_evidence` == 7.

**Verification query (read-only):**
```sql
SELECT name FROM pragma_table_info('flavor_evidence')
WHERE name LIKE 'vector_%' AND name <> 'vector_rich';
-- expect exactly: smoky, peaty, fruity, sweet, spicy, maritime, sherry
```

---

## R2 — Extractor → storage axis preservation (no silent drop)

**Given** a parsed article whose text yields a non-zero `maritime` signal
(e.g. contains "sea salt", "brine", "coastal").
**When** `editorial_knowledge_extractor.extract()` runs,
**Then** `record['flavor_vector']['maritime']` is computed AND, after promotion,
survives into `flavor_evidence.vector_maritime` (not dropped).

**Regression guard:** a promotion mapping that iterates `CANONICAL_AXES` and writes
`vector_<axis>` MUST include `maritime`. A unit test must assert that every key in
`CANONICAL_AXES` has a corresponding `vector_<axis>` target column; failing this is a
hard error (this is exactly the bug that let `maritime` go missing).

---

## R3 — `rich` is NOT maritime (semantic guard)

**Given** the contract statement "rich … is NOT the maritime axis; maps to sweet-side".
**Then:**
- `vector_rich` MUST NOT be used to backfill `vector_maritime`.
- A test asserting `vector_maritime IS NULL` for historical rows is valid (no fabricated data).
- Any "rich → maritime" derivation in code is a FAIL.

---

## R4 — Scale normalization (0-100)

**Given** CANONICAL_SCHEMA mandates `axis_scale='0-100'`.
**If** the optional scale migration (FIX 2) is applied,
**Then** post-migration `MIN(vector_smoky) >= 0 AND MAX(vector_smoky) <= 100`
(and same for all 7 axes). A value > 1.0 after migration indicates a double-multiply bug.
**If** the scale migration is NOT applied, document the 0-1 scale as an accepted deviation
and assert `MAX(...) <= 1.0` so a future accidental 0-1/0-100 mix is caught.

---

## R5 — Data integrity regression (no loss)

**Given** 791 rows pre-migration, all with non-null `whisky_id` and unique `evidence_id`.
**After** applying FIX 1 (add column only, no backfill):
- Row count unchanged: `COUNT(*) == 791`.
- `whisky_id` NULL count == 0.
- `evidence_id` duplicate count == 0.
- Existing 7 columns' values UNCHANGED (compare SUM/checksum before vs after).

---

## R6 — Promotion contract test (end-to-end, staging → production)

**Given** a staging record with `flavor_vector_json` containing all 7 canonical axes
including `maritime`.
**When** the (corrected) promotion routine writes to `flavor_evidence`,
**Then** `vector_maritime` equals the staging `maritime` value (within scale convention),
and no canonical axis is silently omitted.

---

## Manual sign-off checklist (for the authorized migration owner)
- [ ] `vector_maritime` added (FIX 1)
- [ ] Pre-migration backup taken (`production.db.pre_p95b_*.bak`)
- [ ] `vector_rich` retained (deprecation noted, not dropped)
- [ ] Scale decision recorded (apply FIX 2 or document 0-1 deviation)
- [ ] R1–R6 executed and green
- [ ] production.db SHA re-verified post-migration

> This document is a test SPECIFICATION. No SQL/test was executed as part of P95B Phase 9.9
> (READ-ONLY task). Execute only under an authorized migration with a backup.

# P95B Phase 9.9 — Evidence Schema Alignment

**Mode:** READ-ONLY. No production migration. No data write. Dry-run SQL only.
**Date:** 2026-07-17
**Scope:** `production.db.flavor_evidence` vs canonical 7-axis flavor contract.

---

## 1. `flavor_evidence` — actual vector columns (verified)

Source: `PRAGMA table_info(flavor_evidence)` on `output/import/production.db` (read-only).

| Column | Type | notnull | non-null rows / 791 | value range | avg |
|---|---|---|---|---|---|
| vector_smoky | REAL | 0 | 791/791 | 0.0–1.0 | 0.215 |
| vector_peaty | REAL | 0 | 791/791 | 0.0–1.0 | 0.079 |
| vector_sherry | REAL | 0 | 791/791 | 0.0–1.0 | 0.053 |
| vector_fruity | REAL | 0 | 791/791 | 0.0–1.0 | 0.385 |
| vector_spicy | REAL | 0 | 791/791 | 0.0–1.0 | 0.265 |
| vector_sweet | REAL | 0 | 791/791 | 0.0–1.0 | 0.584 |
| vector_rich | REAL | 0 | 791/791 | 0.0–1.0 | 0.291 |

Stored as **7 scalar columns** (not a JSON vector), on a **0–1** scale.

---

## 2. Canonical 7-axis contract (verified)

Authoritative definition — `mr-kep/CANONICAL_SCHEMA.md` lines 52-54:

> `smoky, peaty, fruity, sweet, spicy, maritime, sherry` — stored normalized to
> `axis_scale='0-100'`. Inputs in 0–1 are ×100. `rich` (SMWS) maps to sweet-side; it is
> NOT the `maritime` axis.

Corroborated by the live pipeline constant `editorial.adapters.editorial_adapter_factory.CANONICAL_AXES`
= `['smoky', 'peaty', 'fruity', 'sweet', 'spicy', 'maritime', 'sherry']`.

`maritime` is also a real column in sibling tables: `staging_book_flavor_profiles.maritime`,
`staging_notebooklm_flavor_profiles.maritime` — confirming `maritime` is the intended canonical axis.

---

## 3. Missing / surplus canonical evidence fields (report)

| Canonical axis | In `flavor_evidence`? | Status |
|---|---|---|
| smoky | vector_smoky | ✅ present |
| peaty | vector_peaty | ✅ present |
| fruity | vector_fruity | ✅ present |
| sweet | vector_sweet | ✅ present |
| spicy | vector_spicy | ✅ present |
| sherry | vector_sherry | ✅ present |
| **maritime** | — | ❌ **MISSING** (gap) |
| (rich) | vector_rich | ⚠️ **SURPLUS / non-canonical** |

**GAP 1 — `vector_maritime` missing.** The canonical 7th axis `maritime` has no storage column in
`flavor_evidence`. The editorial extractor *computes* `maritime` (lexicon: salt, brine, seaweed,
coastal, sea spray, marine) and emits it in `flavor_vector`, and the staging layer preserves it in
`flavor_vector_json` — but on promotion to `flavor_evidence` there is no target column, so maritime
evidence is **silently dropped**.

**GAP 2 — `vector_rich` is surplus / non-canonical.** `rich` is NOT in the canonical 7-axis contract
(CANONICAL_SCHEMA.md: "rich … is NOT the maritime axis"). The canonical extractor never produces a
`rich` key (verified: `extract().record['flavor_vector']` keys = the 7 canonical axes, no `rich`).
All 791 rows carry `vector_rich`, so it is **orphaned legacy data** that no current pipeline populates
or consumes.

**GAP 3 — scale mismatch (0–1 vs 0–100).** CANONICAL_SCHEMA mandates `axis_scale='0-100'`
(0–1 inputs ×100). `flavor_evidence.vector_*` are stored on a **0–1** scale (verified min/max 0.0–1.0).
This is a secondary alignment defect: any consumer expecting the 0–100 canonical scale will misread values.

---

## 4. Impact analysis — missing `vector_maritime`

- **Data loss on promotion.** Editorial/ingestion evidence carrying a maritime signal (e.g. coastal
  Islay, sea-salt, brine character) cannot be persisted to `flavor_evidence`. Maritime is a
  high-discrimination axis for coastal/maritime-heavy distilleries; its absence flattens the flavor
  differentiation of those whiskies in the canonical evidence store.
- **Extract→store contract break.** The extractor output (`flavor_vector` with `maritime`) and the
  storage schema (`flavor_evidence`) are out of sync. A promotion routine mapping
  `flavor_vector` → scalar columns has no key for `maritime`, so it is dropped silently (no error).
- **No backfill possible from existing data.** `maritime` was never stored, and per contract `rich`
  is semantically distinct (maps to sweet-side, not maritime), so `vector_rich` cannot be used to
  derive `vector_maritime`. Backfill would require re-running extraction over source text — out of
  scope for this READ-ONLY alignment task.
- **Mitigating factor.** Staging (`flavor_vector_json`) and the canonical extractor DO carry `maritime`,
  so the gap is contained to the promotion/storage boundary, not the ingestion boundary. Fixing the
  storage schema (add `vector_maritime`) closes the gap without data loss going forward.

---

## 5. Dry-run migration SQL (NOT executed — read-only task)

See `dry_run_migration.sql`. Contains:
- `ALTER TABLE flavor_evidence ADD COLUMN vector_maritime REAL;` — fills the canonical gap.
  (No backfill: existing rows will be NULL; maritime cannot be derived from `vector_rich`.)
- Optional, commented scale-normalization block (×100) to bring columns to the 0–100 canonical scale.
  Left commented because it is a higher-risk, separately-reviewable change and is not required to close
  the axis gap.
- Explicit note that `vector_rich` is retained (not dropped) to preserve existing 791-row data; it is
  flagged for deprecation, not deletion.

**Nothing in `dry_run_migration.sql` was executed.** No production mutation occurred.

---

## 6. Existing data integrity

| Check | Result |
|---|---|
| Row count `flavor_evidence` | 791 |
| `whisky_id` NULL | 0 |
| `evidence_id` (PK) duplicate | 0 |
| ≥1 vector populated per row | 791/791 |
| All 7 `vector_*` non-null | 791/791 |
| production.db SHA (untouched) | 8350fe9d… (unchanged this task) |

Existing data is **internally consistent** (no corruption, no nulls, no dupes). The defects are
**contract misalignments** (axis set + scale), not data-integrity failures.

---

## Deliverables
- `evidence_schema_alignment.md` (this file)
- `dry_run_migration.sql` (dry-run only, not executed)
- `axis_regression_test.md` (acceptance test spec for the fix)

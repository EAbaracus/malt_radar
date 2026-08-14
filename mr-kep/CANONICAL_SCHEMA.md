# CANONICAL_SCHEMA — knowledge.db contract

- doc_version: 1 (P137A, 2026-07-17)
- authoritative naming + relationship contract for all future book/NotebookLM/SMWS/community/web
  promotions into knowledge.db. Replaces any informal D2 recollection.
- Scope: knowledge.db ONLY. production.db is never written by this pipeline.

## 1. Canonical source column: `source_id` (NOT `source_key`)

P137 preflight found `citations` "lacks `source_key`". Verified against the live schema:

| table | source_id | source_key |
|---|---|---|
| sources | ✅ | ❌ |
| books | ✅ (FK→sources) | ❌ |
| citations | ✅ (FK→sources) | ❌ |

**Decision (D2-final): `source_id` is canonical.** `source_key` does NOT exist anywhere in
knowledge.db and was never part of the implemented schema. No migration is required — the
existing name is correct and functional (it is a FK to `sources.source_id`).

> If any future task spec says "source_key", read it as `source_id`. The P128/P135 D2 note
> that mentioned `source_key` was a misremembery; the implemented contract wins.

## 2. Provenance chain (mandatory on every row)

```
sources(source_id) ─1─< citations(source_id) ─1─< evidence(citation_id)
                                              └─< promotion_queue(citation_id)
                                              └─< merge_history(citation_id)
```
Every enrichment row MUST carry a `citation_id` resolving to an existing `citations` row,
which resolves to an existing `sources` row. `provenance` (JSON) stores the upstream
anchor (smws_code, book_id+page, notebooklm_run_id).

## 3. UUID PK + audit columns (every table)

`*_id TEXT` (UUID), `created_at TEXT` (ISO8601 UTC), `updated_at TEXT`,
`confidence REAL` (0–1), `source TEXT`, `provenance TEXT`. Enforced at DDL level
(migration/schema.sql is authoritative).

## 4. Idempotency keys (UNIQUE)

- `promotion_queue.dedupe_key` UNIQUE → `(entity_key, field_name, source_hash)`.
- `merge_history.dedupe_key` UNIQUE → same shape; re-apply = no-op.
- `canonical_tasting_notes.note_hash` UNIQUE → dedupe notes.
- `books.file_hash` indexed → dedupe book re-ingest.
- `citations.source_hash` indexed.

## 5. Canonical flavor axes (fixed 7)

`smoky, peaty, fruity, sweet, spicy, maritime, sherry`.

**Layered scale contract (ratified P95C, verdict C — intentional, NOT a contradiction):**

| Layer | Table | Required axis scale | Notes |
|---|---|---|---|
| 1 — storage/raw | `flavor_evidence` | **0.0–1.0** | raw evidence landing; MUST be 0–1 |
| 2 — derived/semantic | `canonical_flavor_vectors` | **0–100** | `axis_scale='0-100'`; bridge = `norm_axis_0_100()` (×100) |
| 3 — application/presentation | `flavor_profiles` | **0–100** | presentation layer; 0–100 |

Bridge: `norm_axis_0_100()` multiplies `flavor_evidence` (0–1) by 100 to produce
`canonical_flavor_vectors` (0–100). `flavor_profiles` is populated in parallel from the
same 0–100 source vector (it is NOT derived from `flavor_evidence`); the storage layer's
0–1 form is produced by the writer (`to_storage_scale()` ÷ 100 before insert).

**Writer contract (P95D):** any code writing `flavor_evidence` MUST emit axis values in
0.0–1.0. Source vectors that are 0–100 (e.g. `staging_book_flavor_profiles`,
`AxisReducer.canonical_vectors`) MUST be divided by 100 on the way into `flavor_evidence`.
The regression invariant `MAX(flavor_evidence.*) <= 1.0` is enforced as a hard gate
(R4) in `p95b_phase12_execute.py`.

`rich` (SMWS) maps to sweet-side; it is NOT the `maritime` axis. Consensus method
recorded in `consensus_method`.

## 6. Field class → promotion action (P128 field_merge_matrix)

| class | action | example |
|---|---|---|
| IMMUTABLE | REJECT | whisky_id, entity_key |
| APPEND | APPEND | cask_type, finish_type, tasting_note |
| REPLACEABLE | APPLY / REVIEW | region, country, nas, bottle_size |
| REVIEW | REVIEW → review_queue | age, abv, type, brand (medium-confidence) |

## 7. Relationship of the three counts (proven by SQL, P137A)

- **724** = `normalized_metadata WHERE source='smws'` = `staging_smws ∩ flavor_evidence`
  (797 ∩ 791 = 724). The SMWS whisky population with a production link.
- **726** = P127.5 MERGE candidates from the **book PDF corpus** (unrelated population;
  different filter). NOT a subset of 724.
- **2.664** = `promotion_queue` total = sum of non-null smws fields per whisky:
  age 724 + abv 707 + cask_type 627 + region 606 = 2.664 (avg 3.68 fields/whisky).
  2.664 ≠ 726. They answer different questions.

## 8. Change policy

- Additive/reversible DDL only (ADD COLUMN, CREATE INDEX, CREATE TABLE). NO DROP/RENAME.
- Every change via migration/migrate.py (records schema_version). Backup + hash guard
  before any knowledge.db mutation.
- production.db: read-only from this pipeline. Promotion P138 writes via the P121 gate.

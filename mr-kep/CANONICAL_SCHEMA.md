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

`smoky, peaty, fruity, sweet, spicy, maritime, sherry` — stored normalized to
`axis_scale='0-100'`. Inputs in 0–1 are ×100. `rich` (SMWS) maps to sweet-side; it is
NOT the `maritime` axis. Consensus method recorded in `consensus_method`.

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

# P203 — Canonical Crosswalk Schema (DESIGN ONLY — not implemented)

> This is a schema proposal. No table is created in this READ-ONLY phase.

## Target table: `distillery_crosswalk`
```sql
CREATE TABLE distillery_crosswalk (
  crosswalk_id   INTEGER PRIMARY KEY,          -- surrogate
  entity_id      TEXT    NOT NULL,             -- → production.distilleries.distillery_id (or new id)
  canonical_name TEXT    NOT NULL,             -- preferred display name (e.g. 'Macallan')
  external_name  TEXT    NOT NULL,             -- raw name as seen in source (e.g. 'The Macallan')
  source         TEXT    NOT NULL,             -- 'books/new.csv' | 'p119_6' | 'production' | …
  confidence     REAL    NOT NULL,             -- 0.0-1.0 match confidence
  match_method   TEXT,                         -- 'exact' | 'normalized' | 'fuzzy' | 'manual'
  created_at     TEXT,
  UNIQUE(entity_id, external_name, source)
);
```

## Recommended columns (per spec)
| column | purpose |
|---|---|
| canonical_distillery | display label of the resolved entity |
| aliases | all known string forms (denormalized list or 1 row per alias) |
| external_name | the raw source string that triggered the match |
| source | which dataset/CSV the external_name came from |
| confidence | match certainty (exact=1.0, normalized=0.9, fuzzy=0.6, manual=1.0) |
| entity_id | the stable production.distilleries.distillery_id (or generated new id) |

## Operational rules
1. `entity_id` points at production `distilleries` when a match exists; otherwise a NEW canonical entity is minted.
2. One `(entity_id, external_name, source)` tuple is unique — no duplicate aliases per source.
3. Crosswalk is **append-only / reviewed**, never auto-overwriting production dimension data.
4. Confidence < 0.7 rows require MANUAL_REVIEW before promotion (mirrors P200/P202 gating).

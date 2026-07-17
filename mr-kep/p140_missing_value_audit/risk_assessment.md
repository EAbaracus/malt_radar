# P140 — Risk Assessment (Phase 5)

- doc_version: P140-1
- question: could converting `''` → NULL affect queries / indexes / Flutter app / API /
  search / sorting / filters?

## Indexes
- `whiskies` has exactly **one index: `idx_whiskies_whisky_id`** (on the PK `whisky_id`).
- **No index exists on `region` or `age_statement`.** Therefore the conversion touches
  zero indexes → no index rebuild, no query-plan regression from indexing.

## Queries
- Code that tests `col = ''` would stop matching (those rows become NULL). Such tests are
  almost certainly bugs; correct code uses `col IS NULL`. **Risk: LOW**, provided the app
  uses NULL-checks (which it must, since 4 columns are already 100% NULL).
- `COUNT(col)` would change (NULL excluded, `''` counted) — counts would **drop** by the
  `''` count for those columns. Any dashboard counting "populated region" would show a
  small decrease. **Risk: MEDIUM** for reporting accuracy if not anticipated.

## Flutter app / API responses
- Dart/JSON: SQLite NULL serializes to `null`; `''` serializes to `""`. Clients that treat
  `null` and `""` equivalently (common) see **no behavioral change**. Clients that branch on
  `isEmpty` would see `null` instead of `""` — **Risk: LOW** if the app already handles
  NULL (it must, given 4 fully-NULL columns).
- `completed_fields` / `notes_for_review` are already NULL everywhere, so existing code
  paths for NULL are exercised daily.

## Search
- Full-text / LIKE search on `region`/`age_statement`: `''` never matches a real query term,
  so removing it changes **nothing** in search results. **Risk: NONE**.

## Sorting
- `ORDER BY region`: NULLs sort first/last (collating sequence dependent); `''` sorts before
  any non-empty string. Behavior shifts slightly for the 713 rows. **Risk: LOW** (cosmetic
  ordering of empty entries).

## Filters
- "region is set" filters using `region IS NOT NULL` would now correctly include the
  previously-`''` rows as "not set" — **this is the desired, consistent behavior**.
  Filters using `region != ''` would change semantics. **Risk: LOW-MEDIUM**; should audit
  any `!= ''` / `= ''` filter in app/API.

## Data-integrity / rollback
- Conversion is a single reversible `UPDATE` per column; a pre-conversion backup (as done in
  P139) makes rollback trivial. **Risk: LOW** with backup.

## Summary
| surface | risk |
|---|---|
| indexes | NONE (no index on affected cols) |
| queries (`col=''`) | LOW (correct code uses IS NULL) |
| counts/aggregates | MEDIUM (counts shift by `''` count) |
| Flutter/API null-vs-empty | LOW (app already handles NULL) |
| search | NONE |
| sorting | LOW (cosmetic) |
| filters (`!= ''`) | LOW-MEDIUM (audit filters) |
| rollback | LOW (backup + idempotent) |

**Overall: LOW-MEDIUM.** The conversion is safe provided (a) a backup is taken, (b) any
`col = ''` / `col != ''` query/filter in app+API is reviewed, and (c) count-based dashboards
are updated to expect NULL semantics.

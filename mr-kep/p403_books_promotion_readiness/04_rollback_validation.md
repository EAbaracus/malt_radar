# P404 — 04 Rollback Validation (LOSSLESS)

> **Correction applied:** the earlier DELETE-only rollback was lossy — it discarded original
> book-row values and the 2 extra rows for W000014/W002442. Rollback is now **lossless**: a
> pre-apply snapshot of every book row for the manifest IDs is retained, and rollback restores
> the EXACT original state (values **and** collapsed duplicates).

## Pre-apply snapshot (captured read-only, before any Apply)
- **Snapshot file:** `rollback_snapshot_book_rows.json`
- **Rows captured:** 8 (all `source='book'` rows whose whisky_id is in the manifest)
- **Whiskies with an existing book row:** 6 → ['W000014', 'W001980', 'W002288', 'W002442', 'W002565', 'W002573']
- **Duplicate-collapse cases (had >1 book row — would be LOST by DELETE-only):**
  - W000014: ['P95B_801d8867aa5e43f8bd4d', 'P95B_9707c4b49cfc40a48622']
  - W002442: ['P95B_f3675ccf2c924167bfa2', 'P95B_3f1fff7182774377b2c5']
- Each snapshot row stores its **original `evidence_id`** and full column values.

## Lossless rollback procedure
```
1) DELETE FROM flavor_evidence WHERE source='book' AND whisky_id IN (manifest_ids)
2) Re-INSERT every row from rollback_snapshot_book_rows.json
     with its ORIGINAL evidence_id and ORIGINAL column values
```
This restores the 8 original book rows (including both W000014 / W002442 duplicates) exactly.

## Restore command
```python
import sqlite3, json
c = sqlite3.connect(r'C:\Users/eltun\Documents/malt radar CLEAN\output\import\production.db')
man = json.load(open(r'C:\Users/eltun\Documents/malt radar CLEAN\mr-kep\p403_books_promotion_readiness\06_promotion_manifest.json'))
snap = json.load(open(r'C:\Users/eltun\Documents/malt radar CLEAN\mr-kep\p403_books_promotion_readiness\rollback_snapshot_book_rows.json'))
ids = man['eligible_whisky_ids']
c.execute("DELETE FROM flavor_evidence WHERE source='book' AND whisky_id IN (" + ",".join("?"*len(ids)) + ")", ids)
cols = snap['snapshot_columns']
for r in snap['rows']:
    c.execute("INSERT INTO flavor_evidence (" + ",".join(cols) + ") VALUES (" + ",".join("?"*len(cols)) + ")",
              [r[col] for col in cols])
c.commit()
```

## Verification (simulated apply → lossless rollback on a temp copy)
| Metric | Value |
|---|---|
| After-apply book rows | 64 |
| Restored book rows | 8 (== original snapshot 8) |
| Restored evidence_ids == original | True |
| **Lossless restore (exact state)** | **True** |

The simulation confirms rollback returns the DB to the **identical pre-apply book rows with identical original `evidence_id`s**.

## Idempotency
Apply → lossless rollback → re-apply reproduces the identical final state (64 book rows, 0 duplicates). Rollback is now provably lossless.

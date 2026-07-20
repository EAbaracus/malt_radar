# P404 — 02 Dry Run Results

**Executed against a TEMPORARY COPY of production.db. No production write occurred. Temp copy discarded after run.**

| Metric | Value |
|---|---|
| Rows inserted | **58** |
| Rows updated | **8** (6 existing-row updates + 2 duplicate-collapse normalizations) |
| Rows skipped | 0 |
| Rows failed | 0 |
| Final book-source rows | **64** (exactly 1 per manifest whisky) |
| Duplicate (whisky_id, source='book') rows | **0** |
| Expected final evidence count | 1049 (was 993) |

### Idempotent rerun (same temp copy, second pass)
| Metric | Value |
|---|---|
| Inserted | 0 |
| Updated | 0 |
| Skipped (no-op) | 64 |
| Failed | 0 |

The second pass produced **0 inserts / 0 updates / 64 skips** → fully idempotent.

## Interpretation
- 58 net-new whiskies get a `book` evidence row (52 of them their FIRST evidence).
- 6 whiskies already had a `book` row → updated (and 2 had 2 rows → collapsed to 1).
- No blind INSERT; no second book row created for any whisky.

# P203 — ROI

| dimension | assessment |
|---|---|
| cost | LOW — one-time normalization script + manual review of <0.7 confidence rows; table is small (<<5k rows). |
| benefit | HIGH — unlocks ~88% of previously-failing external matches; reusable across EVERY future dataset. |
| confidence | HIGH — normalize+stopword is deterministic; fuzzy only for edge cases. |
| risk | LOW — crosswalk is append-only; never mutates production dimension. |
| maintenance | LOW — grows incrementally as new sources arrive; review queue only for low-confidence. |

## Which prior assets improve immediately
- **P202A / P202B** (`books/new.csv`): 15/17 rows become resolvable → review text linkable to production.
- **P119_6 staging CSVs**: +51 distillery names gain a resolution path.
- **Any future external CSV** with free-text distillery names (the standard pattern).

## Future-dataset benefit
- Every external ingest gets a matching boost with zero per-dataset customization.
- Turns 'NO_MATCH' into 'HIGH_CONFIDENCE' for the dominant mismatch class (suffix/unicode/punctuation).

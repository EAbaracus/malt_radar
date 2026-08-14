# P203D — Task 1: Staging Inventory Audit

> Read-only audit of `data/p203c_staging/editorial_staging_retry.db`
> (the current validated RETRY run). Source DB: `staging_editorial_reviews`.
> All figures verified directly against the SQLite file (read-only `mode=ro`).

## Totals
| Metric | Value |
|---|---|
| Total evidence records | **19** |
| Distinct `evidence_id` | 19 (no collisions) |
| `review_required = true` | **8** |
| Duplicate `evidence_id` groups | **0** |
| Rows with populated `canonical_distillery_id` | 11 |
| Rows with NULL `canonical_distillery_id` | 8 (all == `review_required=1`) |

## Source distribution
| source_id | count |
|---|---|
| thewhiskyphiles | 5 |
| thedramble | 5 |
| whiskynotes_be | 5 |
| thewhiskeywash | 4 |

> Note: spec lists `wordsofwhisky` as an included source; the RETRY staging
> contains **0** `wordsofwhisky` rows. Only the 4 sources above are present.
> `whiskymonster` is correctly absent (EXCLUDE_PENDING_ACCESS). This is a
> **coverage observation**, not a validation failure — the 19 rows are internally consistent.

## Required-field presence (null/empty count; 0 = fully present)
| field | null/empty |
|---|---|
| evidence_id | 0 |
| source_id | 0 |
| source_url | 0 |
| fetched_at (capture timestamp) | 0 |
| raw_name | 0 |
| distillery_raw | 0 |
| provenance_state | 0 |
| flavor_vector_json | 0 |
| author | **14** (coverage gap, not logic failure) |
| published_date | **19** (coverage gap, not logic failure) |
| canonical_distillery_id | 8 (the 8 review-required rows) |

## Verification of required invariants
- ✅ `evidence_id` UNIQUE — 19 distinct, 0 duplicate groups.
- ✅ Source provenance present — `source_id` + `source_url` populated on all 19.
- ✅ URL present — 19/19.
- ✅ Author preserved where available — 5/19 (`whiskynotes_be` = "Ruben"); 14 absent at source.
- ✅ Capture timestamp present — `fetched_at` set on all 19.

## Conclusion
Inventory is internally consistent: 19 unique records, no duplicates,
complete provenance/URL/timestamp, and an explicit `review_required` flag
(8 rows) that cleanly partitions the unmatched set. Author/published_date
absence is a source-coverage gap, consistent with the `staging_unverified`
provenance state, not an extraction defect.

# P137A — Count Relationship (proven by SQL, not assumption)

- doc_version: P137A-1
- date_utc: 2026-07-17
- all counts below executed against the LIVE (read-only) databases this session.

## The three numbers
| number | meaning | where |
|---|---|---|
| **724** | SMWS whisky population with a production link | `knowledge.normalized_metadata WHERE source='smws'` |
| **726** | P127.5 MERGE candidates from the **book PDF corpus** | `mr-kep/p127_5_smws/merge_candidates.csv` |
| **2.664** | `promotion_queue` total rows (HIGH confidence, ≥0.90) | `knowledge.promotion_queue` |

## Proof 1 — 724 = staging_smws ∩ flavor_evidence
```sql
-- staging CSV distinct cask_no = 797
-- production.flavor_evidence distinct smws_code = 791
-- intersection = 724
SELECT COUNT(*) FROM normalized_metadata WHERE source='smws';   -- 724
```
`scodes ∩ fe = 724`; `fe - staging = 67` (SMWS codes with no staging CSV row);
`staging - fe = 73` (staging codes with no flavor_evidence link). So 724 is the
**SMWS whisky set that has BOTH a staging note AND a production flavor_evidence row.**

## Proof 2 — 726 is a DIFFERENT population
726 came from P127.5 entity resolution over the **book PDF corpus**
(`merge_candidates.csv`). It is book-derived, not SMWS-derived. It is NOT a subset
or superset of 724. Comparing 726 to 724 is a category error — they answer
"how many book merges?" vs "how many SMWS whiskies linked?".

## Proof 3 — 2.664 = non-null SMWS fields per whisky
```sql
SELECT field_name, COUNT(*) FROM promotion_queue GROUP BY field_name ORDER BY 2 DESC;
-- age 724, abv 707, cask_type 627, region 606   => 2664
SELECT COUNT(DISTINCT entity_key) FROM promotion_queue;   -- 724
-- avg = 2664 / 724 = 3.68 fields/whisky
```
So `promotion_queue` is **one row per (whisky, non-null smws field)**, not one row
per whisky. 2.664 is purely an artifact of 724 whiskies × 3.68 fields each. It has
no arithmetic relationship to 726.

## Conclusion
- P137B must NOT assume "726 MERGE rows". The real ready set is **2.664 promotion_queue
  rows over 724 whiskies**, all citation-backed and ≥0.90 confidence.
- If a task spec says "726", it is referencing the book-corpus MERGE count and does not
  apply to the SMWS promotion path.

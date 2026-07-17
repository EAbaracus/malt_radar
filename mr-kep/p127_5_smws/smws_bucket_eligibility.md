# P127.5 — Bucket Eligibility (SMWS USA)

| Bucket | Rows | % of 803 |
|---|---|---|
| MERGE (enrich existing whisky) | 726 | 90.4 |
| CREATE (net-new entity) | 0 | 0.0 |
| AMBIGUOUS (human review) | 77 | 9.6 |

- MERGE entity sub-total: 725 unique entities
- AMBIGUOUS entity sub-total: 73 unique entities
- CREATE entity breakdown: none

## P128 READINESS SUMMARY
- Bucket eligibility: COMPLETE (MERGE 726 / CREATE 0 / AMBIGUOUS 77)
- Promotion-ready rows (MERGE+CREATE, ambiguous excluded): 726
- Review queue size (AMBIGUOUS): 77
- Remaining blockers:
  - 727 rows have NULL flavour_profile (resolve before vector promotion)
  - 389 rows have NULL distillery (resolver coverage gap)
  - 73 unique ambiguous SMWS codes (77 rows) unlinked -> human review (P128 AMBIGUOUS path)
  - 6 SMWS codes appear in 2 rows each (duplicate codes): 5.42, 100.12, 39.52, 50.62, 64.60, 94.4
    (dedupe->resolve->expand chain keeps each duplicate's rows in ONE bucket; no data loss)
  - 56 product_name values occur in >1 row (duplicate product names; informational only)
- Recommendation: P128 gate -> MERGE promote (enrich existing whiskies via gate);
  CREATE = 0 (no net-new whisky_id minted by this set);
  AMBIGUOUS -> staging_manual_review_queue.

## Classification rationale (honest note)
All 726 linked SMWS codes resolve to whisky_id values that ALREADY EXIST in
production.whiskies (verified: 790/790 promotion_ready ids present). Therefore they are
MERGE (enrich existing entity), NOT CREATE. CREATE would require a net-new whisky_id,
which this staging set does not produce. This corrects the erroneous "CREATE=790" reading.

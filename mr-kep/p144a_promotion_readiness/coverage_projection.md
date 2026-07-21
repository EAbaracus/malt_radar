# P144A — Coverage Projection (Phase 5)

- total whiskies: 4749
- current ABV non-empty: 2186 (46.03%)
- current Age non-empty: 1630 (34.32%)

## If the 3 READY_NULL_FILL rows are promoted (the ONLY promotable abv/age candidates)
- ABV: 2186 -> 2188 (46.07%)  [+2 rows]
- Age: 1630 -> 1631 (34.34%)  [+1 rows]

## Reality check vs P143 claim
- P143 claimed promoting abv+age would add 1,431 fields (ABV 46%->61%, Age 34%->49%).
- **ACTUAL promotable NULL_FILL = 3** (2 abv + 1 age). The other 1,428 already exist in
  production (NO_CHANGE). Therefore the real gain is +3 fields, NOT +1,431.
- P143's ROI ranking #1/#2 (promote abv/age) is based on a FALSE premise and must be revised.

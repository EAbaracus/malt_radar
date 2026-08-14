# Source Gap Analysis — P103 Corpus Audit
_Generated 2026-07-15 18:01 UTC_

## Processed vs Remaining

| class | count | notes |
|---|---|---|
| Ingested (real books) | 4 | B1 Yearbook, B2 Atlas, B3 Michael Jackson, WA_ARCH Whisky Advocate, JMB2020 Jim Murray Bible (S07), DB_MANUAL Broom Manual (S08) |
| Synthetic seed (no file) | 17 | P103 mock `Source:<hash>` identities |
| Registered, not ingested | 1 | B8 Robin Robinson |
| Remaining raw sources | 45 | incl. SMWS 803-file group, 19 magazines, B4/B5/B7 books, CSVs |

## Estimated remaining whisky coverage

- Conservative measured net-new whisky_ids across all remaining candidates: **~277** (real, from sampled extraction; large PDFs undercounted).
- Current coverage 1737/3876 (44.8%). Adding even a fraction of remaining yield pushes well past 55–60%.
- Upper bound (if all remaining yield were additive and non-overlapping): 2014/3876 = 52.0% (optimistic; real overlap will lower this).

## Expected corroboration increase

- **SMWS (B6):** 803 independent single-cask ratings → highest corroboration value (cross-checks existing tasting facts).
- **Whisky Advocate / Magazine (W3):** 19 issues of independent reviews → strong corroboration, especially for recent vintages.
- **Books (B4/B5/B7):** expert-authored facts → medium corroboration, fill descriptive/attribute gaps.
- Net effect: every remaining source is T2/T3 authority (corroborate-only per P95) — none can sole-certify, but together they raise evidence-quality and corroboration substantially.

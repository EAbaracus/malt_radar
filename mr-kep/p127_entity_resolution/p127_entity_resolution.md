# P127 — Entity Resolution & Promotion Preparation (READ-ONLY)

**Staged resolver** (unicode→token→stopword→blocking→fuzzy→context→confidence). Read-only; no staging/production writes.


## Per-stage statistics

1. Raw candidate mentions (cache): 48658

2. After unicode+token normalization (len≥4): 48658

3. After whisky stopword removal (non-empty): 47228

4. Blocking buckets: 2071 prefix keys; unique groups after dedupe: 30574

5. Fuzzy matched (threshold 0.85): 16725; unmatched: 13849

6. Context signals — age 3779, abv 4872, region 1724, cask 4530, bottler 766

7. Confidence classification → MERGE 16725, CREATE 10829, AMBIGUOUS 3556 (B4b +536)


## Expected database enrichment (upper bound, pre-review)

- New distilleries (potential): 4008
- New brands: 0

- New bottlers: 296
- New expressions: 10081


## Promotion-ready review queue
1. MERGE (enrich existing, low risk)
2. CREATE (resolver-reviewed; distillery leads first incl. 536 B4b)
3. AMBIGUOUS (human decision)


## GO Verdict
**GO WITH WARNINGS.** Staged resolver executed read-only; full candidate universe reclassified with per-stage stats. WARNING: CREATE/AMBIGUOUS are pre-review maxima; single-word/generic (conf 0.4) shrink after human review; blocking threshold 0.85 may miss rare variants. No evidence deleted, no auto-promotion.

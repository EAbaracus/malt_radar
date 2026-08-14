# Book ROI Recalculation (V2)

The original P126 book promotion plan calculated ROI based on the absolute volume of new entities. This V2 recalculation weights candidate books based on their ability to close the **actual knowledge gaps** identified in the P131 `production.db` audit.

## Gap-Weighted Scoring Formula
```
ROI_Score = 10 * (Cask/Finish fields enriched) + 8 * (Region/Country fields enriched) + 5 * (Age/Tasting Notes/ABV/Brand fields) + 3 * (Distillery/Flavor fields)
```

## Recalculated Book Priority (Top 6)

### 1. Malt Whisky Yearbook 2019 (B1)
- **Closed Gaps:** Distillery Founded Year, Owner, parent company, and website links (currently 99%-100% missing in production).
- **Enrichment Impact:** Re-establishes the complete factual backbone of Speyside, Highland, and World distilleries.
- **V2 ROI Score:** **CRITICAL (Jumps to Rank 1)**
- **Reasoning:** It targets the absolute highest deficiency area in the production dataset (100% missing owner/website).

### 2. SMWS USA Archive (A6/A5)
- **Closed Gaps:** Cask Type (98.86% missing), Tasting Notes (63.55% missing), and ABV (53.63% missing).
- **Enrichment Impact:** 792 cask vectors, 13,238 tasting note rows, and exact cask numbers.
- **V2 ROI Score:** **CRITICAL (Rank 2)**
- **Reasoning:** Huge volume of tasting notes and cask types, both of which are highly deficient.

### 3. B4b Jim Murray Complete Book (Prior Extract)
- **Closed Gaps:** Distillery links (40.66% missing), Tasting Notes (63.55% missing).
- **Enrichment Impact:** 536 new distillery leads, 525 flavor profiles.
- **V2 ROI Score:** **HIGH (Rank 3)**

### 4. B5 Flavor Methodology (Whisky Classified / Flavour of Whisky)
- **Closed Gaps:** Flavor profiles / vectors (36.85% missing).
- **Enrichment Impact:** Provides the mathematical baseline (7-axis methodology) to calibrate all other vector merges.
- **V2 ROI Score:** **HIGH (Rank 4)**

### 5. The World Atlas of Whisky (B2) / Michael Jackson (B3)
- **Closed Gaps:** Region (91.24% missing), Country (97.16% missing).
- **Enrichment Impact:** Fills geographic boundaries and region-based metadata for Speyside, Islay, and Spey expressions.
- **V2 ROI Score:** **HIGH (Rank 5)**

### 6. Japanese Whisky (Dedicated JP Ref)
- **Closed Gaps:** Fill missing Japanese distilleries and expressions (currently highly underrepresented).
- **Enrichment Impact:** Speeds up non-Scotch coverage.
- **V2 ROI Score:** **MEDIUM (Rank 6)**

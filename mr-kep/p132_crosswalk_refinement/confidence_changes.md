# Confidence Changes — Crosswalk Refinement

This document explains the confidence classification adjustments applied to the UUID ↔ W-ID crosswalk.

## Confidence Distribution
After applying secondary constraints (Age, ABV, Region, Cask Type, and name patterns), the 790 UUID-to-W-ID candidates are classified as follows:

- **EXACT:** 0 rows (0.0%)
- **STRONG:** 4 rows (0.5%)
- **MEDIUM:** 6 rows (0.8%)
- **WEAK:** 465 rows (58.9%)
- **NO_MATCH:** 315 rows (39.9%)

## Analysis of Confidence Upgrades

### The 4 STRONG Matches
1. **Bowmore SMWS 003.113** ↔ **bowmore 12y** (W000015): Matched due to shared Bowmore distillery and 12-year-old age.
2. **Glen Grant SMWS 9.74** ↔ **glen grant 10yo** (W000017): Matched due to Glen Grant and 10-year-old age.
3. **Glenmorangie SMWS 125.44** ↔ **glenmorangie the original 10y** (W000016): Glenmorangie and 10-year-old age.
4. **Glenmorangie SMWS 125.59** ↔ **glenmorangie the original 10y** (W000016): Glenmorangie and 10-year-old age.

### The 6 MEDIUM Matches
- Matched on Speyside/Islay distilleries (Clynelish, Caol Ila, Mortlach) where age did not match but regional/ABV overlaps were detected (mostly special Diageo release W-ids).

## The False Positive Risk (Critical Finding)
While the 4 STRONG matches satisfy the rules (same age + same distillery), **they are expression-level mismatches**. 
- SMWS 125.44 is an independent single cask bottling at cask strength.
- Glenmorangie 10y is a mass-market core range bottling at 40% ABV.
They do **not** represent the same whisky. Auto-migrating these would overwrite core-range official metadata with single-cask metadata.

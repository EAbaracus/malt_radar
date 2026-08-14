# Migration Ready Candidates

This document summarizes the UUIDs cleared for automatic migration based on the refined crosswalk.

## Auto-Migration Summary
- **Total Cleared for Auto-Migration:** 0 rows (0.0%)
- **Total Routed to Manual Review Queue:** 790 rows (100.0%)

## Reason for Zero Auto-Migration
Although 4 rows matched at **STRONG** confidence based on the rule (shared `distillery_id` and `age`), they are verified **expression-level mismatches**:
- **Official Bottlings (OB)** (e.g. `bowmore 12y` W000015) vs **Independent Single Cask Bottlings (IB)** (e.g. `Bowmore SMWS 003.113` 12yo single cask).
- Merging these would cause data corruption (overwriting standard distillery data with single-cask data).

## Recommendations for Promotion
1. **Zero Auto-Promotion:** No SMWS UUID should be auto-promoted or merged into existing legacy `W...` entries.
2. **Treat as Genuinely New:** All 790 SMWS expressions are single-cask releases that do not exist in the legacy `W...` database. They must be promoted as **CREATE** actions (net-new expressions), preserving their unique UUIDs, rather than trying to merge them into official bottling entries.
3. **Waiver Request:** A policy waiver should be obtained to bypass the D3 "derive via consensus" rule for SMWS single casks, allowing them to be loaded directly to the database as net-new entities.

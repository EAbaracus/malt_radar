# [DEPRECATED / HISTORICAL] Classic Pipeline Stages (P1 - P25)

**WARNING:** This pipeline has been **RETIRED** per P500-A. The active canonical architecture is **MR-KEP** (domain pipeline) + **KEP Runtime** (safety/execution layer). All promotions now use `PromotionGate` under `kep_review_runtime`. Do not run or reference this pipeline for active work.

For historical reference only, the classic stages were:

- **P1-P17**: Core schema creation, dataset ingestion, and basic coverage metrics.
- **P18 (A-E)**: Library-wide extraction. Scans PDF books, utilizes anchor regex to deduce flavors, and deduplicates.
- **P19 & P19.5**: Identity matching and Canonicalization. Maps newly found whiskies to existing catalog via Levenshtein fuzzy match.
- **P20 & P23**: Production Merge. Safely executes DB insertions and Profile Enrichment via weighted averaging.
- **P21 & P24**: Real-time Quality & Coverage Impact Audits.
- **P25**: Automatic Book Ingestion (Daemon/CLI trigger for automated end-to-end extraction).

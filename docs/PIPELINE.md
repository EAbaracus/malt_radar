# Pipeline Stages (P1 - P25)

The Malt Radar pipeline uses sequential Python scripts to safely massage, deduplicate, and ingest data.

- **P1-P17**: Core schema creation, dataset ingestion, and basic coverage metrics.
- **P18 (A-E)**: Library-wide extraction. Scans PDF books, utilizes anchor regex to deduce flavors, and deduplicates.
- **P19 & P19.5**: Identity matching and Canonicalization. Maps newly found whiskies to existing catalog via Levenshtein fuzzy match.
- **P20 & P23**: Production Merge. Safely executes DB insertions and Profile Enrichment via weighted averaging.
- **P21 & P24**: Real-time Quality & Coverage Impact Audits.
- **P25**: Automatic Book Ingestion (Daemon/CLI trigger for automated end-to-end extraction).

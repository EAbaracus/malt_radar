# Entity Resolution Analysis (Sample size: 50)

Based on the re-run against the production aliases and whiskies tables, unresolved records are distributed as follows:

- **Missing Aliases:** 0
- **Parser Failure:** 0
- **Normalization Failure:** 0
- **Database Coverage (True Net-New):** 47
- **Extraction Bug / Malformed:** 3

**Conclusion:** The vast majority of the unresolved entities are genuine database coverage gaps. Malt Radar simply does not possess these highly obscure, single-cask SMWS expressions in `production.db`.

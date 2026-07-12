# Malt Radar CLEAN

Malt Radar is a production-grade data pipeline for detecting, matching, and extracting whisky flavor profiles from PDF books and structured datasets into a centralized SQLite database (`production.db`).

## Architecture
- **NLP Flavor Extraction**: Employs dictionary-based anchor scanning to extract quantitative flavor vectors.
- **Identity Matching**: Fuzzy matching across historical catalogs and new textual extractions.
- **Data Auditing**: Transactional merges with fallback schemas and robust hashing.

Please see the `docs/` folder for pipeline documentation.

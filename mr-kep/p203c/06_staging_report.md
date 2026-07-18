# P203C — 06 Staging Report

Write target: `data/p203c_staging/editorial_staging.db` (editorial staging ONLY — never production tables).
- Staging rows: **15** (no duplicates).
- Persisted fields (EXCERPT_POLICY-compliant): source, author, url, publication_date, capture_timestamp, content_sha256, http_status, content_type, content_length, excerpt(≤15w), whisky_raw_name, distillery_crosswalk fields, match fields, abv/age/cask, score, flavor_vector, schema_valid.
- **No raw HTML, no full review text, no response-header blobs** persisted (per your explicit storage directive).
- production.db NOT touched; knowledge.db NOT touched.

# P127.5 — SMWS USA Entity Resolution Manifest (READ-ONLY)

- resolver_version: P127.5
- strategy: P127 7-stage replica (unicode -> token -> stopword -> blocking -> fuzzy -> context -> confidence), adapted for SMWS exact-identity codes
- similarity_algorithm: SMWS code = exact identity token (deterministic join to production.db flavor_evidence.smws_code / promotion_ready.smws_code); difflib.SequenceMatcher ratio used ONLY as fuzzy fallback for unlinked codes against whisky.name
- similarity_thresholds: blocking 0.85 (fuzzy fallback only); below 0.85 -> AMBIGUOUS
- confidence_thresholds (P127): HIGH>=0.92, MEDIUM 0.85-0.919, LOW 0.78-0.849, UNRESOLVED<0.78
- blocking_strategy: primary block = smws_code (exact); secondary = normalized (distillery + product_name) for fuzzy fallback
- reference_db: output/import/production.db
- reference_db_sha256: d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961
- staging_file: mr-kep/p119_6/staging_smws_tasting_notes.csv
- staging_file_sha256: 10113e53e953742e204ba2ca350cff7cdc5537653ed963499994b04c478d5a0f
- execution_timestamp_utc: 2026-07-16T11:07:31Z
- mutation: NONE (read-only via get_read_connection; only new staging CSV/MD written under mr-kep/p127_5_smws/)

# Architecture Memory

- **Database:** SQLite (`production.db`), 34 tables. The LIVE schema in
  `output/import/production.db` is the single source of truth.
- **Canonical DDL:** `schema/schema.sql` is regenerated verbatim from `sqlite_master`
  (P56, 2026-07-12T17:32:52Z, SHA256 `7e75d35052da…`). It is authoritative; do not hand-edit.
- **Schema domains:**

  - **Core product:** whiskies, distilleries, flavor_profiles, tasting_notes, price_history
  - **Entity graph:** brands, bottlers, companies, distillery_company_links, bottler_product_links, whisky_product_entities, entity_aliases, entity_external_links, external_entities, external_reference_links
  - **Knowledge base:** knowledge_regions, knowledge_glossary_terms, knowledge_guides, official_source_references
  - **Review / audit:** review_actions, review_conflict_log, review_status_transitions, promotion_audit_log
  - **Staging / pipeline:** staging_external_reviews, staging_tasting_notes, staging_p6_flavor_profile_candidates, staging_book_flavor_profiles, staging_manual_review_queue, staging_new_products, staging_notebooklm_flavor_profiles, staging_flavor_profile_candidates, staging_web_tasting_notes, staging_flavor_profile_candidates_full, staging_historical_menu_prices

- **NLP Flavor Engine:** anchor-guided regex scanners over 7 flavor dimensions
  (smoky, peaty, fruity, sweet, spicy, maritime, sherry).
- **Identity Resolver:** string normalization + Levenshtein fuzzy matching of
  expressions to master products.
- **Known stale reference:** the pre-P56 `schema.sql` described a legacy model
  (countries/regions/whisky_products/cask_types/…) that does not exist in the
  live DB; it has been replaced by the live-generated schema.

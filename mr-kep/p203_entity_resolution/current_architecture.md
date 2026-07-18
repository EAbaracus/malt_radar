# P203 — Current Identity Architecture

Derived from `schema/schema.sql` (production.db, 34 tables),
`mr-kep/p136_knowledge_bootstrap/migration/schema.sql` (knowledge.db, 18 tables),
and `mr-kep/editorial/matching.py`. **No SQL executed; DDL inspected read-only.**

## production.db — canonical serving store
Entity-relevant tables (from DDL):
- `whiskies` — PK `whisky_id TEXT`; cols `name, original_name, distillery_id,
  country, region, type, age, age_statement, nas, abv, brand, …`.
- `distilleries` — PK `distillery_id TEXT`; cols `name, country, region, owner,
  parent_company, wikidata_id, wikipedia_url, data_confidence, …`.
- `brands` / `bottlers` / `companies` — PK INTEGER AUTOINCREMENT; `brand_name` /
  `bottler_name` / `company_name` UNIQUE.
- `entity_aliases` — `(alias_id, entity_type, entity_id, alias_name)`;
  `entity_type` enum documented as `'brand','bottler','company','distillery'`.
- `entity_external_links` — `(entity_type, entity_id, url, link_type)` where
  `link_type` ∈ `'wikipedia','official','api'`.
- `external_entities` — `(entity_id, entity_name UNIQUE, entity_type, base_url)`.
- `whisky_product_entities` — `(whisky_id, entity_type, entity_id, relationship_type)`
  where `relationship_type` ∈ `'owned_by','branded_as'`.
- `distillery_company_links` / `bottler_product_links` — ownership / bottling links.
- `official_source_references` — `(entity_type, entity_id, source_category,
  source_name, source_url, field_name, field_value, confidence, license_risk,
  copyright_risk)`. **This is the official-source citation mechanism** that can
  carry provenance for official aliases.

**Key observation:** `whisky_id` and `distillery_id` are TEXT (W-ids / UUIDs), while
`brand/bottler/company` use INTEGER surrogate keys. Key *types* differ across entity kinds.

## knowledge.db — staging / consensus store
- `sources` — `source_type ∈ book|notebooklm|smws|community|web`, `authority_tier T1=1..T4=4`.
- `evidence` — `entity_key` (whisky_id or distillery_id), `entity_type ∈
  whisky|distillery|brand|bottler`, `field_name`, `normalized_value`,
  `extraction_method ∈ regex|llm|lookup`.
- `normalized_metadata` — resolved entity attributes keyed by `entity_key`.
- `review_queue` — `issue_type ∈ conflict|identity|low_conf|historical`.
- `merge_history` — every applied merge (idempotent `dedupe_key`).
- `promotion_queue` — `field_class ∈ IMMUTABLE|APPEND|REPLACEABLE|REVIEW`,
  `action ∈ APPLY|APPEND|REVIEW|REJECT`, `dedupe_key` enforces idempotency.
- `source_priority`, `confidence` ledger, `canonical_flavor_vectors`,
  `canonical_tasting_notes`, `processing_log` (stages
  `raw→normalize→canonicalize→merge→consensus→queue→review→export`).
- **No alias tables exist in knowledge.db** — aliases live only in production.db.

## ID-space mismatch (the root crosswalk problem)
- production.db `whiskies` = 3,959 W-ids + 790 UUID-ids (per `p129_crosswalk`).
- knowledge.db uses its own UUID PKs everywhere.
- Bridge: `promotion_queue.entity_key` already holds the **production whisky_id**
  (resolved at P136 ingest from `flavor_evidence.whisky_id`), so SMWS promotion needs
  no UUID↔W translation (`p137a` D5). Book-sourced UUID entities still need a bridge —
  the deferred P129 crosswalk.

## Matching layer (today)
- `WhiskyRegistryMatcher` (`matching.py`) reads `whiskies(name, whisky_id, age)`
  read-only and returns `MatchDecision(matched_master_whisky_id, match_status,
  match_confidence)`. It is **whisky-name only, alias-blind, no phonetic/token**.
- Editorial adapters (`editorial_adapter_factory.py`) are concrete skeletons that
  extract `raw_name` from the article title and **delegate identity/score/flavor
  derivation to the LLM Knowledge Extractor**; adapters open neither production.db nor
  do any matching. So editorial identity resolution happens downstream via the matcher.

## Source identity handling observed
- **SMWS:** promoted via `promotion_queue.entity_key` (production whisky_id); SMWS code
  overlap `uuid ∩ W = 0` → no direct code bridge (`p129`).
- **Book / NotebookLM:** `evidence.entity_key` resolved at ingest; unresolved entities
  classified by `B4b/classify_unresolved.py` (OCR-aware rules, auto-suppress noise).
- **Editorial (P201/202):** `raw_name → WhiskyRegistryMatcher → match_status/confidence`.
- **CSV / Whiskybase / WhiskyNotes:** adapters exist (`acquisition/adapters/`), return
  normalized dicts; matching funnels through the same registry matcher.

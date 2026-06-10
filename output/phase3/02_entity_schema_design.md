# Entity Schema Design

## 1. Entity Master Tables
These tables hold verified, canonical entities that are involved in the production, bottling, or branding of whiskies, but are distinct from physical distilleries.

* `brands`: Brand names (e.g., "Johnnie Walker", "Chivas Regal").
* `bottlers`: Independent bottlers (e.g., "Gordon & MacPhail", "Signatory Vintage").
* `companies`: Parent corporations or owning groups (e.g., "Diageo", "Pernod Ricard").
* `external_entities`: Third-party sources of truth or review sites (e.g., "WhiskeyFYI", "Whisky Edition").
* `entity_aliases`: Alternate names or misspellings mapped to canonical entity IDs.
* `entity_external_links`: URLs, Wikipedia links, or API endpoints for entities.

## 2. Relationship Mapping Tables
These tables connect products and distilleries to the entity master tables.

* `whisky_product_entities`: Many-to-many map connecting `whiskies` to `brands`, `bottlers`, or `companies`.
* `distillery_company_links`: Connects a `distillery` to its owning `company` (handling history/date ranges if necessary).
* `bottler_product_links`: Explicit connection between an independent bottler and a specific whisky release.

## 3. Staging Tables (Candidate Queue)
These tables hold unverified or candidate data imported from APIs and documents.

* `staging_new_products`: Holds raw new product candidates (from Whisky Edition API, etc.).
* `staging_tasting_notes`: Holds candidate tasting notes tied to a staging product or a master whisky.
* `staging_historical_menu_prices`: Holds 35ml pour prices (e.g., from The Malt List).
* `staging_external_reviews`: Holds external scores and reviews (e.g., from WhiskeyFYI).
* `staging_manual_review_queue`: A workflow queue tracking the approval status (Pending, Approved, Rejected) of items in the above staging tables.

## 4. Knowledge Tables
These tables store reference encyclopedic data.

* `knowledge_regions`: Geographical info, historical notes about Scotch regions.
* `knowledge_glossary_terms`: Definitions of whisky terminology.
* `knowledge_guides`: Long-form reference articles or guides.
* `external_reference_links`: Links from knowledge tables to external URLs.

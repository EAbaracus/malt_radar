# P128 — Field Merge Matrix (READ-ONLY policy)

Classification of **every** field in the real `production.db` schema (gate-read, 2026-07-16).
Grounded in actual `PRAGMA table_info` output — no assumed columns.

**Classes:**
- **IMMUTABLE** — set once at create; never updated by book merge (identity / provenance keys).
- **APPEND-ONLY** — book knowledge may add, never overwrite (accumulates evidence).
- **REPLACEABLE** — may be overwritten when incoming confidence ≥ threshold AND source authority ≥ incumbent.
- **REVIEW-REQUIRED** — any change routes to `staging_manual_review_queue`; never auto-applied.

---

## distilleries
| Field | Class | Rule |
|---|---|---|
| distillery_id | IMMUTABLE | PK, canonical identity |
| name | REVIEW-REQUIRED | rename affects joins; human gate |
| country | REPLACEABLE | conf ≥ 0.90 + source authority |
| region | REPLACEABLE | conf ≥ 0.90; cross-check knowledge_regions |
| owner | REVIEW-REQUIRED | ownership changes are legal/temporal |
| parent_company | REVIEW-REQUIRED | corporate structure; human gate |
| founded_year | REVIEW-REQUIRED | historical fact; conflict-prone across books |
| founder | REVIEW-REQUIRED | historical fact |
| status | REVIEW-REQUIRED | active/closed/mothballed — temporal |
| location | REPLACEABLE | conf ≥ 0.85 |
| coordinates | REPLACEABLE | conf ≥ 0.90; numeric validation |
| official_website | REPLACEABLE | conf ≥ 0.80 |
| wikidata_id | APPEND-ONLY | external ID; add if empty, else review |
| wikipedia_url | APPEND-ONLY | add if empty |
| data_confidence | REPLACEABLE | recomputed on merge (max of sources) |
| notes_for_review | APPEND-ONLY | book citations appended |

## whiskies
| Field | Class | Rule |
|---|---|---|
| whisky_id | IMMUTABLE | PK |
| name | REVIEW-REQUIRED | canonical product name |
| original_name | IMMUTABLE | provenance of first ingest |
| distillery_id | REVIEW-REQUIRED | FK reassignment is structural |
| country | REPLACEABLE | conf ≥ 0.90 |
| region | REPLACEABLE | conf ≥ 0.90 |
| type | REVIEW-REQUIRED | single malt/blend classification |
| age | REVIEW-REQUIRED | numeric conflict → review (see conflict rules) |
| age_statement | REVIEW-REQUIRED | tied to age |
| nas | REPLACEABLE | boolean; conf ≥ 0.90 |
| abv | REVIEW-REQUIRED | numeric conflict-prone; ±0.1 tolerance |
| bottle_size | REPLACEABLE | conf ≥ 0.85 |
| cask_type | APPEND-ONLY | multiple casks legitimate; accumulate |
| finish_type | APPEND-ONLY | accumulate |
| cask_strength | REPLACEABLE | boolean; conf ≥ 0.90 |
| meta_critic_score | REPLACEABLE | recomputed aggregate |
| user_score | IMMUTABLE | user-sourced; books never touch |
| data_confidence | REPLACEABLE | recomputed |
| completed_fields | REPLACEABLE | recomputed metadata |
| notes_for_review | APPEND-ONLY | citations appended |
| brand | REVIEW-REQUIRED | brand association |

## brands
| Field | Class | Rule |
|---|---|---|
| brand_id | IMMUTABLE | PK |
| brand_name | REVIEW-REQUIRED | canonical name |
| description | APPEND-ONLY | book descriptions appended w/ citation |
| created_at | IMMUTABLE | provenance timestamp |

## bottlers
| Field | Class | Rule |
|---|---|---|
| bottler_id | IMMUTABLE | PK |
| bottler_name | REVIEW-REQUIRED | canonical name |
| country | REPLACEABLE | conf ≥ 0.85 |
| created_at | IMMUTABLE | provenance |

## flavor_profiles
| Field | Class | Rule |
|---|---|---|
| whisky_id | IMMUTABLE | FK identity |
| whisky_name | IMMUTABLE | denormalized identity |
| production_bottle_name | IMMUTABLE | link key |
| match_score | REPLACEABLE | recomputed by resolver |
| match_method | REPLACEABLE | recomputed |
| flavor_vector | REVIEW-REQUIRED | 7-axis vector; consensus-gated (knowledge.db) |
| flavor_profile | REVIEW-REQUIRED | derived from vector |
| flavor_tags | APPEND-ONLY | accumulate descriptors w/ citation |
| flavor_source | APPEND-ONLY | source list grows |
| flavor_data_confidence | REPLACEABLE | recomputed |
| production_price | IMMUTABLE | **never touched; price rule (AGENTS.md)** |
| production_rating | REPLACEABLE | recomputed |
| production_region | REPLACEABLE | conf ≥ 0.90 |
| notes_for_review | APPEND-ONLY | citations |
| source_count | REPLACEABLE | recomputed counter |
| evidence_count | REPLACEABLE | recomputed counter |
| enrichment_version | REPLACEABLE | version stamp on merge |

## tasting_notes
| Field | Class | Rule |
|---|---|---|
| whisky_id | IMMUTABLE | FK |
| normalized_name | IMMUTABLE | link key |
| distillery_id | REVIEW-REQUIRED | FK reassignment |
| source_url | IMMUTABLE | provenance |
| source_name | IMMUTABLE | provenance |
| data_confidence | REPLACEABLE | recomputed |
| notes_for_review | APPEND-ONLY | citations |
| nose_notes | APPEND-ONLY | each book note is a distinct row/append |
| palate_notes | APPEND-ONLY | append |
| finish_notes | APPEND-ONLY | append |
| aroma_tags | APPEND-ONLY | accumulate |
| source_system | IMMUTABLE | provenance |
| source_doc | IMMUTABLE | provenance (book SHA/name) |
| source_entry_number | IMMUTABLE | provenance |

## knowledge_regions
| Field | Class | Rule |
|---|---|---|
| region_id | IMMUTABLE | PK |
| region_name | REVIEW-REQUIRED | canonical |
| description | APPEND-ONLY | book descriptions appended |
| characteristics | APPEND-ONLY | accumulate |
| source / source_id / url | APPEND-ONLY | provenance list |
| country | REPLACEABLE | conf ≥ 0.90 |
| confidence | REPLACEABLE | recomputed |

## official_source_references (citation ledger)
| Field | Class | Rule |
|---|---|---|
| ref_id | IMMUTABLE | PK |
| entity_type / entity_id | IMMUTABLE | link |
| source_* / field_name / field_value | APPEND-ONLY | **every merge writes a citation row here** |
| confidence | IMMUTABLE | as-recorded |
| license_risk / copyright_risk | IMMUTABLE | as-assessed at ingest |
| retrieved_at / created_at | IMMUTABLE | provenance |

## entity_aliases
| Field | Class | Rule |
|---|---|---|
| alias_id | IMMUTABLE | PK |
| entity_type / entity_id | IMMUTABLE | link |
| alias_name | APPEND-ONLY | new aliases append; dedupe on (entity, alias) |

## Price fields — GLOBAL RULE
`production_price`, `price_history.*`, `staging_historical_menu_prices.*` are **IMMUTABLE for book merge** and **never exposed in UI/API** (AGENTS.md Product Rule). Books never write price.

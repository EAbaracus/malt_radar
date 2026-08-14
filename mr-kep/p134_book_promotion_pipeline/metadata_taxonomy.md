# P134 — Metadata Taxonomy (READ-ONLY Design)

- doc_version: P134-1
- date_utc: 2026-07-16
- mode: DESIGN ONLY; zero DB writes; grounded in real `production.db` (`PRAGMA table_info`) + `knowledge.db` schemas
- scope: every metadata field supported by Malt Radar, grouped, with lifecycle class (mandatory/optional/deprecated/unsupported)

## Field lifecycle classes
- **mandatory** — required for a record to be promotable (validation gate fails if absent)
- **optional** — enriched when present in source; promotion tolerates absence
- **deprecated** — column exists in schema but out of promotion scope (legacy / superseded)
- **unsupported** — not represented in production/knowledge schema; pipeline must not emit

---

## 1. Identity
| field | table | lifecycle | notes |
|---|---|---|---|
| whisky_id | whiskies / flavor_profiles / tasting_notes | mandatory | PK; `W####` (seed) or UUID (SMWS importer). IMMUTABLE |
| name | whiskies | mandatory | canonical product name. REVIEW-REQUIRED |
| original_name | whiskies | optional | provenance of first ingest. IMMUTABLE |
| distillery_id | whiskies | mandatory | FK→distilleries. REVIEW-REQUIRED reassignment |
| distillery (name) | distilleries.name | mandatory (entity) | REVIEW-REQUIRED |
| bottler | bottlers / bottler_product_links | optional | independent bottler; extracted via BOTTLER_RE |
| brand | whiskies.brand / brands | optional | brand association; REVIEW-REQUIRED |
| expression | derived (name+age+abv+cask) | mandatory (logical) | an expression = one whiskies row; identity = name+age+abv+cask |

## 2. Technical
| field | table | lifecycle | notes |
|---|---|---|---|
| age | whiskies | mandatory* | numeric years; *mandatory for age-stated, NAS flag if NAS. REVIEW-REQUIRED (conflict→distinct expression) |
| age_statement | whiskies | optional | text form of age |
| abv | whiskies | mandatory | % alc; REVIEW-REQUIRED (±0.1 tolerance) |
| nas | whiskies | optional | boolean no-age-statement |
| vintage | — | unsupported | not in schema; capture as note only |
| cask_type | whiskies | optional | APPEND-ONLY (multi-cask legitimate) |
| cask_number | staging (SMWS) | optional | SMWS cask #; transient identity, not promoted to whiskies |
| bottle_size | whiskies | optional | REPLACEABLE conf≥0.85 |
| release_year | — | unsupported | derive from book edition year, store as note |
| bottle_count | — | unsupported | limited-edition counts not in schema |

## 3. Sensory
| field | table | lifecycle | notes |
|---|---|---|---|
| nose_notes | tasting_notes | optional | APPEND-ONLY per book |
| palate_notes | tasting_notes | optional | APPEND-ONLY |
| finish_notes | tasting_notes | optional | APPEND-ONLY |
| tasting_notes_raw | staging | optional | verbatim; copyright-gated (C6) |
| flavor_vector | flavor_profiles / canonical_vectors | mandatory (for flavor) | 7-axis (smoky,peaty,fruity,sweet,spicy,maritime,sherry). REVIEW-REQUIRED; **only via knowledge.db consensus** |
| flavor_profile | flavor_profiles | optional | derived label from vector |
| flavor_tags | flavor_profiles | optional | APPEND-ONLY descriptors |
| nose/palate/finish_summary | staging_book_flavor_profiles | optional | per-book; route to tasting_notes append |
| finish (categorical) | whiskies.finish_type | optional | APPEND-ONLY |

## 4. Commercial
| field | table | lifecycle | notes |
|---|---|---|---|
| msrp / price | production_price / price_history | **unsupported for book merge** | PRICE FIREWALL (AGENTS.md Product Rule + promotion_contract C7). Books NEVER write price |
| availability | — | unsupported | not in schema |

## 5. Media
| field | table | lifecycle | notes |
|---|---|---|---|
| image / label | — | unsupported | no image column in production.db; out of scope |
| source_doc (book SHA) | tasting_notes / official_source_references | mandatory (provenance) | IMMUTABLE provenance, not "media" |

## 6. Knowledge / reference (knowledge.db + knowledge_* tables)
| field | table | lifecycle | notes |
|---|---|---|---|
| glossary terms | knowledge_glossary_terms | optional | APPEND-ONLY |
| guides | knowledge_guides | optional | APPEND-ONLY |
| regions | knowledge_regions | optional | description/characteristics APPEND-ONLY; country REPLACEABLE≥0.90 |
| citations | citations / official_source_references | mandatory (per change) | C1 — every promoted change writes a citation row |

## 7. Deprecated / legacy columns (present in schema, out of promotion scope)
| field | table | reason |
|---|---|---|
| foo.w_id | foo | scratch table, not a real entity |
| whiskies.finish_type (REAL) | whiskies | typed inconsistently; treat as APPEND-ONLY text, not numeric |
| aroma_tags (REAL) | tasting_notes | should be TEXT list; currently REAL — normalization needed before use |

## 8. Confidence / provenance metadata (pipeline-internal, not a "field")
- extraction_confidence, parser_confidence, signal_confidence, overall_confidence, source_confidence — carried on staging rows; consumed by confidence engine (Phase 6), not promoted verbatim.

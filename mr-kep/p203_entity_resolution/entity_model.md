# P203 — Canonical Entity Specification

Proposed single identity model. Each canonical entity has a stable `canonical_id`
(TEXT, source-agnostic) plus typed attributes and an `aliases` relation. Built on top
of the **existing** tables; no replacement of working infrastructure.

## Entity types (reuse existing taxonomy)
| Entity | Existing home | Existing PK | Notes |
|---|---|---|---|
| Whisky (Expression) | `production.whiskies` | `whisky_id TEXT` | core product; needs alias support (currently absent) |
| Distillery | `production.distilleries` | `distillery_id TEXT` | has `entity_aliases` support |
| Brand | `production.brands` | `brand_id INTEGER` | has `entity_aliases` support |
| Bottler | `production.bottlers` | `bottler_id INTEGER` | independent bottler; has alias support |
| Company | `production.companies` | `company_id INTEGER` | owner/parent; has alias support |
| Series | *(new)* | canonical_id | e.g. "Cask Strength Edition", "Distillers Edition" |
| Edition | *(new, sub-of Expression)* | canonical_id | vintage / batch / single-cask |
| Region | `production.knowledge_regions` | `region_id INTEGER` | `region_name` UNIQUE |
| Country | `production.distilleries.country` | derived | currently only 2.84% populated (`p143`) |
| Source | `knowledge.sources` | `source_id UUID` | `source_type`, `authority_tier` |
| Expression | ≡ Whisky entity above | — | alias term for a bottled product |

## Canonical Whisky (Expression) attributes
Reuse `whiskies` columns directly: `name, original_name, distillery_id, country,
region, type, age, age_statement, nas, abv, cask_type, finish_type, cask_strength,
brand`. Add a **canonical alias relation** (see `alias_policy.md`) keyed by `whisky_id`.

## Canonical Distillery attributes
Reuse `distilleries`: `name, country, region, owner, parent_company, founded_year,
wikidata_id, wikipedia_url`. Aliases already supported via `entity_aliases`.

## Canonical Brand / Bottler / Company
Reuse `brands/bottlers/companies` `name` + `entity_aliases`. Bottler↔whisky link via
`bottler_product_links`; company↔distillery via `distillery_company_links`.

## New entities needed (Series / Edition)
Not present today. Series/Edition naming is the #1 source of identity inconsistency
(e.g. "Glenlivet 12" vs "The Glenlivet 12 Year Old" vs SMWS code). Recommend a
lightweight `series` and `edition` table in knowledge.db staging, promoted like other
metadata via `promotion_queue`. **Out of scope for this READ-ONLY phase** — flagged for
implementation plan.

## External identity (reuse)
- `external_entities` — universal external ID space (`entity_name` UNIQUE, `entity_type`, `base_url`).
- `entity_external_links` — map canonical entity → external URL (wikipedia/official/api).
- `official_source_references` — provenance-backed official attribute values (carries
  `confidence`, `license_risk`, `copyright_risk`).

## Canonical ID strategy
- Keep existing `whisky_id` / `distillery_id` TEXT keys as the canonical production keys.
- knowledge.db retains its UUID `entity_key`; the `promotion_queue.entity_key` bridge
  stays the single join point (D5). No new ID space is introduced in this phase.

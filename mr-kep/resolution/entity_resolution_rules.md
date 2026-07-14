# Entity Resolution Rules — MR-KEP P63

> **Phase:** P63 — Source Resolution & Coverage Planner. **Spec only** — no
> scraper, parser, extractor, or download code. Deterministic, evidence-first,
> read-only. Built on the Sprint 1 authority layer (`mr-kep/authority/`).

This document defines the deterministic rules the Source Resolution Engine
applies to decide **which sources, in which order** resolve each field for each
entity type. It is the human-readable companion to
`resolution/source_resolution_model.yaml` and
`resolution/source_resolution_matrix.csv`.

## Entity types

| entity_type | Description | Identity owner |
|-------------|-------------|----------------|
| distillery | A production site | T1_authoritative |
| brand | A market brand (may span sites/OBs) | T1_authoritative |
| whisky | A named product line | T1_authoritative |
| bottling | A specific bottling (incl. independent) | T1_authoritative |

## Field types (inherited from `authority/field_rules.yaml`)

| field_type | Fields | Authority ceiling |
|------------|--------|-------------------|
| identity | distillery_name, region, country | T1_authoritative |
| official_bottling | abv, age_statement, cask_type | T1_authoritative |
| sensory_evaluation | nose, palate, finish, flavor_axes | T2_expert |
| scored_assessment | score | T2_expert |
| supporting | community_rating | T3_community |

## Source classes → authority mapping

Every source class maps onto a Sprint 1 authority `source_key` + tier — the
resolution layer never invents a new trust ranking.

| Source class | authority source_key | Tier | Evidence type |
|--------------|----------------------|------|---------------|
| official | producer_technical_sheet | T1 | primary_source_quote |
| regulatory | regulatory_register | T1 | primary_source_quote |
| official_wayback | producer_technical_sheet (archived) | T1 | primary_source_quote (`archived_snapshot`) |
| book | reference_book *(proposed)* | T2 | expert_quote |
| expert_review | whiskyfun | T2 | expert_quote |
| structured_metadata | structured_metadata *(proposed)* | T2 | aggregated_link |
| community | community_aggregate | T3 | aggregated_link |

*`reference_book` and `structured_metadata` are **proposed** additions to
`authority/source_priority.yaml`. P63 does not edit the authority layer; the
proposal is recorded in `source_resolution_model.yaml → proposed_authority_additions`.*

## Core resolution rules (deterministic)

1. **Official → use directly.** If an `official` (or `regulatory` /
   `official_wayback`) source yields a T1 field, it is used directly as the
   winning value.
2. **No official → Tier 2 fallback.** If no T1 source yields the field, the
   `fallback_chain` (book, expert_review, structured_metadata) may PROPOSE a
   value — but a T1-ceiling field proposed by a T2/T3 source **cannot be
   certified as that field**; it is routed to Certification/Audit
   (see `conflict_resolution.md`).
3. **Conflict → Certification.** If two sources disagree and the named merge
   policy cannot resolve deterministically, route to the Certification path
   (`certification_paths.md`), never average or silently pick.
4. **Single source → low confidence.** One source ⇒ base confidence only, no
   agreement bonus (`authority/confidence.yaml`).
5. **Multiple independent sources → raise confidence.** ≥2 *independent*
   sources agreeing ⇒ apply the agreement bonus (capped). Same publisher under
   different URLs does not count as independent.

## Determinism guarantees

- `preferred_source_order` and `fallback_chain` are **ordered lists**; the
  resolver always attempts them left-to-right.
- Ties within a tier break by `authority/source_priority.yaml` numeric priority.
- No randomness, no network calls in P63 — this is a planning layer that emits a
  resolution *plan*, not fetched data.

## Read-only & no-fabrication

- The resolver **plans** sources; it does not fetch, parse, or write anything.
- If coverage is absent for a field, the plan marks it `UNCOVERED` — it never
  fabricates a value or a source.
- Production data is never touched.

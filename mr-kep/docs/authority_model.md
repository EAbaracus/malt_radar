# Authority Model — MR-KEP

How MR-KEP decides *whose word counts* when sources disagree. This is the
human-readable companion to `authority/authority_matrix.yaml`,
`source_priority.yaml`, and `field_rules.yaml`.

## Tiers

Three authority tiers, ordered by trust:

| Tier | Rank | Certifies | Forbidden to certify |
|------|------|-----------|----------------------|
| T1_authoritative | 1 | identity, official_bottling, regulatory_facts | subjective_flavor |
| T2_expert | 2 | sensory_evaluation, tasting_notes, scored_assessment, expert_opinion | identity, regulatory_facts |
| T3_community | 3 | supporting_evidence_only | identity, regulatory_facts, sole_source facts |

Lower rank number = more trusted. T1 always beats T2/T3 on identity and
official-bottling facts.

## Field-category mapping

Each extractable field belongs to a category with an **authority ceiling** — the
highest tier allowed to certify it:

- **identity** (distillery_name, region, country) → ceiling T1.
- **official_bottling** (abv, age_statement, cask_type) → ceiling T1.
- **sensory_evaluation** (nose, palate, finish, flavor_axes) → ceiling T2.
- **scored_assessment** (score) → ceiling T2.
- **supporting_evidence_only** (community_rating) → ceiling T3, never sole source.

A field extracted by a too-low tier is REJECTED by the Validation Agent, not
silently kept.

## Priority within a tier

When two sources share a tier, `source_priority.yaml` breaks the tie with a
numeric `priority` (lower = higher precedence). Unlisted/unknown sources fail
safe to `T3_community` / priority `99` — an unknown source can never override a
known one.

## Confidence contribution

`confidence.yaml` gives each evidence type a base confidence
(`bottle_print` 0.98, `primary_source_quote` 0.95, `expert_quote` 0.90,
`aggregated_link` 0.55, `inferred` 0.20). Agreement among ≥2 independent
sources adds a capped bonus. Penalties subtract for missing evidence, low
authority, normalization failure, or unresolved conflict.

## Why this model

- **Prevents fabrication of authority.** A community rating can never masquerade
  as an official ABV.
- **Keeps provenance honest.** Sensory claims come from experts, identity from
  producers — each field knows its trustworthy source.
- **Deterministic.** Given the tiers + priorities + policies, the resolution of
  any conflict is computable, not opinion.

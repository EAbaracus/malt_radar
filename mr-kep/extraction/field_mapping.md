# Canonical Field Mapping — MR-KEP P65

> Spec/docs only, deterministic, evidence-first, read-only, no fabrication.
> Companion to `canonical_output.schema.json` and `authority/field_rules.yaml`.

This document maps each **source**'s native fields onto the MR-KEP **canonical
fields**. It is declarative planning — no parser is written. Each source is
tagged with its P63 `source_class` + Sprint-1 `authority_tier`; a source may only
map fields its authority tier is allowed to certify (see `field_rules.yaml`
ceilings). Fields a source cannot provide are `— (n/a)` and resolve to `null`.

## Source → class/tier registry

| Source | source_name | source_class | authority_tier |
|--------|-------------|--------------|----------------|
| Official (producer/distillery) | producer_technical_sheet | official | T1_authoritative |
| WhiskyFun | whiskyfun | expert_review | T2_expert |
| Whisky Advocate | whisky_advocate | expert_review | T2_expert |
| Whiskybase | whiskybase | structured_metadata | T2_expert |
| Books (reference) | reference_book | book | T2_expert |

*`whisky_advocate`, `whiskybase`, `reference_book` are **proposed** authority
source_keys (recorded in `resolution/source_resolution_model.yaml →
proposed_authority_additions` for the first two classes; book already proposed).
P65 does not edit the authority layer.*

## Canonical field mapping matrix

Legend: ✔ = source can provide + certify (within its ceiling); ○ = can provide as
below-ceiling PROPOSAL/corroboration only (not sole certifier); — = n/a → null.

| Canonical field | Category (ceiling) | Official (T1) | WhiskyFun (T2) | Whisky Advocate (T2) | Whiskybase (T2) | Books (T2) |
|-----------------|--------------------|:---:|:---:|:---:|:---:|:---:|
| distillery_name | identity (T1) | ✔ | ○ | ○ | ○ | ○ |
| region | identity (T1) | ✔ | ○ | ○ | ○ | ○ |
| country | identity (T1) | ✔ | ○ | ○ | ○ | ○ |
| abv | official_bottling (T1) | ✔ | ○ | ○ | ○ | ○ |
| age_statement | official_bottling (T1) | ✔ | ○ | ○ | ○ | ○ |
| cask_type | official_bottling (T1) | ✔ | ○ | ○ | ○ | ○ |
| nose | sensory (T2) | — | ✔ | ✔ | — | ✔ |
| palate | sensory (T2) | — | ✔ | ✔ | — | ✔ |
| finish | sensory (T2) | — | ✔ | ✔ | — | ✔ |
| flavor_axes | sensory (T2) | — | ✔ | ✔ | ○ | ✔ |
| score | scored_assessment (T2) | — | ✔ | ✔ | ○ | ○ |
| community_rating | supporting (T3) | — | — | — | ✔ | — |

Notes:
- **Official never certifies flavor/score** (T1 forbidden from `subjective_flavor`).
- **○ (below-ceiling)** entries are PROPOSED_NEEDS_CERT (P63 path C): retained as
  evidence, penalized, never sole certifier of a T1 field.
- **Whiskybase** as `structured_metadata` corroborates official_bottling and may
  provide `community_rating` (its user ratings) as T3-equivalent supporting data.

## Per-source native → canonical notes (declarative)

### Official
- Native: technical sheet / product page fields.
- ABV native like `46% vol` → canonical `abv=46.0` via `strip_percent_cast_real`.
- Age like `Aged 12 Years` → `age_statement=12` via `extract_first_integer_year`.

### WhiskyFun (expert_review, T2)
- Native: review body with Nose/Palate/Finish prose + a score.
- Score is on a /100-style scale → canonical `score` (0–100). Nose/Palate/Finish
  → raw text canonical fields; flavor_axes derived only into the 7 canonical axes.

### Whisky Advocate (expert_review, T2)
- Native: structured review + 0–100 rating.
- Rating → `score`; review sections → nose/palate/finish; category prose →
  flavor_axes (7 canonical axes only).

### Whiskybase (structured_metadata, T2)
- Native: structured product record + user votes.
- Structured ABV/cask/age → corroborate official_bottling (○). User votes →
  `community_rating` (0–5). Does not certify identity.

### Books (book, T2)
- Native: printed prose; `source_url=null` → requires `source_citation`
  (title/author/page) per P64.
- Sensory prose → nose/palate/finish; historical facts may corroborate identity
  (○), especially for closed distilleries (P63 override).

## Guarantees
- Every mapped value normalizes to a canonical field key defined in the schema.
- A source never maps into a field above its authority ceiling as a certifier.
- Unmappable native fields are dropped to `null`, never coerced or invented.

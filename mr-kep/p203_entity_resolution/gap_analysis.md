# P203 — Gap Analysis

## Identity-infrastructure gaps (from audit, not speculation)
| Gap | Evidence | Impact on canonical model |
|---|---|---|
| Matcher is alias-blind | `grep alias matching.py` → none; matcher queries only `whiskies.name` | aliases never used in resolution |
| Whisky aliases unsupported | `entity_aliases.entity_type` enum = brand/bottler/company/distillery (`schema.sql:69`) | whisky identity = fuzzy name only |
| No phonetic/token matcher | grep `mr-kep` for soundex/metaphone/token_set/jaro → 0 hits | word-order / spelling variants unhandled |
| Only whisky matched | `matching.py` loads `whiskies` only | distillery/brand/bottler have no resolver |
| Crosswalk deferred | `p137a` D5: not loaded into knowledge.db | book UUID→W bridge absent |
| Crosswalk weak | `p129`: 475 weak / 0 exact / 4 strong-but-mismatch | cannot auto-activate |
| No `alias_class` | `entity_aliases` has only `alias_name` | cannot weight official > community |
| No Series/Edition entity | neither DB models them | expression naming inconsistency unmodeled |

## Data-coverage gaps (from `mr-kep/p143_release_readiness/remaining_gaps.md`)
Field completion (verbatim from p143):
- `distillery_id` **59.34%** (needs distillery resolution / crosswalk, deferred D5)
- `country` **2.84%** (only 135 present; needs external source / manual review)
- `region` **19.94%** (improved +530 via P142; remaining 3802 NULL need external/LLM)
- `brand` **39.36%** (needs external)
- `abv` **46.03%** (707 high-conf candidates exist, not yet promoted)
- `age` **34.32%** (724 high-conf candidates exist, not yet promoted)
- `original_name` **28.91%**, `type` **39.1%**, `age_statement` **26.03%**, `nas` **3.12%**
- `cask_type` **14.34%**, `finish_type` **0.0%**, `cask_strength` **0.0%**,
  `meta_critic_score` **27.67%**, `user_score` **0.0%**
- Threshold summary: <25%: 10 fields; 25–50%: 8 fields; 50–75%: 1 field; ≥90%: 2 fields
  (`name`, `whisky_id`).

## Risk if gaps ignored
Auto-merging on the current alias-blind, whisky-only, fuzzy-only matcher would:
- mis-resolve "BenRiach"/"Benriach", "GlenDronach"/"Glendronach", "Glenlivet"/"The Glenlivet";
- inject the P129 weak/expression-mismatch crosswalk rows into production (AGENTS.md risk);
- leave distillery_id/country/region largely unresolved, breaking region/owner joins.

## Mitigation (design)
All gaps are closed in the implementation plan (alias enum extension, alias_class,
multi-entity + phonetic/token matcher, gated crosswalk, Series/Edition tables, coverage
promotion via P139 harness). None require reinventing existing tables.

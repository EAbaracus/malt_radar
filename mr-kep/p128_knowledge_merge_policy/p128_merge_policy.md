# P128 — Knowledge Merge Policy (READ-ONLY)

Defines **exactly** how book-extracted knowledge (P125→P127 MERGE/CREATE/AMBIGUOUS candidates)
updates existing entities. Grounded in the real `production.db` schema (see `field_merge_matrix.md`)
and `AGENTS.md` authority. **This is a policy specification only — no staging, no production writes, no promotion.**

## Global principles (from AGENTS.md)
1. **Evidence required** — every field change carries a citation row in `official_source_references`.
2. **Backup → inspect → apply → verify** before any future DB modification (this doc is design-only).
3. **Price never merged, never exposed** — book merge never touches `production_price` / `price_history`.
4. **Low confidence → stop & review** — routed to `staging_manual_review_queue`, never auto-applied.

## Confidence thresholds (global)
| Band | Range | Default action |
|---|---|---|
| HIGH | ≥ 0.90 | auto-apply to REPLACEABLE fields; append to APPEND-ONLY |
| MEDIUM | 0.70–0.89 | append-only + citation; REPLACEABLE → review |
| LOW | 0.50–0.69 | review-required (staging queue) |
| REJECT | < 0.50 | discard from promotion (AMBIGUOUS bucket) |

Source authority tiers (incumbent vs incoming): **Official source > Reference book (Yearbook/Atlas/Jackson) > General book > Periodical (Advocate/Magazine)**. Overwrite only allowed when incoming authority ≥ incumbent authority AND incoming confidence ≥ threshold.

---

## 1. Distillery
- **merge:** enrich empty fields (region, country, location, founded_year) from HIGH-confidence book evidence.
- **overwrite:** only `country/region/location/coordinates/official_website` at conf ≥ 0.90 + authority ≥ incumbent.
- **append:** `notes_for_review`, `wikidata_id`/`wikipedia_url` (if empty), alias rows.
- **citation:** one `official_source_references` row per field set (entity_type='distillery').
- **conflict:** founder/founded_year/owner/status/parent_company → REVIEW (temporal/legal).
- **threshold:** create new distillery only if resolver CREATE + conf ≥ 0.70 + not blocked-matched.

## 2. Whisky
- **merge:** fill empty `age_statement, nas, bottle_size, cask_type, finish_type` from HIGH evidence.
- **overwrite:** `bottle_size, cask_strength, nas` at conf ≥ 0.90; `meta_critic_score` recomputed.
- **append:** `cask_type, finish_type` (multi-cask legitimate), `notes_for_review`.
- **citation:** per field (entity_type='whisky').
- **conflict:** `age`/`abv`/`type`/`name`/`distillery_id`/`brand` → REVIEW (see conflict_resolution_rules.md).
- **threshold:** never overwrite `user_score` (user-sourced, IMMUTABLE).

## 3. Expression (whisky variant = row in whiskies keyed by name+age+abv+cask)
- **merge:** treated as a distinct whisky row; expression-level attributes (age/abv/cask/finish) define identity.
- **overwrite:** none on identity fields — a differing age/abv means a **new expression**, not an overwrite.
- **append:** attach tasting_notes + flavor evidence to the matched expression row.
- **citation:** per expression (entity_type='whisky', field=expression attrs).
- **conflict:** same name, different age/abv from two books → create two expressions, flag as related in review.
- **threshold:** CREATE new expression if no blocked fuzzy match ≥ 0.85 on (name+age+abv).

## 4. Brand
- **merge:** enrich `description` (append-only w/ citation).
- **overwrite:** none — `brand_name` REVIEW-REQUIRED.
- **append:** `description`, alias rows.
- **citation:** entity_type='brand'.
- **conflict:** brand↔distillery ambiguity (from P127 alias stage) → REVIEW.
- **threshold:** CREATE brand only if resolver CREATE + conf ≥ 0.70 + no fuzzy match in brands.

## 5. Bottler
- **merge:** enrich `country` at conf ≥ 0.85.
- **overwrite:** `country` only, conf ≥ 0.85.
- **append:** alias rows; `bottler_product_links` associations (review-gated).
- **citation:** entity_type='bottler'.
- **conflict:** independent-bottler vs OB confusion → REVIEW.
- **threshold:** CREATE bottler if context matches BOTTLER_RE (Cadenhead/Signatory/G&M/…) + conf ≥ 0.70.

## 6. Flavor Profile
- **merge:** `flavor_tags`, `flavor_source` append-only; each descriptor cites its book.
- **overwrite:** `flavor_vector`/`flavor_profile` REVIEW-REQUIRED — **only via knowledge.db consensus** (`consensus_nodes`→`canonical_vectors`), never direct book write.
- **append:** `flavor_tags`, `notes_for_review`; increment `source_count`/`evidence_count`.
- **citation:** `flavor_evidence` + `official_source_references`.
- **conflict:** divergent 7-axis vectors across books → consensus algorithm arbitrates, not last-writer.
- **threshold:** vector update requires ≥ 2 corroborating sources OR conf ≥ 0.90 single authority.
- **PRICE:** `production_price` IMMUTABLE — never merged.

## 7. Tasting Notes
- **merge:** each book note = a **new append row** (nose/palate/finish), never overwrite existing.
- **overwrite:** none — tasting notes are additive evidence.
- **append:** `nose_notes, palate_notes, finish_notes, aroma_tags`; provenance in `source_doc`/`source_entry_number`.
- **citation:** provenance columns are IMMUTABLE at insert; book SHA in `source_doc`.
- **conflict:** contradictory notes coexist (subjective) — no resolution needed; both retained.
- **threshold:** attach if whisky match conf ≥ 0.85; else route to review.

## 8. Production Facts (glossary/production terminology → knowledge_glossary_terms, knowledge_guides)
- **merge:** append new terminology; enrich definitions.
- **overwrite:** definition REPLACEABLE at conf ≥ 0.90 + authority.
- **append:** new terms, examples.
- **citation:** source book per term.
- **conflict:** competing definitions → keep both w/ source attribution, flag if contradictory.
- **threshold:** CREATE term if not present + conf ≥ 0.70.

## 9. Historical Facts (founded_year, founder, ownership timeline, region history)
- **merge:** NONE automatic — all historical facts REVIEW-REQUIRED.
- **overwrite:** never auto; human-gated.
- **append:** `notes_for_review` + `knowledge_regions.description/characteristics`.
- **citation:** mandatory; conflicting dates across books logged in `review_conflict_log`.
- **conflict:** multi-source date disagreement → present all candidates to reviewer, no auto-pick.
- **threshold:** always review regardless of confidence (temporal sensitivity).

## 10. Awards (no dedicated table — stored as notes/references)
- **merge:** append to `notes_for_review` + `official_source_references` (field_name='award').
- **overwrite:** none — awards are point-in-time facts.
- **append:** each award = citation row (award name, year, body, source book).
- **citation:** mandatory (award body + year + book).
- **conflict:** duplicate award mentions deduped on (whisky, award, year).
- **threshold:** attach if whisky/distillery match conf ≥ 0.85.

## 11. Aliases (entity_aliases)
- **merge:** append new alias if not present for (entity_type, entity_id).
- **overwrite:** never — aliases only accumulate.
- **append:** `alias_name`; dedupe on (entity_type, entity_id, alias_name).
- **citation:** source book recorded via official_source_references.
- **conflict:** same alias → two entities = REVIEW (identity collision, from P127 ambiguous bucket).
- **threshold:** add alias if resolver MERGE surface ≠ canonical name + conf ≥ 0.85.

---

## Candidate-bucket → policy routing (from P127)
| P127 bucket | Count | Policy path |
|---|---|---|
| MERGE (16,725) | matched existing | enrich per entity rules; APPEND/REPLACEABLE only; citation mandatory |
| CREATE (10,829 +536 B4b) | new entity | CREATE gated by conf ≥ 0.70 + review for distillery/brand/bottler |
| AMBIGUOUS (3,556) | uncertain | 100% REVIEW-REQUIRED → staging_manual_review_queue |

See `promotion_contract.md` for the promotion gate and `conflict_resolution_rules.md` for arbitration.

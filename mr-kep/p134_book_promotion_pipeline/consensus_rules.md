# P134 — Consensus Rules (READ-ONLY Design)

- doc_version: P134-1
- deterministic field-level precedence. Superset of P128 merge_policy §1–11 + conflict_resolution_rules.
- "incumbent" = current production.db value; "incoming" = book-extracted candidate.

## Global precedence order (authority tiers)
`T1 Official > T2 Reference (Yearbook/Atlas/Jackson) > T3 General book > T4 Periodical`
Overwrite allowed only when `incoming_tier ≤ incumbent_tier` (i.e. ≥ authority) AND `conf ≥ field threshold`.

## Per-field consensus
| field | rule | class |
|---|---|---|
| abv | within ±0.1% → keep incumbent + cite corroboration; beyond → REVIEW | REVIEW-REQUIRED |
| age | any mismatch → treat as **distinct expression** (new whiskies row), never overwrite | REVIEW-REQUIRED |
| age_statement / nas | fill if empty (HIGH); REPLACEABLE at conf≥0.90 | optional |
| cask_type | APPEND (multi-cask legitimate); dedupe | APPEND-ONLY |
| finish_type | APPEND | APPEND-ONLY |
| bottle_size | REPLACEABLE conf≥0.85 | optional |
| cask_strength | REPLACEABLE conf≥0.90 | optional |
| country | REPLACEABLE conf≥0.90 + authority≥incumbent | optional |
| region | REPLACEABLE conf≥0.90; cross-check knowledge_regions | optional |
| name | REVIEW-REQUIRED (canonical) | review |
| distillery_id | REVIEW-REQUIRED (FK) | review |
| brand | REVIEW-REQUIRED | review |
| type | REVIEW-REQUIRED | review |
| founded_year / owner / status / parent_company | REVIEW-REQUIRED (historical/temporal) | review |
| tasting_notes (nose/palate/finish) | APPEND per book (no conflict; subjective) | APPEND-ONLY |
| flavor_tags | APPEND; dedupe on (whisky, tag) | APPEND-ONLY |
| flavor_vector (7-axis) | **consensus via knowledge.db** (`consensus_nodes`→`canonical_vectors`); never direct book write. Requires ≥2 corroborating sources OR single T2 conf≥0.90 | REVIEW-REQUIRED |
| notes_for_review | APPEND (citation text) | APPEND-ONLY |
| wikidata_id / wikipedia_url | APPEND if empty | APPEND-ONLY |
| data_confidence / completed_fields | recomputed (max of sources) | REPLACEABLE |
| production_price / price_history | **NEVER** (firewall) | unsupported |

## Flavor vector semantic consensus (knowledge.db)
- Each book vector → `evidence_nodes` → `extracted_facts` → `consensus_nodes`.
- `canonical_vectors` derived by consensus algorithm (mean/median of corroborating evidence, weighted by authority×confidence).
- Axis set alignment: sources use `rich` (NotebookLM/staging) but `canonical_vectors` uses `maritime` → **normalization maps `rich→maritime` equivalence is INVALID**; they are distinct axes. Pipeline must map source `rich` to a `rich` slot and align to the 7 canonical axes (smoky,peaty,fruity,sweet,spicy,maritime,sherry) — `rich` is NOT one of them. Decision: treat `rich` as a derived 8th descriptor, or drop to the 7 canonical; document in normalization_rules.md.

## Numeric conflict arbitration (from conflict_resolution_rules)
- abv ±0.1 tolerance; age exact; founded_year exact→REVIEW; coordinates ~0.01°.
- Tie-break: (1) more recent edition for temporal facts; (2) more specific source for domain facts; (3) else REVIEW.

## Identity consensus (crosswalk)
- Book whisky_name+age+abv+cask → lookup in `whiskies` (fuzzy ≥0.85 on name+age+abv). Match → MERGE; no match → CREATE (conf≥0.70); ambiguous → REVIEW.
- SMWS cask_no → `flavor_evidence.smws_code` → existing `whisky_id` (UUID or W). If UUID→W bridge needed, use P129 crosswalk (currently weak-only; see B2).

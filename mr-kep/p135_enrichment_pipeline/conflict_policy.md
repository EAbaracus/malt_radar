# P135 — Conflict Policy (READ-ONLY Plan)

- doc_version: P135-1
- field-level priority order + rationale. Superset of P128 conflict_resolution_rules + P134 consensus_rules.

## Global priority order (highest → lowest authority)
```
SMWS (T3, structured, extraction_conf=1.0)
  > Books / Reference (T2: Yearbook/Atlas/Jackson)
  > Books / General (T3: Whiskypedia/Broom)
  > NotebookLM (T3, LLM-derived)
  > Community / Web (staging_tasting_notes, staging_web_tasting_notes)
  > Legacy production (incumbent, lowest authority for overwrite)
```
**Why this order:**
1. **SMWS first** — it is the most structured, highest-confidence source (extraction_conf=1.0, parser_conf=1.0, deterministic cask# join). It is "official-ish" society archive data with exact ABV/age/cask on the bottle label. Lowest hallucination risk.
2. **Reference books (T2) next** — curated, fact-checked, high authority for region/country/historical facts.
3. **General books (T3)** — broader but less rigorous.
4. **NotebookLM** — convenient LLM summary, useful for vectors/notes but lower authority than primary books (LLM may confabulate).
5. **Community/Web** — user/submitted; lowest structured authority.
6. **Legacy incumbent** — never "wins" an overwrite by authority; it is the baseline. Incoming may overwrite it ONLY if incoming authority ≥ incumbent AND conf ≥ threshold (P128 §global).

## Per-field priority & action
| field | winner rule | class | action |
|---|---|---|---|
| cask_type | SMWS (if present) else book | APPEND-ONLY | accumulate |
| age | SMWS/book exact; mismatch→distinct expression | REVIEW | never overwrite |
| abv | SMWS (label-exact) ±0.1 vs incumbent | REVIEW | keep incumbent if within tol |
| region | SMWS or Reference book | REPLACEABLE ≥0.90 | apply if authority≥incumbent |
| country | Reference book | REPLACEABLE ≥0.90 | apply |
| type | book + SMWS agree | REVIEW | human if conflict |
| brand | book | REVIEW | human |
| tasting_notes | ALL sources APPEND (no winner) | APPEND-ONLY | retain all |
| flavor_vector | consensus (knowledge.db), NOT any single source | REVIEW | via consensus only |
| flavor_tags | ALL append | APPEND-ONLY | dedupe |
| notes_for_review | ALL append | APPEND-ONLY | accumulate |
| meta_critic_score | recomputed aggregate | REPLACEABLE | recompute |
| founded_year/owner/status | human only | REVIEW | never auto |
| price | NONE (firewall) | unsupported | never |

## Tie-break (P128 §5)
1. More recent edition wins (temporal facts).
2. More specific source wins (domain facts).
3. Else REVIEW.

## Authority × confidence gate
- Overwrite REPLACEABLE only if `incoming_tier ≤ incumbent_tier` AND `conf ≥ field_threshold`.
- SMWS (T3) cannot overwrite a T2 incumbent on region even at conf 1.0 — but SMWS region is usually corroborating, not conflicting.

## Non-negotiables
- Price: never in conflict flow.
- user_score: never overwritten.
- IMMUTABLE fields (whisky_id, original_name, name, distillery_id reassignment): cite-only or REVIEW.
- Every applied change: mandatory citation (C1).

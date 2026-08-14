# P143 — Production Census (Phase 1)

- doc_version: P143-1  - date_utc: 2026-07-17  - mode: READ-ONLY
- table: whiskies  - rows: 4749
- NOTE: schema has 21 columns. 14 fields requested by the spec do NOT exist in the schema: subtitle, distillery, category, bottler, series, vintage, cask_number, bottle_count, release_year, image, description, tasting_notes, flavour_profile, flavour_vector.
  Those are reported as ABSENT (not measurable). No speculation about their values.

| column | populated | null/empty | completion % | usefulness |
|---|---|---|---|---|
| whisky_id | 4749 | 0 | 100.0% | N/A (complete) |
| name | 4749 | 0 | 100.0% | N/A (complete) |
| original_name | 1373 | 3376 | 28.91% | LOW (no known high-conf source; needs external/LLM/OCR) |
| distillery_id | 2818 | 1931 | 59.34% | LOW (no known high-conf source; needs external/LLM/OCR) |
| country | 135 | 4614 | 2.84% | LOW (no known high-conf source; needs external/LLM/OCR) |
| region | 947 | 3802 | 19.94% | HIGH (high-conf source in knowledge.db) |
| type | 1857 | 2892 | 39.1% | LOW (no known high-conf source; needs external/LLM/OCR) |
| age | 1630 | 3119 | 34.32% | HIGH (high-conf source in knowledge.db) |
| age_statement | 1236 | 3513 | 26.03% | LOW (no known high-conf source; needs external/LLM/OCR) |
| nas | 148 | 4601 | 3.12% | LOW (no known high-conf source; needs external/LLM/OCR) |
| abv | 2186 | 2563 | 46.03% | HIGH (high-conf source in knowledge.db) |
| bottle_size | 39 | 4710 | 0.82% | LOW (no known high-conf source; needs external/LLM/OCR) |
| cask_type | 681 | 4068 | 14.34% | HIGH (high-conf source in knowledge.db) |
| finish_type | 0 | 4749 | 0.0% | LOW (no known high-conf source; needs external/LLM/OCR) |
| cask_strength | 0 | 4749 | 0.0% | LOW (no known high-conf source; needs external/LLM/OCR) |
| meta_critic_score | 1314 | 3435 | 27.67% | LOW (no known high-conf source; needs external/LLM/OCR) |
| user_score | 0 | 4749 | 0.0% | LOW (no known high-conf source; needs external/LLM/OCR) |
| data_confidence | 1728 | 3021 | 36.39% | LOW (no known high-conf source; needs external/LLM/OCR) |
| completed_fields | 0 | 4749 | 0.0% | LOW (no known high-conf source; needs external/LLM/OCR) |
| notes_for_review | 0 | 4749 | 0.0% | LOW (no known high-conf source; needs external/LLM/OCR) |
| brand | 1869 | 2880 | 39.36% | LOW (no known high-conf source; needs external/LLM/OCR) |

## Schema discrepancy (evidence)
The spec requested 23 fields. Actual `whiskies` has 21 columns. Missing (ABSENT from schema):
subtitle, distillery, category, bottler, series, vintage, cask_number, bottle_count, release_year, image, description, tasting_notes, flavour_profile, flavour_vector.
These cannot be measured; their absence is itself a release-risk finding (see risk_assessment.md).

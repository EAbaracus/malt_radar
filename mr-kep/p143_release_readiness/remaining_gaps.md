# P143 — Remaining Gaps (Phase 3)

| Field | completion % | tier | why not filled |
|---|---|---|---|
| original_name | 28.91% | 25-50% | 28.91% — partial; no pending promotion. Existing books asset may help (needs extraction). |
| distillery_id | 59.34% | 50-75% | 59.34% — FK to distillery; remaining need distillery resolution (crosswalk, deferred per D5). |
| country | 2.84% | <25% | Only 135 present; no high-conf source in knowledge.db; needs external source / manual review. |
| region | 19.94% | <25% | 19.94% — improved +530 via P142; remaining 3802 NULL have no SMWS source (outside P137B scope). Needs external/LLM. |
| type | 39.1% | 25-50% | 39.1% — no pending promotion. Needs external/source mapping. |
| age | 34.32% | 25-50% | 34.32% — 724 high-conf candidates EXIST in knowledge.db but NOT yet promoted. Automation: LOW (reuse P139 harness). |
| age_statement | 26.03% | 25-50% | 26.03% — unchanged; no pending promotion. Needs external source / LLM extraction. |
| nas | 3.12% | <25% | 3.12% — sparse; needs source. |
| abv | 46.03% | 25-50% | 46.03% — 707 high-conf candidates EXIST in knowledge.db but NOT yet promoted. Automation: LOW (reuse P139 harness). |
| bottle_size | 0.82% | <25% | 0.82% — almost empty; needs source. |
| cask_type | 14.34% | <25% | 14.34% — 627 filled via P139; remaining 4068 NULL have no high-conf source. Needs external. |
| finish_type | 0.0% | <25% | 0% — 100% NULL. No source in knowledge.db. Needs external/LLM. |
| cask_strength | 0.0% | <25% | 0% — 100% NULL. No source. Needs external. |
| meta_critic_score | 27.67% | 25-50% | 27.67% — external ratings source needed (MetaCritic). Not in local assets. |
| user_score | 0.0% | <25% | 0% — 100% NULL. Requires user-generated data (post-launch). |
| data_confidence | 36.39% | 25-50% | 36.39% — computed field; depends on other fields. |
| completed_fields | 0.0% | <25% | 0% — 100% NULL. Computed/derived; populate at read time, not storage. |
| notes_for_review | 0.0% | <25% | 0% — 100% NULL. Internal QA field; not user-facing. |
| brand | 39.36% | 25-50% | 39.36% — no pending promotion. Needs external. |

## Threshold summary
- <25%: 10 fields
- 25-50%: 8 fields
- 50-75%: 1 fields
- 75-90%: 0 fields
- >=90%: 2 fields (name, whisky_id)

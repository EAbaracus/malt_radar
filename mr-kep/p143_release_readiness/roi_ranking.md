# P143 — ROI Ranking (Phase 6)

Ranked by: production value x coverage increase x automation feasibility x evidence quality.

| Rank | Opportunity | Coverage gain | Automation | Evidence | Score |
|---|---|---|---|---|---|
| 1 | Promote abv (707 high-conf pending) | 46%->61% (+707) | LOW (P139 harness) | HIGH (source_id=smws, conf 0.95) | 9.2 |
| 2 | Promote age (724 high-conf pending) | 34%->49% (+724) | LOW (P139 harness) | HIGH (source_id=smws, conf 0.95) | 9.0 |
| 3 | Review Queue triage (1431 rows) | variable | MEDIUM (manual/LLM) | MEDIUM (conflicts flagged) | 6.5 |
| 4 | distillery_id resolution (crosswalk, D5 deferred) | 59%->? | MEDIUM | MEDIUM (P129 weak matches only) | 5.5 |
| 5 | country enrichment (external source) | 2.84%->? | HIGH (needs source) | LOW (no local source) | 3.0 |
| 6 | Schema extension for tasting_notes/flavour | new columns | HIGH (migration) | MEDIUM (assets exist) | 4.0 |
| 7 | finish_type / cask_strength (external) | 0%->? | HIGH (no source) | LOW | 2.0 |

## Recommended roadmap
1. P144: promote abv + age from existing knowledge.db pool (LOW effort, HIGH evidence, +1,431 fields).
2. P145: triage review_queue (1,431) for medium-confidence promotes.
3. P146: resolve distillery_id via crosswalk (D5).
4. Later: schema extension + external sourcing for text/flavour/country.

# P135 — Field-by-Field Enrichment Map (READ-ONLY Plan)

- doc_version: P135-1
- date_utc: 2026-07-16
- mode: PLAN ONLY; zero DB writes. Grounded in real completion rates measured this session.
- baseline: production.db `whiskies` (4,749 rows), `flavor_profiles` (3,467), `tasting_notes` (1,848).
- context: entity resolution COMPLETE; UUIDs canonical; identity ignored. Focus = metadata enrichment only.

## Measurement method
Completion = `COUNT(col IS NOT NULL AND TRIM(col)<>'') / total`. Source availability = non-null in staging asset joined to `whiskies`.

---

## A. whiskies technical / identity-supporting fields
| field | current | target | source of truth | confidence | automation | expected gain |
|---|---|---|---|---|---|---|
| cask_type | 1.1% (54) | 55% | **SMWS staging** (81.3% populated) | HIGH | FULL | +54% pts (~2,550 rows) |
| age | 34.3% (1,630) | 60% | SMWS staging (99%) + books | HIGH | FULL | +26% pts |
| abv | 46.0% (2,186) | 70% | SMWS staging (96.6%) | HIGH | FULL | +24% pts |
| age_statement | 26.0% (1,236) | 50% | SMWS + books | HIGH | FULL | +24% pts |
| nas | 3.1% (148) | 20% | books/SMWS keyword | MED | SEMI | +17% pts |
| bottle_size | 0.8% (39) | 15% | books (rare) | MED | SEMI | +14% pts |
| cask_strength | 0.0% (0) | 10% | SMWS (boolean) | MED | SEMI | +10% pts |
| region | 8.8% (416) | 35% | SMWS (79.5%) + books | HIGH | FULL | +26% pts |
| country | 2.8% (135) | 25% | knowledge_regions map | MED | SEMI | +22% pts |
| type | 39.1% (1,857) | 55% | books + SMWS | MED | SEMI | +16% pts |
| brand | 39.4% (1,869) | 50% | books | MED | SEMI | +11% pts |
| distillery_id | 59.3% (2,818) | 59% (no change*) | — | — | — | 0 (identity; out of scope) |
| meta_critic_score | 27.7% (1,314) | 40% | books (reviews) | MED | SEMI | +12% pts |
| data_confidence | 36.4% (1,728) | 60% | recomputed | HIGH | FULL | +24% pts |
| completed_fields | 0.0% (0) | 100% | recomputed | HIGH | FULL | +100% pts |
| notes_for_review | 0.0% (0) | 80% | appended citations | HIGH | FULL | +80% pts |
| original_name | 28.9% (1,373) | 28.9% | IMMUTABLE | — | — | 0 (do not touch) |
| user_score | 0.0% | 0% | IMMUTABLE (user) | — | — | 0 (never book-write) |
| finish_type | 0.0% | 20% | books (APPEND) | MED | SEMI | +20% pts |
| name | 100% | 100% | REVIEW-REQUIRED | — | — | 0 |

\* distillery_id is identity — excluded per task scope.

## B. flavor_profiles
| field | current | target | source | confidence | automation | gain |
|---|---|---|---|---|---|---|
| production_region | 8.8% (305) | 30% | SMWS/books | MED | SEMI | +21% pts |
| flavor_tags | 99.9% | 100% | books append | HIGH | FULL | +0.1% (maintain) |
| flavor_source | 99.9% | 100% | append | HIGH | FULL | maintain |
| notes_for_review | 69.9% | 95% | citations | HIGH | FULL | +25% pts |
| production_price | 40.7% | 40.7% | **FIREWALL** (never book-write) | — | — | 0 |
| production_rating | 48.9% | 48.9% | recompute only | — | — | 0 |
| flavor_vector | 100% | 100% | consensus (P134 §4) | HIGH | GATED | maintain |
| flavor_profile | 99.9% | 100% | derived | HIGH | FULL | +0.1% |

## C. tasting_notes (asymmetric gap!)
| field | current | target | source | confidence | automation | gain |
|---|---|---|---|---|---|---|
| nose_notes | 7.2% (133) | 60% | SMWS (verbatim) + books | HIGH | FULL | +53% pts |
| finish_notes | 7.3% (134) | 60% | SMWS + books | HIGH | FULL | +53% pts |
| palate_notes | 99.9% | 100% | maintain | — | — | 0 |
| aroma_tags | 0.0% (0) | 40% | books (REAL→TEXT fix) | MED | SEMI | +40% pts |

## D. Highest-ROI summary (top gains)
1. **cask_type**: +54 pts (SMWS, FULL)
2. **nose_notes / finish_notes**: +53 pts each (SMWS/books, FULL)
3. **completed_fields**: +100 pts (recompute, FULL)
4. **notes_for_review**: +80 pts (citations, FULL)
5. **region / age / abv / age_statement**: +24–26 pts (SMWS, FULL)
6. **country / type / brand / meta_critic / production_region**: +11–22 pts (books, SEMI)

## E. Realistic total after all batches
- whiskies with ≥1 enriched technical field: from current ~46% abv-baseline to ~70% blended completion.
- tasting_notes nose/finish coverage: 7% → 60%.
- No identity field touched; price never touched.

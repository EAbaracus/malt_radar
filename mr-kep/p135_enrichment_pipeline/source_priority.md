# P135 — Source Priority (READ-ONLY Plan)

- doc_version: P135-1
- grounded in real joinability + availability measured this session.

## Source inventory & measured metrics
| source | rows | joinable→whiskies | fields supplied | coverage | reliability | automation cost | conflict risk | priority |
|---|---|---|---|---|---|---|---|---|
| **SMWS staging** (`staging_smws_tasting_notes.csv` + `flavor_evidence`) | 803 + 791 | 791/791 (100%, via flavor_evidence.whisky_id) | cask_type, age, abv, region, tasting notes (nose/finish), vectors | cask_type 81%, age 99%, abv 97%, region 80% | HIGH (structured extract, extraction_conf=1.0) | LOW (regex on label) | LOW (deterministic cask#→whisky_id) | **P1** |
| **Book staging** (`staging_book_flavor_profiles`) | 2,577 (2,575 pending) | 1,803/2,577 (70%) | tasting notes summaries, 7-axis vectors, distillery_name, region, descriptors | notes 100% of joinable, vectors 100% | MED (LLM-derived) | MED (OCR+LLM) | MED (LLM hallucination) | **P2** |
| **NotebookLM** (`staging_notebooklm_flavor_profiles`) | 17 | small | 7-axis vectors, summaries | 100% of 17 | MED | LOW | LOW | **P3** (pilot) |
| **Flavor candidates full** (`staging_flavor_profile_candidates_full`) | 6,133 (harvested) | via whisky_id | 7-axis, tags, confidences | high | MED | LOW (already extracted) | MED | **P2** (vector feed) |
| **Books (raw PDF/EPUB)** | 849 files | via name lookup | everything (reference) | broad | T2/T3 | HIGH (OCR+LLM) | MED | **P2** (deep) |
| **existing CSV/JSON** (sprint outputs) | varies | n/a | evidence/facts | n/a | HIGH (curated) | LOW | LOW | **P2** (reuse) |
| **knowledge bootstrap** (`canonical_vectors` 3,077) | 3,077 | via consensus_id→W-id | consensus vectors | 100% | HIGH | LOW | LOW | **P4** (consensus target) |
| **legacy production** (`whiskies` incumbent) | 4,749 | self | incumbent values | baseline | n/a | n/a | n/a | incumbent (authority ref) |
| **staging_manual_review_queue** | 62 | n/a | conflicts | n/a | n/a | n/a | n/a | REVIEW sink |

## Priority rationale
1. **SMWS = P1** — highest completion lift per unit effort (cask_type +54 pts alone), deterministic joins (flavor_evidence.whisky_id 100% valid), HIGH confidence, LOW conflict. Best ROI.
2. **Books + flavor candidates = P2** — large tasting-note + sensory lift, but 70% joinable (30% need resolution → review), MED confidence, MED hallucination risk → SEMI automation + review gate.
3. **NotebookLM = P3** — only 17 rows; use as pipeline pilot / format validation before scaling to books.
4. **knowledge bootstrap = P4** — consensus target for vectors; not a source of row-level metadata but the derivation sink for Batch 4.
5. **Raw books = P2 deep** — re-run OCR+LLM only for fields not covered by staging (descriptions, founded_year). High cost; defer to later batch.

## Coverage note
- SMWS covers 791 whisky_ids (mostly UUID + some W). Books cover 1,803 (mostly W). **Union ≈ 2,400 distinct whisky_ids** can receive ≥1 enrichment — ~50% of 4,749.
- 30% of book staging (774 rows) not joinable → route to `staging_manual_review_queue` (P134 decision point).

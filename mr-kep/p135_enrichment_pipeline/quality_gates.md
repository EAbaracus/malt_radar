# P135 — Quality Gates (READ-ONLY Plan)

- doc_version: P135-1
- per-batch validation. All gates checked AFTER write, inside/after P121 gate.

## Gate template (every batch)
| check | method | pass criterion |
|---|---|---|
| duplicate | dedupe on (entity,field,source_hash) | 0 duplicate applied rows |
| NULL | count NULL post-write vs pre-write | no field lost (NULLs only added where source empty, never overwrite incumbent with NULL) |
| schema | `PRAGMA table_info` post-write | no column type violation; IMMUTABLE/price untouched |
| citation | count `official_source_references` new rows == applied-change count | 1:1 (C1) |
| coverage delta | completion% before vs after | ≥ expected gain (per batch) |
| confidence delta | mean field_conf of applied | ≥ band threshold per field class |

## Batch-specific gates
### B1 SMWS tech
- duplicate: cask_type append dedupe on (whisky_id, cask_type) → 0 dup
- NULL: incumbent non-null fields must NOT become null
- citation: 791 whisky_ids × fields-applied == citation rows
- coverage: cask_type 1.1%→≥55%, abv 46%→≥70%, region 8.8%→≥35%
- confidence: all applied conf ≥0.90 (SMWS HIGH)

### B2 SMWS notes
- duplicate: note hash dedupe → 0 dup
- citation: 1 row per (whisky, source_pdf, section)
- coverage: nose_notes 7.2%→≥60%, finish_notes 7.3%→≥60%
- conflict: palate already 99.9% — verify no palate overwrite (APPEND only)

### B3 books
- duplicate: (whisky_id, source_hash) dedupe
- NULL: REVIEW-required fields (age/abv/type/brand) never auto-applied if LOW conf
- citation: per field
- coverage: incremental over B1 (region→~45%, type→~47%)
- confidence: MEDIUM band → APPEND only; REPLACEABLE→review
- review sink: 774 non-joinable → `staging_manual_review_queue`

### B4 vectors
- duplicate: (whisky_id, source_hash) in evidence layer
- schema: `canonical_vectors` only changed via consensus (no direct book write)
- citation: per evidence node
- coverage: maintain 100% vector coverage; consensus count grows
- confidence: ≥2 sources OR T2≥0.90 single
- BLOCKED until D1+D2 (target knowledge.db + crosswalk)

### B5 knowledge
- duplicate: (entity, term, source_hash)
- schema: `knowledge_*` APPEND-ONLY respected
- citation: per term/guide
- coverage: brand descriptions %, glossary/guide growth
- conflict: competing definitions retained w/ attribution

### B6 recompute
- duplicate: n/a (pure function)
- schema: `completed_fields`/`data_confidence` REPLACEABLE updated only
- citation: n/a (recompute, no new field fact)
- coverage: completed_fields 0→100%
- confidence: `data_confidence` = max of sources

## Post-batch verification (P128 promotion_contract §verification)
- row counts changed as expected
- no IMMUTABLE/price field mutated (hash-compare price columns)
- citation count == applied-change count
- canonical_vectors only changed via consensus
- git status clean of tracked files
- promotion_audit_log complete

# P203 — Diagrams (ASCII, evidence-based)

All boxes map to tables/functions read in the audit. No external images.

## 1. Entity Graph
```
                         external_entities
                                | (entity_name UNIQUE)
                                v
   companies <-- distillery_company_links --> distilleries <-- distilleries.name
        ^                                     |   ^                     |
        |                                     |   |                     | entity_aliases
   brands(bottler?)                     bottler_product_links      (brand/bottler/
        ^                                     |   ^                company/distillery)
        |                                     v   |
   whiskies <-- whisky_product_entities --> bottlers
        ^                                   (owned_by/branded_as)
        |
   evidence.entity_key (knowledge.db)  -->  normalized_metadata
        |
   promotion_queue.entity_key  ---------->  production.whiskies (bridge, D5)
        |
   entity_external_links (wikipedia/official/api)
        |
   official_source_references (provenance)
```

## 2. Matching Pipeline (current → canonical)
```
  SOURCE (book/editorial/csv/smws/p300)
        |
        v
  [ normalize_text ]  <-- single canonical normalizer (matching.py + B4b OCR rules)
        |
        v
  [ candidate generation ]
     current: whiskies(name,whisky_id,age)
     canonical: + distilleries/brands/bottlers + entity_aliases + external_entities
        |
        v
  [ scoring ]  current: SequenceMatcher only
               canonical: + token_set + phonetic + alias_boost + crosswalk_strength
        |
        v
  [ confidence blend ] -> identity_confidence
        |
        v
  decision: exact | fuzzy | manual_review | unmatched
        |                |          |              |
        v                v          v              v
   auto-accept      auto-accept  review_queue   net-new entity
   (IMMUTABLE)     (REPLACEABLE) (identity)     (staging)
```

## 3. Alias Resolution Flow
```
  raw_name
     |
     v
  normalize_text
     |
     v
  LOOKUP entity_aliases WHERE alias_name = norm  (class-weighted)
     | yes                         | no
     v                            v
  canonical entity (boost)   SequenceMatcher fuzzy
     |                            |
     v                            v
  high confidence            confidence blend
                              |
              +---------------+----------------+
              v               v                v
          exact/fuzzy    manual_review     unmatched
                           (review_queue)
```

## 4. Confidence Decision Tree
```
  ratio >= 0.94 and margin >= 0.03 ?
    ├─ YES -> age match? --YES--> exact (accept)
    │                     └─NO---> manual_review
    └─ NO -> ratio >= 0.88 and margin >= 0.04 ?
              ├─ YES -> fuzzy (accept, REPLACEABLE/APPEND)
              └─ NO -> ratio >= 0.82 ?
                        ├─ YES -> manual_review (review_queue)
                        └─ NO -> unmatched (net-new candidate)
  canonical extension: add alias_boost / token / phonetic / crosswalk
  into the ratio before the tree; bands unchanged.
```

## 5. Canonical Lifecycle
```
  source
    ↓  (adapter/extractor emits raw_name + hints)
  normalize
    ↓  (normalize_text + OCR rules)
  candidate generation
    ↓  (registry + aliases + external_entities)
  scoring
    ↓  (SequenceMatcher + token + phonetic + alias + crosswalk)
  confidence blend
    ↓
  canonical entity (exact/fuzzy)  ----> promotion_queue (APPLY/APPEND)
    ↓                                      │
  manual_review / unmatched         merge_history (dedupe_key)
    ↓                                      │
  review_queue (identity/conflict)  normalized_metadata (production)
    ↓
  human resolve -> merge -> confidence ledger -> production / knowledge
```

# B4b Extraction Report -- Staging Only

**Book:** B4b -- Jim Murray, *The Complete Book of Whiskey* (1957/1998 Carlton)
**Source SHA256:** 49d1558e119fc816d50187d766f3c1da41ebccc9fd00ad395d9feb29c6a05cc3
**Output dir:** `mr-kep/book_ingestion/B4b/`
**Mode:** deterministic, local, NO LLM (Rule 08). No production.db / knowledge.db write. No promotion.

## Counts (rule-based, honest lower bound)
- **Total pages processed:** 232 (222 with extractable text, 95%)
- **Extracted entities (claims w/ source location):** 561
  - distillery mentions (resolved vs production.db): 290
  - region facts: 65
  - historical facts (founding/established): 180
  - production facts (cask/maturation): 26
- **Extracted tasting references:** 3 (claims co-occurring with nose/palate/finish/taste)
- **Extracted flavor terms (-> 7 canonical axes):** 525
- **Unresolved entities (unknown/ambiguous):** 721

## Flavor axis coverage (7 axes only -- no new axes)
- smoky: 31
- peaty: 135
- sherry: 82
- fruity: 39
- sweet: 198
- spicy: 28
- maritime: 12

## Validation
- [x] Every extracted claim carries `source_book` + `page` + `chapter` (no orphan evidence).
- [x] No canonical DB mutation (production.db read-only via gate; knowledge.db untouched).
- [x] Flavor terms mapped only to the 7 canonical axes.

## Caveats (why WARN_GO)
- Extraction is **heuristic** (substring/fuzzy), not semantic. Recall/precision are lower bounds;
  human review of staging JSONL is required before any promotion.
- "Unresolved entities" are noise-prone (capitalized tokens near whiskey context); they sit in
  `unresolved_entities.jsonl` for manual triage -- none auto-promoted.
- Numeric Jim Murray scores are **IP**; extracted only as derived axis signals, never verbatim.

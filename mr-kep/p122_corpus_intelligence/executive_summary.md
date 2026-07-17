# P122 Executive Summary — Whisky Corpus Intelligence Audit

**Mode:** READ-ONLY. Evidence: `data/books/`, `book_registry.json`, `mr-kep/book_ingestion/`, prior audit + SMWS P45–P119 staging. No DB/registry/pipeline modification.

## 1. Corpus maturity
- 44 corpus books + SMWS 906-PDF archive. 1 book (B4b) fully staged; SMWS 792 vectors staged; everything else UNEXTRACTED. Registry STALE (only B4b enriched).

## 2. Strongest domains
- Reference (18 books)
- Scotch (11 books)
- Industry (9 books)
- World Whisky (7 books)
- History (7 books)

## 3. Weakest domains
- Bourbon (1 books)
- Distillation (1 books)
- Maturation (1 books)
- Chemistry (1 books)
- Maps (1 books)

## 4. Highest-value books NOT yet ingested
- B1 Malt Whisky Yearbook (CRITICAL, factual backbone)
- B6 SMWS Archive (CRITICAL, 792 staged vectors ready)
- B5 Whisky Classified / Flavour of Whisky (HIGH, flavor-axis authority)
- Japanese Whisky (HIGH, fills world-whisky gap)

## 5. Books that can wait
- Whisky Opus, Whisky Advocate issues, Scotch Whisky annuals, intro guides — overlapping/low net-new vs canonical set.

## 6. Books providing unique knowledge
- SMWS Archive (exclusive cask notes)
- Flavour of Whisky (only quantitative flavor-science)
- Whisky Bible (largest tasting corpus)
- Aeneas MacDonald 'Whisky' (1930 primary source)
- Japanese Whisky (only JP dedicated ref)

## 7. Recommended ingestion sequence
B1 → B6 (promote staged) → B5 → B2/B3 → Japanese → B4/B4b → Whiskypedia/Aeneas → LOW tier. Rationale: uniqueness + gap-fill + evidence quality + resolver value.

## 8. Recommended acquisition sequence (only if justified)
1. Malt Whisky Yearbook 2020–2024 (extend B1)
2. The Distilleries of Scotland (foundational directory)
3. Charles MacLean — Scotch Whisky: A Liquid History
4. Scotch Whisky: From Region to Glass (Dave Broom)
5. Dave Broom — The Way of Whisky (Japanese craft)
(See book_inventory/acquisition_priority.md for Tier detail.)

## Constraints honored
- READ ONLY: production.db hash unchanged, knowledge.db untouched (3077), book_registry.json NOT modified, no commit, no extraction/classification/promotion performed.

## Final status: 🟡 WARN_GO
Audit complete and evidence-backed. WARN because registry is STALE (must be refreshed before ingestion) and several books lack identified metadata (UNKNOWN) — but all conclusions trace to files. No fabrication; scores are deterministic from known-title profiles + acquisition_plan reliability.
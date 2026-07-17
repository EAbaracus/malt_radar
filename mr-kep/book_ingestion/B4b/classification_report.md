# B4b Candidate Classification Report

**Input:** `unresolved_entities.jsonl` (721 rows)
**Method:** deterministic rule-based classifier (LLM-free, staging-only). No DB mutation.
**Output:** `candidate_classification.jsonl` (preserves original text/page/context + adds classification/confidence/reason).

## Category counts
- DISTILLERY_CANDIDATE: 536
- WHISKY_PRODUCT_CANDIDATE: 23
- COMPANY/BRAND: 0
- PERSON: 22
- AWARD/EVENT: 2
- BOOK_METADATA: 30
- GENERIC_TERM: 17
- FALSE_POSITIVE: 2
- UNKNOWN: 89

## Confidence split
- high: 278
- medium: 352
- low: 91

## Resolver impact
- **Legit entity leads (real new candidates):** 581
  - DISTILLERY_CANDIDATE + WHISKY_PRODUCT_CANDIDATE + COMPANY/BRAND are genuine net-new leads for the
    resolver to match/insert via staging (NOT noise).
- **Noise to suppress (route out of review queue):** 49
  - BOOK_METADATA (chapter/section headings) + FALSE_POSITIVE (OCR) + GENERIC_TERM (geographic phrases)
    should be auto-demoted so they never reach manual review.
- **Manual review bucket:** 91 (UNKNOWN + AWARD/EVENT) — keep in queue.

## Expected reduction in noise
- Current unresolved queue: 721
- After routing BOOK_METADATA+FALSE_POSITIVE+GENERIC_TERM to auto-suppress:
  **672 remain** (93% of original) → **noise cut by 49 rows (~6%)**.
- The resolver redesign should: (1) skip headings/metadata, (2) OCR-normalize before matching,
  (3) treat "*Distillery"/"*Distillenes" as high-confidence distillery leads.

## Caveats
- Classification is heuristic (rule precedence); spot-check before acting. PERSON may over-capture
  common given-names; DISTILLERY_CANDIDATE medium-confidence may include false leads.
- Nothing promoted; staging only.

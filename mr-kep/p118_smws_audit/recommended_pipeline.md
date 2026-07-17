# Recommended Pipeline

**Recommendation: GO for Phase 2 Extraction**

## Strategy
1. **OCR Pre-processing:** 8 documents require OCR before processing.
2. **Deduplication:** Remove the 3 exact file duplicates.
3. **LLM Extraction:** The documents are rich in unstructured tasting notes. We must reactivate the LLM Knowledge Extraction pipeline to generate `evidence_nodes` for flavour descriptors and link them to `whisky_id`s.
4. **Entity Resolution:** The SMWS `code` provides a strong anchor for deterministic matching against `production.db` (e.g. `29.302`).

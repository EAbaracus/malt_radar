# B4b Staging Data Audit — Existing-Data-Audit Rules

**Book:** B4b — Jim Murray, *The Complete Book of Whiskey* (1957/1998 Carlton)
**Audited:** 2026-07-15T21:18:15Z (read-only; no DB mutation)
**Verdict:** **WARN_GO** (heuristic rule-based extraction; human review required before promotion)

## Check Results

**15/16 checks PASS**

- [x] source_pdf_present — 35897472 bytes
- [x] source_pdf_sha256_matches_registry — live=49d1558e119fc816d50187d766f3c1da41ebccc9fd00ad395d9feb29c6a05cc3
- [x] claims_json_valid — 0 bad / 561
- [x] flavor_json_valid — 0 bad / 525
- [x] unresolved_json_valid — 0 bad / 721
- [x] classification_json_valid — 0 bad / 721
- [x] zero_orphan_evidence_claims — 0 missing loc
- [x] flavor_terms_have_provenance — 0
- [x] unresolved_have_provenance — 0
- [x] flavor_only_7_canonical_axes — escaped=[]
- [ ] no_spurious_distillery_mention — 2 single-char OCR fragments: ['T', 'W']
- [x] classification_rowcount_matches_unresolved — cls=721 unres=721
- [x] classification_preserves_original — 0
- [x] classifier_precedence_pitfall_fixed — {'The Glenfiddich Award': 'AWARD/EVENT', 'La Salle Distillery': 'DISTILLERY_CANDIDATE', 'Jim Murray': 'PERSON'}
- [x] production_db_unchanged — live=d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961
- [x] knowledge_db_canonical_vectors_unchanged — live=3077

## Staged Data Profile

- extracted_claims.jsonl: **561** rows (distillery_mention=290, region_fact=65, historical_fact=180, production_fact=26, tasting_refs=3)
- extracted_flavor_terms.jsonl: **525** rows
- unresolved_entities.jsonl: **721** → candidate_classification.jsonl: **721**
- Flavor axis histogram (7 canonical): fruity=39, maritime=12, peaty=135, sherry=82, smoky=31, spicy=28, sweet=198

## Classification breakdown

- DISTILLERY_CANDIDATE: 536
- WHISKY_PRODUCT_CANDIDATE: 23
- COMPANY/BRAND: 0
- PERSON: 22
- AWARD/EVENT: 2
- BOOK_METADATA: 30
- GENERIC_TERM: 17
- FALSE_POSITIVE: 2
- UNKNOWN: 89

## Data-Quality Observations (caveats, not blockers)

- **Spurious distillery_mention entities:** 2 single-char OCR fragments (['T', 'W'] on page 1) — genuine but negligible noise (~0.7% of distillery_mentions); should be dropped before promotion.
- 58 all-caps distillery names (GLEN SCOTIA, CLYNELISH, YAMAZAKI, ...) are REAL entities captured via uppercase section lists — NOT noise (an earlier broad all-caps filter was a verifier self-bug and has been corrected).
- Chapter headings are OCR-garbled in places (e.g. "the World lo the Whiskeys" = "the World of the Whiskies"); chapter provenance remains usable.
- One flavor token is an OCR artifact mapped correctly via FLAVOR_MAP: "oIoROS" (intended 'oloroso')→sherry.
- Unresolved queue is noise-prone by design; 721 rows are triage candidates, not promoted facts.

## Orphan / Mutation Proof

- production.db SHA256 = `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` (baseline `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961`) → **unchanged**.
- knowledge.db canonical_vectors = 3077 (baseline 3077) → **unchanged**.
- source PDF SHA256 = `49d1558e119fc816d50187d766f3c1da41ebccc9fd00ad395d9feb29c6a05cc3` matches registry claim → provenance intact.

## Conclusion

Staged B4b extraction is internally consistent, fully provenanced (zero orphan evidence), flavor-restricted to the 7 canonical axes, classifier precedence pitfall corrected, and both canonical DBs are byte-for-byte unchanged. Per the staging-only standard the verdict is **WARN_GO**: extraction is heuristic (substring/fuzzy), so precision/recall are lower bounds and the staging JSONL requires human review before any promotion gate. No promotion performed.
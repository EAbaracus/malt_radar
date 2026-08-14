# Current Phase

- **Active Phase:** P95-B (Authority Matrix Revision & Canonical Flavor Standard) — COMPLETE. Deterministic architecture phase, STRICT READ-ONLY, no promotion, no DB writes, no phase regeneration.
- **P95-B deliverables (`mr-kep/output/p95b/`, all deterministic, verified byte-identical + no DB mutation):**
  - canonical_product_policy.md (permanent MERGE/KEEP_SEPARATE/REVIEW rules)
  - authority_matrix_v2.md (T1 official / T2 expert / T3 community; unlisted→T3; highest-tier-wins; books-tier conflict documented, frozen contract wins)
  - canonical_flavor_standard.md (Axis7 over 7 frozen axes; ACCEPT axis_num/num_dict_term; CONVERT scale100 lossless, num_array len7 lossless, term-bag lossy; REJECT pca/embeddings/malformed)
  - source_weight_matrix.csv (15 sources; rule-based weights T1=1.0/T2=0.85/T3=0.55)
  - batch_classification.csv (3557 products: KEEP_SEPARATE=3471, REVIEW=49, MERGE=37)
  - promotion_rulebook.md (Authority→Format→Conflict→Confidence→Certification→Promotion→Production)
  - p95b_validation_report.md, integrity_hash.json (per-file + concat sha256)
  - **VERDICT: GO for P95-C (Canonical Flavor Conversion).**
- **7 FROZEN canonical axes (immutable, memory/decisions.md #2):** smoky, peaty, fruity, sweet, spicy, maritime, sherry.
- **P95-C (Canonical Flavor Conversion) — COMPLETE (staging-artifact-only, read-only, deterministic).** Eligible T2/core rows = 1,998; **converted = 1,611** canonical 7-axis vectors (1,345 pass-through axis7 + 266 term-bag lexicon); **rejected = 387** (PCA 225, num_array-no-axis-order 152, term-bag-none-mappable, unparseable); **excluded = 678** (all T3: book 192, ml 326, upload 153, notebooklm 2, other 5); count balance OK; no book/NotebookLM data; canonical vectors contain only the 7 frozen axes; verified byte-identical + no DB mutation.
  - Deliverables: `mr-kep/output/p95c/` (canonical_vectors.csv, unmapped_*, ambiguous_*, rejected_*, excluded_check.csv, unmapped_vocabulary.csv, validation.json, integrity_hash.json) + `docs/audit/p95c_canonical_flavor_conversion.md`.
  - **GO (conditional):** staging artifacts NOT yet written to production; a gated P35/P37-style promotion (backup+transaction+rollback+audit_log) required before any mutation. Book/NotebookLM conversion still pending **D4** (16/20→7 reducer); num_array needs an axis-order contract.
- **7 FROZEN canonical axes (immutable):** smoky, peaty, fruity, sweet, spicy, maritime, sherry.

# P403 — 04 Provenance Validation

| Field | In schema? | Populated (of 64) |
|---|---|---|
| Book (`source_book`) | yes | 64 |
| Page (`source_page_or_section`) | yes | 58 (partial) |
| Confidence (`flavor_data_confidence`) | yes | 0 (all null) |
| Author | **column absent** | — |
| Citation | **column absent** | — |
| Evidence ID | **column absent** | — |
| Authority Tier | **column absent** | — |

**Provenance complete: False.** The `staging_book_flavor_profiles` table lacks `author`/`citation`/`evidence_id`/`authority_tier` columns; `page` is 58/64 and `confidence` is 0/64. This is the sole GO condition — acceptable only if the owner authorizes promotion with book-level provenance (book title + distillery) standing in for per-row citation.

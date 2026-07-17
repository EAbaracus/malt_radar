# P134 — Implementation Plan (READ-ONLY Design)

- doc_version: P134-1
- splits build into independently testable phases. Each phase is DESIGN-COMPLETE here;
  execution deferred to an explicitly-approved promotion task through the P121 gate.

## Phase split (matches task spec + real schema)
| phase | engine | testable unit | input → output |
|---|---|---|---|
| **P135** | Extraction Engine | per-book → typed field dict + conf signals | book PDF/EPUB → `staging_*` rows with `extraction_confidence` filled |
| **P136** | Normalization Engine | field-in/field-out equality tests | raw string → canonical (abv/age/cask/axis 0-100) |
| **P137** | Consensus Engine | field-precedence unit tests | (incumbent, incoming[], tier[]) → decided value + class action |
| **P138** | Promotion Engine | dry-run diff vs production.db | staged candidates → (apply/review/reject) plan + citation rows |
| **P139** | QA | hash + count + FK + citation==change verification | post-promotion assertion suite |

## Prerequisite (blocker-clearing) sub-phases — MUST precede P138
These are NOT in the original P135–P139 list but are **mandatory** given P128/P129 findings:
- **D1** Bootstrap target `knowledge.db` (`canonical_vectors`+`citations`+`official_source_references`) — clears B1.
- **D2** Build uuid↔W crosswalk with SMWS-code backfill (P129 weak-only → strong) — clears B2.
- **D3** Generate `official_source_references` SMWS rows + attach `source_citation_id` to MERGE rows — clears B3 / C1.
- **D4** Schema fix: `aroma_tags` REAL→TEXT, drop `foo`, confirm `canonical_vectors` axis scale (P136 must read actual min/max).

## Phase detail
### P135 Extraction Engine
- Modules: `ocr/`, `chunk/`, `extract/` (regex + LLM + lookup).
- Reuses existing columns: `staging_book_flavor_profiles`, `staging_flavor_profile_candidates_full`.
- Test: golden book → assert extracted abv/age/cask_type within tolerance; assert `extraction_confidence` populated.

### P136 Normalization Engine
- Pure functions: `norm_abv`, `norm_age`, `norm_cask`, `norm_axis(scale)`, `norm_region`.
- Test: table-driven (e.g. `54.8%`→`54.8`; `12 Years`→`12`; NotebookLM 0-100 ↔ evidence 0-1 ↔ canonical); **axis scale verified against real `canonical_vectors` min/max before locking**.

### P137 Consensus Engine
- Function: `resolve(field_class, incumbent, incoming[], tiers[]) → {action, value, citation_required}`.
- Test: each row of `field_merge_matrix.md` as a unit test; conflict cases → assert REVIEW diversion.

### P138 Promotion Engine
- Dry-run mode: produces diff (entity, field, old, new, action, citation) WITHOUT writing.
- Test: replay over existing `staging_*`; assert no IMMUTABLE/price field in diff; assert citation count == apply count.
- Real write ONLY via `get_write_connection` after D1–D4 + backup + hash guard.

### P139 QA
- Assertions: production.db `integrity_check`==ok; `foreign_key_check`==empty; price columns byte-unchanged; citation count == applied-change count; `canonical_vectors` only changed via consensus; git status clean of tracked files; `promotion_audit_log` complete.

## Sequencing
```
D1 → D4(schema) → D2 → D3 → P135 → P136 → P137 → P138(dry) → P139(dry)
                                                  ↓ (human GO)
                                              P138(real, gated) → P139(real)
```

## Independence guarantee
- P135/P136/P137 are pure transforms → unit-testable with no DB.
- P138 dry-run reads production.db read-only (`get_read_connection`) → safe.
- Only P138(real) + P139(real) touch the DB, and only inside the P121 gate.

## Open decisions for user (consistent with prior phase gates)
1. `rich` axis: fold into `sweet`/`rich_body` tag, or carry as 8th descriptor? (recommend: tag)
2. Crosswalk D2: SMWS backfill on W rows — allowed, or prefer manual review of 443 MERGE overlaps?
3. Promotion order: MERGE-enrich first (per promotion_contract §optimal) — confirm.

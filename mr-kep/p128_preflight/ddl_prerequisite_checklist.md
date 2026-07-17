# DDL Prerequisite Checklist — P128 Preflight (READ-ONLY findings → required work)

> This document lists the DDL / pipeline work that MUST be completed before the P119.6b gate transaction.
> It is a **checklist of prerequisites**, NOT an executed DDL script. No schema was altered by the preflight audit.

## Legend
- [ ] = not done / blocker
- [~] = partial / needs decision
- [x] = verified present (read-only)

## D1 — Target `knowledge.db` bootstrap
- [ ] `output/import/knowledge.db` currently **0 bytes / 0 tables**. Must be created or re-targeted.
- [ ] Required table `canonical_vectors` — target schema must add:
  - `smws_code TEXT` (currently bootstrap has `vector_id,consensus_id,smoky,peaty,fruity,sweet,spicy,maritime,sherry` — **no smws_code, no rich**)
  - `rich REAL` (staging vectors carry `rich`; bootstrap `canonical_vectors` has `maritime` instead — axis mismatch)
- [ ] Required table `citations` — target schema must add:
  - `source_key TEXT`
  - `source_citation_id TEXT` (FK to `official_source_references` per P128 C1)
  - (bootstrap `citations`: `citation_id,version_id,page_number,chunk_id,raw_text,source_hash` — book-derived, no SMWS linkage)
- [ ] Required table `official_source_references` — **ABSENT** in any knowledge.db; only exists in production.db (14 cols). Must be created in target.

## D2 — `official_source_references` alignment (production.db schema, reusable shape)
- [x] Table exists in production.db (96 rows, all `official_facts` brand-website, 0 SMWS).
- [~] For SMWS USA, either reuse generic columns (`entity_type='whisky'`, `entity_id=<uuid>`, `source_name='SMWS USA'`, `field_name`, `field_value`) **or** ALTER to add `smws_code` + `source_citation_id`.
- [ ] Insert 726 (or 803) SMWS source rows — currently **0** exist → C1 unmet until done.

## D3 — Consensus-via vector load (P128 §5)
- [x] `consensus_nodes` exists in bootstrap (3,077 rows; cols `consensus_id,whisky_id,algorithm_version,status`).
- [ ] **Crosswalk MISSING:** `consensus_nodes.whisky_id` is `W####` style; MERGE `matched_whisky_id` is production UUID. Sampled UUID → 0 matches in consensus_nodes.
- [ ] Must build `production.whiskies.uuid ↔ consensus_nodes.W-id` mapping (no bridge column exists today) OR obtain explicit policy waiver to load `canonical_vectors` directly keyed by `smws_code` (forbidden by §5 without waiver).
- [ ] `canonical_vectors.consensus_id` links to `consensus_nodes.consensus_id`, not to SMWS code → any direct SMWS-keyed insert breaks the consensus FK contract.

## D4 — Promotion count split (mechanically ready, semantically gated)
- [x] 726 MERGE / 77 AMBIGUOUS / 0 CREATE split is well-defined; CSVs splittable.
- [ ] 653/726 MERGE rows have NULL `flavour_profile` → decide review-vs-default handling (AGENTS.md: route to review, never invent).
- [ ] 7 AMBIGUOUS type-D rows are genuine new-entity candidates → may become CREATE after human review; "0 CREATE" disposition is revisable.

## Staging artifact schema gaps (SQL in task must be re-expressed as joins)
- [ ] `staging_smws_tasting_notes.csv` has NO `whisky_id`, `bucket`, or `source_citation_id` columns.
- [ ] `smws_merge_candidates.csv` / `smws_ambiguous_candidates.csv` have NO citation column.
- [ ] All verification SQL in P128 preflight must join merge/ambiguous CSV → staging CSV → production.db, not query columns that don't exist.

## Gate readiness after prerequisites
| gate criteria | blocked by |
|---|---|
| 726 MERGE FK valid | ✅ already pass |
| 726 MERGE citation (C1) | B3 (need D2 inserts + D4 source_citation_id) |
| AMBIGUOUS review-ready | ✅ already pass |
| D1–D4 feasible | B1 (empty target), B2 (no crosswalk) |

**Bottom line:** Do NOT enter the P119.6b gate transaction until B1, B2, B3 are resolved. B4/B5 are review-policy decisions, not hard stops.

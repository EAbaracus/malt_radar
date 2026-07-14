# P95 — Books-Tier Contract Conflict Audit

- **Mode:** READ-ONLY. No source code modified, no DB modified, no migration created, no pipeline output changed.
- **Objective:** Audit the books-tier data contract before P95-C Canonical Flavor Conversion.
- **Date:** 2026-07-14 · **DB:** `output/import/production.db` (read via `mode=ro`)
- **Evidence base:** live `production.db` queries, `mr-kep/authority/*.yaml`, `docs/pipeline/*`, `backend/app/utils/source_guard.py`, `frontend/lib/core/utils/source_guard.dart`, `mr-kep/evidence/audit_rules.md`, `mr-kep/docs/glossary.md`.

---

## 1. VERIFIED (what currently holds)

- **Book ingestion tables exist & carry provenance columns.**
  - `staging_book_flavor_profiles` (2,577 rows): `source_system`, `source_book`, `source_page_or_section`, `extraction_method`, `conflict_existing_profile`, `radar_conflict`, `approval_status`. Columns confirmed via `PRAGMA table_info`.
  - `staging_notebooklm_flavor_profiles` (17 rows): `source_system`, `source_hint`, `flavor_source`, `whisky_name`, `approval_status`.
  - `tasting_notes` (1,848 rows): `source_system`, `source_name`, `source_doc`, `source_entry_number`, `source_url`.

- **Book data is present in production `flavor_profiles` via `flavor_source`.**
  - `flavor_profiles` has **no `source_system` column**; provenance lives in `flavor_source` (free-text) and `notes_for_review`.
  - 147 `flavor_profiles` rows carry a book-ish `flavor_source` (PDF filenames incl. `Anna's Archive`, `libgen.li`, `Jim Murray's Whisky Bible`, `The world atlas of whisky`).
  - `tasting_notes` carries book provenance under `source_system`: `book_manual_derived` (54), `book_manual_derived_v2` (23), `NotebookLM` (23).

- **Authority tier is frozen & consistent with P95-A/P95-B.** Per `mr-kep/authority/authority_matrix.yaml` + `source_priority.yaml`: `P32_BOOK_PIPELINE` and all book/NotebookLM sources resolve to **T3_community** (unlisted→T3 default). Books are **supporting-only, cannot sole-certify**. This is unchanged from P95-B `authority_matrix_v2.md`.

- **Provenance-retention rule exists (AR-3).** `mr-kep/evidence/audit_rules.md` AR-3: every entry self-describing (`source_class`, `source_name`, `source_url`/`source_citation`, `selector`, `retrieval_timestamp`, four hashes); losing merge candidates retained as `verified`/`superseded`, never dropped. `merge_policies.yaml` (lines 23, 50) requires attaching remaining candidates to `provenance.evidence[]`.

- **Conflict-hold behavior is wired.** `staging_book_flavor_profiles` carries `conflict_existing_profile` + `radar_conflict` columns; `approval_status` shows only `staging_pending_review` (2,575) + `promoted` (2). So 2,575 book rows are **held, not promoted** — matches "conflicts held" pipeline policy (`docs/pipeline/PIPELINE_OVERVIEW.md` P37 PARTIAL GO).

- **Gating/backup policy exists.** `docs/pipeline/MAINTENANCE.md` (lines 19, 22, 30): P35/P37 staging writes are gated, deterministic, referenceable; pre-write DB backups in `output/import/backups/` (`production_p35_premerge_*`, `production_p39_prestaging_*`); restore = revert staging.

- **External source-visibility control exists.** `backend/app/utils/source_guard.py` + `frontend/lib/core/utils/source_guard.dart` define `PUBLIC_FORBIDDEN_SOURCE_FIELDS` = `{source_id, source_name, source_url, source_system, source_reference, internal_source_url, internal_source_id, internal_audit_url}` and strip them from public responses unless `is_manual`. The control is symmetric (backend + frontend).

---

## 2. CONFLICTS (book contract vs intended policy)

- **C1 — Authority conflict (carried from P95-A/B, still open).** The P95-A directive's *illustrative* ranking placed **Certified Books = 5-star (T1)** and **WhiskyFun = 3-star**, but the frozen `authority_matrix.yaml` has **no book tier** (books fall to T3) and ranks **WhiskyFun = T2**. Frozen contract governs (books = T3). This is an **unresolved contract decision**, not a code bug. It affects whether book-derived rows may *sole-certify* in P95-C.

- **C2 — Provenance leakage via `flavor_source` (visibility gap; RESOLVED BY USER 2026-07-14).** `flavor_profiles.flavor_source` stores raw PDF filenames such as `Anna's Archive.pdf`, `libgen.li:...`, `annas-arch-*.pdf`. `SourceGuard` strips `source_system`/`source_name`/`source_url` but **does NOT list `flavor_source`** in `PUBLIC_FORBIDDEN_SOURCE_FIELDS`. The backend `flavor_profiles` schema (`backend/app/models/schemas.py:26`) and the frontend model (`frontend/.../whisky.dart:28,201`) both surface this field. **User decision: DO NOT modify SourceGuard; Anna's Archive and libgen sources are explicitly ALLOWED to surface in public responses.** Therefore this is now an *authorized, intentional* exposure — the prior R1 "leak" risk is downgraded to informational. (See D2.)

- **C3 — Provenance format inconsistency (book vs NotebookLM vs other).** Book flavor rows embed provenance as a **raw filename string** in `flavor_source` (e.g. `Jim Murray's Whisky Bible 2020 ... 9780993298646 ... Anna's Archive.pdf`). NotebookLM rows use `source_system='notebooklm_book_profile'` + `flavor_source='book_notebooklm'` (2 rows) — a different, less descriptive scheme. Tasting notes use a cleaner `source_system`/`source_doc` pair. **No single canonical provenance schema** is enforced across book-derived data, violating AR-3's "self-describing, four hashes" requirement for the `flavor_profiles` path.

- **C4 — Batch-separation policy under-enforced at the source.** `flavor_profiles` (2,676 rows) has **no `enrichment_version`/batch marker on book rows specifically**, and `staging_book_flavor_profiles.staging_id` is the only batch key. The Canonical Product Policy (P95-B `canonical_product_policy.md`) mandates MERGE-vs-KEEP_SEPARATE by sensory difference; the book pipeline records `cask_or_maturation`, `age_statement`, `abv` but the production table exposes no deterministic batch-identity column to prove a given book row was merged vs separated correctly. Verifiability gap, not a proven violation.

- **C5 — `staging_notebooklm_flavor_profiles` axis schema mismatch.** It carries **16 axis columns** (`smoky, sherry, fruity, sweet, spicy, oaky, maritime` + `floral, winey, malty, nutty, herbal, waxy, oily, light_body, rich_body`) — i.e. a **16-axis** model. The frozen canonical flavor standard (P95-B) is **7 axes** (`smoky, peaty, fruity, sweet, spicy, maritime, sherry`). NotebookLM staging data is in a **different axis vocabulary** than the canonical 7; P95-C conversion must map/reduce it (precision loss) or it cannot be promoted. `staging_book_flavor_profiles` is closer (adds `peaty`, `floral`, `oak`, etc. = 20+ axes) — also non-canonical. **Both book tables use axis sets ≠ canonical 7.**

---

## 3. RISKS

- **R1 (INFO) — Book/piracy-source filenames are intentionally public.** Per user decision (2026-07-14), SourceGuard is NOT modified and Anna's Archive / libgen sources are allowed to surface. Former "leak" risk downgraded to informational; no action required on visibility.
- **R2 (Med) — T3 book rows could sole-certify in P95-C if C1 is resolved the wrong way.** Without the frozen-contract guard enforced in the P95-C promotion rulebook, a book row (T3) might overwrite a T1/T2 canonical profile (violates "never replace stronger with weaker", "never lower confidence").
- **R3 (Med) — Axis-vocabulary mismatch.** Book/NotebookLM staging data (16–20 axes) cannot map losslessly to the canonical 7-axis `flavor_profiles.flavor_vector`. P95-C must define a deterministic reducer or reject; otherwise silent dimension-drop corrupts profiles.
- **R4 (Low/Med) — Provenance non-self-describing on production rows.** `flavor_source` raw strings are not AR-3-compliant (no `source_class`, no hashes). Future audits cannot reconstruct evidence from the row alone.
- **R5 (Low) — Batch identity unverifiable in production.** No per-book-batch marker on promoted rows; MERGE/KEEP_SEPARATE compliance (C4) cannot be proven post-facto.
- **R6 (Low) — 2 promoted book rows already in `staging_book_flavor_profiles` (`approval_status='promoted'`).** Need to confirm these were promoted through a gated path and that their `flavor_source` is sanitized downstream; unverified here (read-only).

---

## 4. REQUIRED DECISIONS

1. **D1 — Books authority tier (resolves C1).** Confirm books remain **T3_community** (frozen contract) → book rows can only corroborate, never sole-certify, in P95-C. (Recommended: keep frozen; reject the P95-A illustrative T1 ranking.)
2. **D2 — Source visibility (RESOLVED by user).** No change to `SourceGuard`. Anna's Archive and libgen sources are permitted in public responses. R1 closed as informational. (No implementation needed.)
3. **D3 — Canonical provenance schema for `flavor_profiles` (resolves C3/C4).** Adopt AR-3 structured provenance (`source_class`, `source_name`, `source_citation`, `selector`, `retrieval_timestamp`, hashes) instead of raw filename strings. Define migration path (P95-C or later).
4. **D4 — Axis-vocabulary policy for book/NotebookLM data (resolves C5/R3).** Define the deterministic 16/20→7 reducer (which axes map to the 7; how extras are dropped) **before** P95-C promotes any book-derived vector. Reject rows that fail the reducer.
5. **D5 — Batch-identity enforcement (resolves C4/R5).** Require a batch/version marker on book-derived production rows, or document that MERGE/KEEP_SEPARATE is enforced at staging only.

---

## 5. GO / NO-GO RECOMMENDATION

### Recommendation: **CONDITIONAL GO** for P95-C — proceed **only after D4 is decided/implemented**; D1, D3, D5 can run in parallel but are not hard blockers for a read-only conversion. (D2 RESOLVED — no visibility blocker.)

- **Safe to start now:** P95-C *Canonical Flavor Conversion* of the **already-promoted, non-book** axis_num vectors (the P95-A READY set) — these are T2, canonical 7-axis, and unaffected by the book conflict.
- **Must NOT start until resolved:**
  - **D4 (axis reducer):** blocking — book/NotebookLM staging uses 16–20 axes ≠ canonical 7; promoting without a defined reducer corrupts profiles (R3).
- **D1** should be confirmed (recommended: books=T3) so the P95-C promotion rulebook treats book rows as supporting-only.
- **D3/D5** are quality/debt items; record them as P95-C acceptance criteria but they do not block a read-only conversion pass.
- **D2 (visibility) — RESOLVED:** SourceGuard unchanged; Anna's Archive / libgen permitted publicly. No blocker remains on exposure.

**Bottom line:** The books-tier *contract* now has one enforcement gap (axis vocabulary, D4) and one unresolved authority decision (D1). P95-C can begin for the canonical-T2 set immediately, and **book/NotebookLM-derived promotion must wait only until D4 is settled** (axis reducer defined). No code was changed; this is audit-only.

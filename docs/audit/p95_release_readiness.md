# P95 Release Readiness Audit

- **Mode:** READ-ONLY. No source/DB/migration changes, no promotion, no regeneration (only re-read existing artifacts for integrity verification).
- **Date:** 2026-07-14 · **DB:** `output/import/production.db` (read via `mode=ro`)
- **DB signature (stable across all phases):** size=11,010,048 bytes · mtime_ms=1783879549340 · `flavor_profiles`=2,676 rows. **No phase mutated production.db.**

## 1. VERIFIED

- **Artifact completeness.** All phase deliverables present:
  - P95-A (`mr-kep/output/p95a/`): 13 files incl. `certification_matrix.csv`, `p95a_validation_report.json`, `integrity_hash.json`.
  - P95-B (`mr-kep/output/p95b/`): 8 files incl. `authority_matrix_v2.md`, `canonical_flavor_standard.md`, `canonical_product_policy.md`, `promotion_rulebook.md`, `integrity_hash.json`.
  - P95 Books Contract Audit (`docs/audit/p95_books_contract_audit.md`).
  - P95-C (`mr-kep/output/p95c/`): 8 files incl. `canonical_vectors.csv`, `rejected_unmappable.csv`, `excluded_check.csv`, `validation.json`, `integrity_hash.json`; plus `docs/audit/p95c_canonical_flavor_conversion.md`.
- **Cross-phase consistency.**
  - Canonical axes identical everywhere: `{smoky, peaty, fruity, sweet, spicy, maritime, sherry}` (decisions.md #2; P95-B `canonical_flavor_standard.md`; P95-C output).
  - P95-A READY=1,086 (T2, conf≥0.70, axis7, no existing profile) ⊕ P95-C eligible T2=1,998 (T2/core, all formats) — consistent: P95-C covers the wider T2 set; P95-A's 1,086 were the previously-unprofiled subset.
  - Authority tier model consistent: books/NotebookLM/ML = T3 across P95-B, P95 Books Audit, P95-C.
- **Determinism evidence.** All three phases ship `integrity_hash.json` (sha256 per-file + concat), `deterministic:true`. P95-A 12 files, P95-B 7 files, P95-C 7 files. Each phase was independently re-run byte-identical (ad-hoc verification, this session).
- **Production DB untouched.** `production.db` size/mtime/row-count identical before/after every phase (read-only `mode=ro` URI; no INSERT/UPDATE/DELETE/ALTER/DROP/VACUUM).
- **Canonical 7-axis compliance.** P95-C produced **1,611** vectors; **0 non-compliant** (exactly the 7 frozen axes).
- **Exclusion of T3/book data.** P95-C `excluded_check.csv` = 678 rows, all T3 (book 192, ml 326, notebooklm 2, other 5, upload 153). **Zero T2 rows in excluded set; zero book/NotebookLM rows in `canonical_vectors.csv`.**
- **No duplicate profiles.** P95-C output keyed by `whisky_id` (PK); MERGE/KEEP_SEPARATE respected (no new product records). P95-B batch classification covers all 3,557 products (KEEP_SEPARATE 3,471 / REVIEW 49 / MERGE 37).

## 2. OPEN ITEMS

1. **D1 — Books authority tier.** Recommended books=T3 (frozen contract). Not formally confirmed as a signed contract decision; frozen contract already governs. Non-blocking.
2. **D4 — Book/NotebookLM 16/20→7 axis reducer.** **Not implemented.** Book/NotebookLM staging uses non-canonical axis vocabularies (16–20 axes). Until D4 exists, book/NotebookLM vectors remain excluded from conversion (per user directive "ignore books-tier until D4").
3. **D3 — Canonical provenance schema.** `flavor_profiles.flavor_source` still stores raw filename strings (not AR-3 structured provenance). Quality/debt; not a blocker for read-only conversion.
4. **D5 — Batch-identity enforcement.** No per-book-batch marker on promoted rows; MERGE/KEEP_SEPARATE enforced at staging only. Debt; not a blocker.
5. **num_array axis-order contract.** P95-C rejected 152 `num_array` rows (incl. len-7) because no stored axis-order contract exists; positional mapping would be a guess. Needs a positional-axis-order definition before those rows can convert.
6. **Staging artifacts not yet promoted.** All P95-C outputs are staging artifacts only; nothing has landed in production.db.

## 3. RELEASE BLOCKERS

- **B1 (hard) — No gated promotion pathway executed.** P95-C artifacts are staging-only. Before any production mutation, a gated P35/P37-style promotion is required: pre-write DB backup (`output/import/backups/`), single transaction, rollback-on-error, one `promotion_audit_log` row, post-apply row-count assertion. **This is the mandatory gate; it has NOT run.**
- **B2 (scope) — D4 not implemented.** Book/NotebookLM (T3) vectors are deliberately excluded. If the release intends to include book-derived flavor data, D4 must land first. If the release is T2-only, this is not a blocker.
- **B3 (none) — Canonical-7 / exclusion / determinism / DB-untouched all PASS.** No blocker there.

## 4. PROMOTION CHECKLIST

- [ ] Authorize promotion (explicit GO from user — required before any `--apply`).
- [ ] Confirm release scope: T2-only (excludes book/NotebookLM) OR include D4 first.
- [ ] Take pre-write `production.db` backup (`output/import/backups/production_p95c_prestaging_*`).
- [ ] Run gated apply: backup + transaction + rollback-on-error + `promotion_audit_log` row.
- [ ] NOT-IN guard to prevent duplicate `flavor_profiles` keys (idempotent).
- [ ] Post-apply assertion: `flavor_profiles` row-count delta == converted count (1,611 new T2 canonical, or 1,086 if scoped to previously-unprofiled).
- [ ] Re-validate canonical-7 compliance on promoted rows (0 violations).
- [ ] Confirm production.db mtime/size changed only by the authorized transaction (no other writes).
- [ ] Update `promotion_audit_log`; mark P95-C artifacts as promoted.

## 5. FINAL GO / NO-GO

### VERDICT: **GO — for T2-only production promotion, CONDITIONAL on executing the gated promotion pathway (B1).**

- **Ready now:** All audit/architecture/conversion artifacts are complete, deterministic, canonical-7-compliant, T3/book-excluded, and DB-safe. P95-A (1,086 READY, 62.1%→92.6% coverage), P95-B (authority + flavor standard + rulebook), P95 Books Audit (visibility resolved per user), and P95-C (1,611 canonical vectors) are all internally consistent and verified.
- **Must happen before promotion:** the gated P35/P37-style apply (B1) — backup + transaction + rollback + audit log + post-apply assertion. Nothing has been promoted yet.
- **If the release scope includes book/NotebookLM data:** **NO-GO** until **D4** (16/20→7 reducer) is implemented (B2).
- **Non-blocking open items (D1, D3, D5, num_array contract):** document as acceptance criteria; do not block a T2-only promotion.

**Bottom line:** P95 is release-ready *as a T2-only, canonical-7, deterministic, audited pipeline*. The sole remaining hard gate is the authorized, gated production promotion itself (B1), which has not yet run. Book/NotebookLM promotion (D4) is deferred by user directive.

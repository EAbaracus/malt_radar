# P140 — Decision Proposal (Phase 6)

- doc_version: P140-1
- mode: READ-ONLY audit. This proposes a decision; it does NOT execute it.

## Options considered
- **A) KEEP_EMPTY_STRING** — leave `''` as-is, treat it as a distinct, valid value.
- **B) NORMALIZE_TO_NULL** — convert `''` → NULL in affected columns.
- **C) MIXED_POLICY** — normalize some columns, keep `''` in others.

## Recommendation: **NORMALIZE_TO_NULL**

### Evidence (no speculation)
1. **Semantics:** SQLite `''` ≠ NULL; they diverge in `IS NULL`, `=`, `COUNT`, `COALESCE`.
   (Phase 3.1)
2. **Convention:** 4 columns are 100% NULL; all other populated columns use NULL; only
   `region`/`age_statement` hold `''`. NULL is the established "no data" encoding.
   (Phase 1 census)
3. **Impact proven:** the `''` anomaly caused exactly the 530-row P139 gap (1,158 → 628).
   (Phase 2 gap analysis: 530/530 skipped = `region ''`, 0 true-NULL)
4. **No prior ruling:** decision_log D1–D5 never treat `''` as meaningful. (Phase 3.4)
5. **Low risk:** only index is on `whisky_id`; no index on affected columns → zero index
   impact. App/API already handle NULL (4 fully-NULL columns prove daily NULL paths exist).
   (Phase 5)
6. **Reversible:** idempotent `UPDATE ... SET col=NULL WHERE col=''` per column + backup.

### Why not KEEP_EMPTY_STRING
It perpetuates an inconsistency, leaves 530 high-confidence SMWS values unfillable by
NULL_FILL promotions, and forces every future query to special-case `''`. No evidence
supports `''` as a meaningful value.

### Why not MIXED_POLICY
Inconsistent encoding across columns is the current problem. A mixed policy would add a
third convention. Normalize all `''` → NULL for a single, coherent "missing = NULL" rule.

### Scope of the (future) normalization
- Columns: `region` (713), `age_statement` (791). Total 1,504 cells / 1,504 rows.
- Would enable 530 additional P139-equivalent region updates (remaining 183 region-`''`
  rows lack a high-confidence source and need separate authorization).
- Must be a **separate, explicitly-authorized write task** (e.g. P141), NOT part of this
  read-only audit. A pre-write backup + post-validation (counts, integrity_check) required.

## Verdict basis
NORMALIZE_TO_NULL is evidence-backed, low-risk, reversible, and resolves the root cause of
the P139 gap. Awaiting explicit user authorization before any SQL UPDATE executes.

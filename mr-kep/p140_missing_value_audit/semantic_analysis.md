# P140 — Semantic Analysis (Phase 3)

- doc_version: P140-1
- question: should `''` (empty-string) be treated as (A) a valid value, or (B) a missing value?

## Evidence

### 1. SQLite semantics
- In SQLite, `NULL` is the dedicated "absence of value". `''` is a **real, non-NULL
  text value of length 0**.
- `col IS NULL` is FALSE for `''`. `col = ''` matches only `''`, never NULL.
- `COUNT(col)` counts `''` but NOT NULL. `COALESCE(col,'x')` returns `''` for `''`, `'x'` for NULL.
- Therefore `''` and NULL behave **differently in every query** — conflating them is a bug.

### 2. Existing production conventions (from Phase 1 census)
- 4 columns (`finish_type`, `cask_strength`, `completed_fields`, `notes_for_review`)
  are **100% NULL** — they use NULL exclusively to mean "no data".
- All other populated columns also use NULL (never `''`).
- **Only `region` and `age_statement` contain `''`.** This is an outlier pattern, not a
  standard. The dominant, intentional convention is NULL = missing.

### 3. Project history
- P139 promotion used `UPDATE ... WHERE col IS NULL`. The 530 skipped region rows held
  `''` and were thus NOT filled. The promotion behaved correctly given NULL-only semantics,
  but 530 high-confidence SMWS values were left unfilled because of the `''` anomaly.
- This is exactly the 1,158 → 628 gap (530 rows) that triggered P140.

### 4. decision_log.jsonl
- D1–D5 cover write-target, source_id, consensus, counts, crosswalk. **None address
  empty-string vs NULL.** So there is no prior ruling establishing `''` as a valid value.
- Absence of any decision treating `''` as meaningful, combined with the census showing
  `''` only as an outlier, supports treating `''` as missing.

## Conclusion
**`''` should be classified as (B) missing value**, NOT a valid value.
Rationale: SQLite semantics distinguish them; the schema's dominant "no data"
convention is NULL (proven by 4 fully-NULL columns + all other columns); no decision
log entry treats `''` as meaningful; and the `''` occurrences are a localized anomaly in
exactly 2 columns. Treating `''` as missing aligns with existing conventions and unblocks
the 530 skipped promotions.

No speculation: every claim above is backed by the Phase 1 census or P139 artifact evidence.

# Forensic Addendum — `production.db` Re-Baselining (P103 Audit)

_Generated 2026-07-15 (post-audit, forensic pass) · READ-ONLY · no database modified_

## 0. Trigger

During the P103 corpus audit the agent detected that `output/import/production.db`
had changed **between the session-start baseline and the end of the audit**:

| metric | session-start baseline | current | delta |
|---|---|---|---|
| `production.db` whisky count | 3,557 | 3,876 | **+319** |
| `production.db` mtime | — | 20:21:52 | — |

The user instructed: treat this as a forensic event, re-baseline before any
further recommendation, identify the exact added/changed rows, determine origin,
verify no existing rows were silently altered beyond the inserts, recompute all
audit metrics against the current DB, and document everything. **Do not modify,
revert, or commit anything; do not begin Sprint 08.**

---

## 1. What changed

Comparison is against the only on-disk snapshot available —
`output/import/production.db.p33_backup.20260709_134752` (Jul-9 backup, 3,293 rows).
Current DB = 3,876 rows. All figures below are read-only diffs.

| category | count | evidence |
|---|---|---|
| Rows added since Jul-9 backup | **583** | `cur_ids - bak_ids` |
| Rows removed since Jul-9 backup | **0** | `bak_ids - cur_ids` = empty |
| Existing rows modified (any column) | **3** | full-column row comparison on 3,293 common ids |

### 1a. The 319 during-session rows (the flagged write)
Of the 583 added rows, **319 carry `data_confidence = NULL`**. This count
matches the +319 session-start→current delta exactly. These are the rows added
by the external process at/after 20:21:52.

The remaining **264** added rows carry `data_confidence = 'medium'` — i.e. a
**pre-session curated/staged import batch** (already present before my session
start: Jul-9 backup 3,293 → session-start 3,557 = +264, all `medium`).
So two distinct insert batches exist:

| batch | rows | data_confidence | when |
|---|---|---|---|
| Curated import (pre-session) | 264 | `medium` | before session (Jul-9 → start) |
| External write (in-session) | 319 | `NULL` | 20:21:52 (during/after audit) |

### 1b. The 3 modified existing rows
All three are **region-field enrichment**, not identity/content changes:

| whisky_id | field changed | backup → current |
|---|---|---|
| W001798 (maker's mark) | `region` | NULL → `Kentucky` |
| W003023 (clonakilty) | `region` | NULL → `Cork` |
| W002238 (kanosuke) | `region` | NULL → `Kyūshū` |

No `name`, `distillery_id`, `abv`, score, or brand field was altered on any
existing row. The change is additive enrichment only.

### 1c. Shape of the 319 new rows
- **ID format:** all 583 new rows use the legacy `W<3+ digits>` scheme (e.g. `W3462`),
  not the modern zero-padded `W######`.
- **Distillery linkage:** 549 / 583 have `distillery_id = NULL` (34 linked).
- **Names** are legitimate catalogue-style entries, e.g.
  `Old Grand-Dad`, `Jameson Black Barrel`,
  `Glenfiddich Orchard Experimental series #05`, `Glen Moray Port Cask Finish`,
  `Aberfeldy 12`, `Aberlour 16 Double Cask`, `Amrut Indian Cask Strength`.
- **Type/country:** mostly NULL; populated ones span Japan/USA/Ireland/India/Scotland
  etc. (consistent with a general catalogue import).
- **`abv` / `brand`:** NULL for all 583 (no liquid specifications attached).

---

## 2. When it changed

- **File mtime:** `production.db` → `2026-07-15 20:21:52`.
- This timestamp falls in the **gap between** the agent's `audit_enrich.py` run
  (20:07) and `audit_fix_smws.py` run (20:34). No audit script was executing at
  20:21:52.
- All four audit scripts open `production.db` **only** with `?mode=ro`; a grep of
  the audit scripts for `INSERT/UPDATE/DELETE/DROP/CREATE/commit()` returns
  **nothing** (the single "DELETE" hit is prose inside a markdown report).
- `knowledge.db` is in WAL mode (has `-wal`/`-shm`); `production.db` is in
  `journal_mode=delete` and has **no** `-wal`/`-shm` — consistent with the
  external writer using a normal read-write connection, not the agent's RO handles.

**Conclusion:** the +319 write was produced by a process **external to the
audit**. The audit did not cause it.

---

## 3. Origin — can we attribute it?

Evidence available from the DB itself:

- `whiskies` has **no** `created_at` / `updated_at` / import-batch column
  (columns: `whisky_id, name, original_name, distillery_id, country, region, type,
  age, age_statement, nas, abv, bottle_size, cask_type, finish_type,
  cask_strength, meta_critic_score, user_score, data_confidence,
  completed_fields, notes_for_review, brand`). The only timestamp-like column
  names are `age_statement` and `data_confidence` (false positives).
- Candidate audit/log tables exist but are tiny and unrelated to a bulk import:
  `review_actions` (6 rows), `promotion_audit_log` (2 rows),
  `review_conflict_log` (0 rows). None records a 319-row insert.
- `whiskybase_export_sample.csv` (a manual source) name-matched **0** of the new
  rows, so the write did **not** originate from that sample export.

**Attribution verdict:** The DB provides **no self-contained proof of which
pipeline** performed the 20:21:52 write. The observable signature
(realistic names, legacy ID format, mixed confidence, region-only enrichment on
3 existing rows, no distillery/abv/brand detail) is **consistent with a routine
product-catalogue import**, but it cannot be conclusively tied to a specific
named batch or script from database internals alone. Confirming the exact origin
would require external evidence (application logs, the process that held the
read-write connection at 20:21:52, or the operator who ran it).

---

## 4. Recomputed audit metrics (against current `production.db`)

All six reports were regenerated with `UNIVERSE = 3876`. Only the **coverage
denominator** changed; per-source entity extraction and ROI are independent of
the universe size, so priorities and sprint order are unaffected.

| metric | session-start snapshot | re-baselined (current) |
|---|---|---|
| Universe | 3,557 | **3,876** |
| Coverage (canonical_vectors) | 1,737 | 1,737 (unchanged) |
| **Coverage %** | **48.8 %** | **44.8 %** |
| Net-new potential (all candidates) | 2,014 | 2,014 |
| Sprint 08 (Whisky Advocate) net-new | 139 | 139 |
| Sprint 09 (books group B7) net-new | 123 | 123 |
| Sprint 10 (SMWS) net-new (sampled) | 2 | 2 |

`knowledge.db` re-verified: `integrity_check = ok`, coverage still **1,737**
(untouched by the audit).

---

## 5. Are the previous reports valid?

- The **original** six reports (written at session start) used the 3,557 universe
  and reported **48.8 % coverage**. Those numbers are a correct snapshot of the
  state *at that moment* but are now **superseded** by the re-baselined DB.
- The **regenerated** six reports (this pass) use the current 3,876 universe and
  report **44.8 % coverage**. These are the authoritative versions.
- **ROI ranking, source IDs, duplicate findings, and sprint order are unchanged**
  between the two passes (they derive from raw-source extraction, not the
  universe count).
- Recommendation: **use the regenerated reports**. Treat the 48.8 % figure as
  historical only. The discrepancy is fully explained by the external +319 write,
  not by any audit error.

---

## 6. Actions taken / not taken

- ✅ Read-only forensic diff (`audit_forensic.py`) → `forensic_rebaseline.json`
- ✅ Regenerated 6 reports against universe = 3,876
- ✅ No database modified, no rows reverted, no commit, no rename/move
- ✅ No Sprint 08 started
- ⏸ Awaiting user instruction on: (a) whether to investigate the exact origin of
  the 20:21:52 write further, and (b) when to begin Sprint 08 (against the
  re-baselined reports).

## 7. Evidence pointers

- `mr-kep/p103_corpus_audit/forensic_rebaseline.json` — full diff data
  (added ids, 3 modified rows with before/after, ID-format distribution,
  distillery null count, log-table counts).
- `mr-kep/p103_corpus_audit/corpus_audit_enriched.json` — measured per-source
  entity/coverage estimates.
- `output/import/production.db.p33_backup.20260709_134752` — the baseline the
  diff was computed against.
- Regenerated reports: `remaining_sources_inventory.md`, `source_gap_analysis.md`,
  `enrichment_priority_matrix.md`, `recommended_sprint_order.md`,
  `duplicate_source_analysis.md`, `coverage_projection.md`.

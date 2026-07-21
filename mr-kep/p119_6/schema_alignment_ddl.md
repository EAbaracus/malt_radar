# P119.6b — Schema Alignment DDL Design (PLAN-ONLY, NO EXECUTION)

**Author:** Hermes (Görev 2) · **Date:** 2026-07-16 · **Scope:** Design only. No DB mutation performed.
**Upstream gate:** P119.6b halt report (NO-GO) · **Policy basis:** P128 promotion contract + P121 write-gate.

---

## 0. Status: ⛔ BLOCKED — design cannot be finalized without 4 user decisions

This document is a **design artifact**, not an executed migration. It is blocked on the
open decisions in §2 because the task's stated premises do not match the repository state
(evidenced in §1). Execution belongs to Görev 3 (Antigravity), and the gate retry to Görev 4.

---

## 1. Discovery evidence (read-only, all verified)

### 1.1 Görev 1 — P127 bucket eligibility for SMWS USA
**Finding: NO P127 disposition exists for the SMWS USA 803-row staging set.**

| Probe | Result |
|---|---|
| `mr-kep/p127_entity_resolution/` contents | `p127_entity_resolution.md`, `confidence_distribution.md`, `merge_candidates.csv` (16,725), `create_candidates.csv` (10,829), `ambiguous_candidates.csv` (3,556) |
| `book` column in all 3 CSVs | 38–39 values, **all PDF books** (e.g. `Malt whisky yearbook 2019`, `Koder-Scotch-Malt-Whisky-Society.pdf`, `Jim Murray's Whisky Bible 2020`). **No `SMWS USA` / `Archive` book.** |
| Staging `source` value | `Counter({'SMWS USA': 803})` — a distinct non-book source |
| SMWS codes in staging (`cask_no`) | **797** unique |
| Overlap of staging SMWS codes ↔ P127 `surface`/`matched_entity` | **0** |
| SMWS-pattern strings (`^[A-Z]*\d{1,3}\.\d{1,4}$`) anywhere in P127 | **0** |
| Substitute disposition in `p120_smws_promotion/promotion_ready.csv` | 790 rows w/ UUID `whisky_id` (CREATE-style net-new) — this is a **P120 downstream proposal, NOT a P127 MERGE/CREATE/AMBIGUOUS classification** |

**Conclusion:** The SMWS USA 803 rows never passed through P127. P128 contract preconditions
(C1–C7) require a resolver classification (MERGE / CREATE / AMBIGUOUS + confidence) as the
promotion precondition. That artifact is **absent** for this source → **blocker B0**.

### 1.2 Target-DB ambiguity (B1)
The task says "→ knowledge.db's canonical_vectors + citations/official_source_references".
No single DB contains all three. Verified:

| DB | `canonical_vectors` | `citations` | `official_source_references` | Role |
|---|---|---|---|---|
| `output/import/production.db` (gate default `DB_PATH`) | ❌ absent | ❌ absent | ✅ **present (14 cols)** | Gate-protected production schema |
| `mr-kep/p102_bootstrap/knowledge.db` | ✅ 3,077 rows | ✅ 13,133 rows | ❌ absent | Bootstrap seed (has the vectors/citations) |
| `output/import/knowledge.db` | ❌ (0 bytes, empty) | ❌ | ❌ | Empty placeholder |

→ There is **no `knowledge.db` containing all three tables** as the task assumes. **Blocker B1.**

### 1.3 `official_source_references` already exists (B2)
`production.db` already has `official_source_references` with schema:
`ref_id, entity_type, entity_id, source_category, source_name, source_url, source_domain,
field_name, field_value, confidence, retrieved_at, license_risk, copyright_risk, created_at`
(PK `ref_id`). The task proposes a **different** schema (`source_id, citation_id, source_url, page_no…`).
These conflict. **Decision required** (D2).

### 1.4 Axis mismatch + P128 direct-load prohibition (B3)
- DB `canonical_vectors` columns: `vector_id, consensus_id, smoky, peaty, fruity, sweet, spicy, maritime, sherry`
  (7 canonical axes per skill: smoky, peaty, fruity, sweet, spicy, **maritime**, sherry).
- CSV `canonical_vectors_staging.csv` columns: `smws_code, smoky, peaty, sherry, fruity, spicy, sweet, **rich**`.
- DB has `maritime`, CSV has `rich` (and no `maritime`, no `smws_code`).
- **P128 rule (promotion_contract §5 + conflict_resolution_rules §3):** *"Flavor vectors — only via
  knowledge.db consensus, never direct"*; vector divergence is resolved by `consensus_nodes`, not
  direct insert. ⇒ The original P119.6b step "load 792 vectors directly into canonical_vectors"
  **violates P128** even after DDL is fixed. **Blocker B3.**

### 1.5 Count / data consistency (B4)
| Artifact | Rows | Note |
|---|---|---|
| `staging_smws_tasting_notes.csv` (logical) | **803** | `wc -l`=13,239 is inflated by ~15.5 embedded newlines/row in `tasting_notes_raw` |
| `canonical_vectors_staging.csv` | **792** | unique `smws_code`=792, no dups |
| SMWS codes in tasting notes (`cask_no`) | 797 unique | ≠ 792 vector codes |
| Overlap vector codes ↔ tasting-note codes | **725** | 67 vector codes have no tasting note; 72 tasting codes have no vector |
| `p120_smws_promotion/promotion_ready.csv` | 790 | UUID `whisky_id`s (net-new CREATE) |

→ 803 ≠ 792 ≠ 790 ≠ 725. The load set is undefined until reconciled. **Blocker B4.**

### 1.6 Gate default target mismatch (B5)
`get_write_connection()` defaults `DB_PATH = output/import/production.db`. If called without
`db_path`, the gate opens `production.db` — which has **no** `canonical_vectors`/`citations`.
To write those, the caller must pass `db_path="…/p102_bootstrap/knowledge.db"`. But the gate's
OS-level R/O lock (`DENY_PRINCIPAL` + `attrib +R`) is scoped to `production.db`; writing to the
bootstrap `knowledge.db` would **bypass the OS lock entirely** (the lock only covers production.db).
**Security consideration — decision required** (D3).

---

## 2. DECISIONS REQUIRED (user must answer before Görev 3)

| # | Decision | Options | Impact |
|---|---|---|---|
| **D1** | Which DB is the gate target for P119.6b? | (a) `production.db` (gate default) — but needs `canonical_vectors`+`citations` added there; (b) `mr-kep/p102_bootstrap/knowledge.db` — already has them, but bypasses OS lock; (c) consolidate into one | Determines where every DDL block runs |
| **D2** | `official_source_references` schema | (a) reuse `production.db`'s existing 14-col table; (b) create task's `source_id…` schema in knowledge.db; (c) align both | Avoids schema conflict (B2) |
| **D3** | Direct vector load vs P128 consensus | (a) honor P128: stage vectors → `consensus_nodes` only, **no direct `canonical_vectors` insert**; (b) override P128 for this one-off | Resolves B3 (policy-compliance) |
| **D4** | Reconcile the 803/792/790/725 mismatch | (a) load only the 725 intersecting codes; (b) full outer join w/ NULLs; (c) re-run extraction to make counts agree | Resolves B4; defines actual load set |

**Until D1–D4 are answered, Görev 3 (execution) must not run.** Proceeding would either
mutate the wrong DB, violate P128, or load an undefined row set.

---

## 3. DDL Block A — `canonical_vectors`: add `smws_code` + axis reconciliation

**Target (pending D1):** the DB that holds `canonical_vectors` = `mr-kep/p102_bootstrap/knowledge.db`
(unless D1 picks production.db, in which case the table must first be created there).

```sql
-- A1. Add join key for P128 duplicate-SMWS detection
ALTER TABLE canonical_vectors ADD COLUMN smws_code TEXT;

-- A2. Axis reconciliation: DB has 'maritime' (canonical 7th axis), CSV has 'rich'.
--     RECOMMENDED (honors 7-axis standard): add 'rich' as an 8th SMWS-specific axis,
--     leave 'maritime' NULL for SMWS rows (rich != maritime; do NOT silently map).
ALTER TABLE canonical_vectors ADD COLUMN rich INTEGER;

-- A3. (Optional) uniqueness guard for dedupe-on-reload
CREATE UNIQUE INDEX IF NOT EXISTS idx_cv_smws_code ON canonical_vectors(smws_code);
```

**vector_id / consensus_id derivation (loader logic, not DDL):** the DB PKs are TEXT
(`VEC_W3411`, `CONS_W3411`). SMWS codes (`12.34`, `G1.10`) are not valid as-is. Derive:
`vector_id = 'VEC_SMWS_' || replace(smws_code, '.', '_')`, `consensus_id = 'CONS_SMWS_' || replace(...)`.

- **Data-corruption risk:** `ALTER TABLE … ADD COLUMN` is safe (new cols NULL). `idx_cv_smws_code`
  fails only if duplicate `smws_code` already exists (none today — verified unique in staging).
- **Backfill:** existing 3,077 rows get `smws_code=NULL`, `rich=NULL` (non-SMWS book vectors unaffected).
- **Rollback:** `ALTER TABLE canonical_vectors DROP COLUMN smws_code;` / `DROP COLUMN rich;`
  (SQLite ≥3.35) or table-rebuild; `DROP INDEX idx_cv_smws_code;`.
- **Post-DDL validation:**
  ```sql
  PRAGMA table_info(canonical_vectors);          -- expect smws_code, rich appended
  SELECT COUNT(*) FROM canonical_vectors WHERE smws_code IS NOT NULL;  -- 0 pre-load, 792 post
  SELECT COUNT(DISTINCT smws_code) FROM canonical_vectors;            -- uniqueness check
  ```

---

## 4. DDL Block B — `citations`: add `source_key` (non-book source)

**Target (pending D1):** DB holding `citations` = bootstrap `knowledge.db`
(`citation_id PK, version_id FK→book_versions, page_number, chunk_id, raw_text NOT NULL, source_hash NOT NULL`).

```sql
-- B1. Alternative key for non-book sources (SMWS USA has no book_versions row)
ALTER TABLE citations ADD COLUMN source_key TEXT;

-- B2. Mark the FK optional for non-book rows (version_id already nullable per schema)
--     No DDL needed; loader writes version_id=NULL, source_key='SMWS_USA' for SMWS rows.
```

- **Data-corruption risk:** minimal — additive nullable column. Existing 13,133 book rows keep
  `version_id` populated, `source_key=NULL`.
- **Backfill:** none required (NULL is valid; `version_id` FK only fires when non-NULL).
- **Rollback:** `ALTER TABLE citations DROP COLUMN source_key;` (SQLite ≥3.35) or rebuild.
- **Post-DDL validation:**
  ```sql
  PRAGMA table_info(citations);                 -- expect source_key appended
  SELECT COUNT(*) FROM citations WHERE source_key='SMWS_USA';   -- 0 pre, 803 post (or 792 per D4)
  SELECT COUNT(*) FROM citations WHERE version_id IS NULL AND source_key IS NULL; -- should stay 0
  ```

> **FK caveat (verified):** `citations.version_id` has `FOREIGN KEY → book_versions(version_id)
> ON DELETE CASCADE`. SMWS rows set `version_id=NULL` so the FK is not violated. The loader must
> NOT invent a `version_id`.

---

## 5. DDL Block C — `official_source_references` (citation chain)

**Conflict (B2):** `production.db` ALREADY has this table (14 col, PK `ref_id`). The task's
proposed `source_id, citation_id, source_url, page_no…` schema **does not match**. Per **D2**,
two paths:

**(C-a) Reuse existing `production.db` table (RECOMMENDED — no new table):**
Map the SMWS citation chain into the existing columns:
`ref_id=TEXT PK, entity_type, entity_id, source_category='smws_archive', source_name='SMWS USA',
source_url, source_domain, field_name, field_value, confidence, retrieved_at, license_risk,
copyright_risk, created_at`. No DDL needed; the loader inserts rows.

**(C-b) Create task's schema in knowledge.db (only if D2=b/c):**
```sql
CREATE TABLE IF NOT EXISTS official_source_references (
    source_id   TEXT PRIMARY KEY,
    citation_id TEXT,                       -- FK → citations(citation_id) when present
    source_url  TEXT,
    page_no     INTEGER,
    source_name TEXT,
    license_risk  TEXT,
    copyright_risk TEXT,
    retrieved_at TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_osr_citation ON official_source_references(citation_id);
```

- **Data-corruption risk:** (C-a) none — append-only inserts into existing table.
  (C-b) creating a second, differently-shaped `official_source_references` **introduces schema
  drift** and confuses the P128 C1 contract (which references the 14-col production shape).
- **Backfill:** N/A (new rows per load).
- **Rollback:** (C-b) `DROP TABLE official_source_references;`.
- **Post-DDL validation:**
  ```sql
  -- C-a (production.db):
  SELECT COUNT(*) FROM official_source_references WHERE source_category='smws_archive';
  -- C-b (knowledge.db):
  PRAGMA table_info(official_source_references);
  SELECT COUNT(*) FROM official_source_references;
  ```

---

## 6. DDL Block D — `citations.source_citation_id` FK → `official_source_references`

**Note:** the name `source_citation_id` (task) is ambiguous — it would point a citation to a
*source* row. The natural P128 chain is `citations.citation_id → official_source_references.citation_id`
(i.e. the source row *references* the citation). Design below supports both.

```sql
-- D1. Add FK column on citations (nullable, non-book-safe)
ALTER TABLE citations ADD COLUMN source_citation_id TEXT;

-- D2. Enforce referential integrity (only fires when non-NULL)
--     SQLite FK enforcement requires the table to be created WITH the FK, so we rebuild:
PRAGMA foreign_keys=OFF;
BEGIN;
CREATE TABLE citations_new (
    citation_id  TEXT PRIMARY KEY,
    version_id   TEXT,
    page_number  INTEGER,
    chunk_id     TEXT,
    raw_text     TEXT NOT NULL,
    source_hash  TEXT NOT NULL,
    source_key   TEXT,                                          -- from Block B
    source_citation_id TEXT,
    FOREIGN KEY (version_id) REFERENCES book_versions(version_id) ON DELETE CASCADE,
    FOREIGN KEY (source_citation_id) REFERENCES official_source_references(source_id)  -- D2-dependent
);
INSERT INTO citations_new SELECT citation_id, version_id, page_number, chunk_id,
    raw_text, source_hash, source_key, source_citation_id FROM citations;
DROP TABLE citations;
ALTER TABLE citations_new RENAME TO citations;
CREATE INDEX idx_citations_hash ON citations(source_hash);
CREATE INDEX idx_citations_version ON citations(version_id);
CREATE INDEX idx_citations_src ON citations(source_citation_id);
COMMIT;
PRAGMA foreign_keys=ON;
```

- **Data-corruption risk:** **HIGH** — table rebuild. Must run inside the P121 gate transaction
  with a pre-backup (B1/§7). If `official_source_references` is the production.db table and
  `citations` is in knowledge.db (D1 split), the cross-DB FK is **impossible** (SQLite FKs are
  intra-DB only) → in that case `source_citation_id` is a logical pointer, not an enforced FK.
- **Backfill:** `source_citation_id=NULL` for all rows pre-load.
- **Rollback:** restore from the pre-DDL backup (do NOT attempt column-drop on a rebuilt table).
- **Post-DDL validation:**
  ```sql
  PRAGMA foreign_key_check;                 -- must be empty
  SELECT COUNT(*) FROM citations WHERE source_citation_id IS NOT NULL;   -- 0 pre, N post
  ```

---

## 7. Consolidated execution order + guardrail (for Görev 3, after D1–D4)

1. **Pre-flight backup** (mandatory, per AGENTS.md): copy target DB(s) to
   `backups/knowledge.db.p119_6b_pre_ddl_<YYYYMMDD_HHMMSS>` + record sha256.
2. Run Blocks **A → B → C → D** **inside `get_write_connection(authorized_context="smws_usa_p119_6_schema")`**,
   each in its own `BEGIN IMMEDIATE` (the gate auto-runs `integrity_check` + `foreign_key_check`).
3. **Hash guard:** sha256 before/after must differ ONLY by the intended tables; assert
   `canonical_vectors`/`citations` rowcounts unchanged by DDL (DDL adds cols, not rows).
4. **Do NOT** load any data in Görev 3 — that is Görev 4 (gate retry) and is separately gated by
   **P128 consensus rule (B3)** + the **P127 disposition (B0)** which are still open.

---

## 8. Verdict of this design phase
- **Görev 1:** ✅ Answered — **no P127 disposition for SMWS USA** (MERGE/CREATE/AMBIGUOUS counts:
  **MERGE 0, CREATE 0, AMBIGUOUS 0** for this source; the 16,725/10,829/3,556 totals are book-corpus only).
- **Görev 2:** ✅ Design written (plan-only). **Execution blocked** on decisions **D1–D4** and the
  policy conflicts **B0 (P127 missing), B2 (table exists), B3 (P128 direct-load ban)**.
- **Next:** user answers D1–D4 → Görev 3 (Antigravity execute DDL) → Görev 4 (Hermes gate retry).
- **No DB was mutated** by this phase. `knowledge.db` sha unchanged: `e3878743…cfe6cd72`.

---

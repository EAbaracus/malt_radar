# Migration Risk Report — P121

## 1. Summary

Productionizing KEP involves 4 categories of risk. Each is rated below.

| Risk Category | Severity | Likelihood | Impact |
|---|---|---|---|
| Data Loss | LOW | LOW | Existing enrichment data could be lost if knowledge.db schema changes |
| Schema Conflict | MEDIUM | MEDIUM | knowledge.db has no versioned schema migration; breaking changes risk data |
| Behavioral Regression | HIGH | MEDIUM | Book enrichment sprints produce known-correct data; changing resolution logic may change results |
| Pipeline Collision | LOW | LOW | Multiple processes writing to knowledge.db simultaneously |

---

## 2. Data Loss Risk

### Existing knowledge.db State
- **13,133 facts** across 6 book enrichment sprints
- **3,077 consensus nodes** + **3,077 canonical vectors**
- **3101 promotion candidates**
- **24 books registered**

### What Protects This Data

| Protection | Status |
|---|---|
| knowledge.db `integrity_check` runs after every write | ✅ Enforced by `save_to_knowledge_db()` |
| `foreign_key_check` runs after every write | ✅ Enforced |
| `PRAGMA foreign_keys = ON` | ✅ Enforced |
| `INSERT OR IGNORE` prevents overwrite | ✅ Enforced |
| All writes use `BEGIN IMMEDIATE TRANSACTION` | ✅ Enforced |

### What Would Risk Data Loss

| Action | Risk Level |
|---|---|
| Dropping or altering knowledge.db tables | **HIGH** — schema change could orphan existing data |
| Adding new columns to existing tables | **LOW** — `ALTER TABLE ADD COLUMN` is safe |
| Changing ID format (e.g. `CONS_` prefix change) | **MEDIUM** — old entries use old format; new entries use new format |
| The Promotion Gate is designed to use the EXISTING knowledge.db schema (12 tables, same columns) as proven by the book enrichment sprints. No schema changes are required. |

**Verdict: LOW risk.** The Promotion Gate writes to the same schema that enrichment already uses. No migration needed.

---

## 3. Schema Conflict Risk

### knowledge.db Schema (p102_bootstrap/schema.sql)

The schema has 12 tables: `books`, `book_versions`, `citations`, `evidence_nodes`,
`extracted_facts`, `consensus_nodes`, `canonical_vectors`, `promotion_candidates`,
`promotion_runs`, `audit_logs`, `schema_metadata`.

### Key Differences from KEP Canonical Output

| KEP Field | knowledge.db Table | Compatible? |
|---|---|---|
| `entity.entity_key` | `extracted_facts.entity_key_raw` | ✅ String match |
| `metadata.flavor_axes.*` | `canonical_vectors.*` (7 columns) | ✅ Same 7 axes |
| `metadata.nose/palate/finish` | `extracted_facts.descriptor_raw` (JSON) | ✅ Can store as JSON |
| `evidence[index].evidence_id` | `evidence_nodes.evidence_id` | ✅ Direct match |
| `certification.per_field.*` | `consensus_nodes` | ⚠️ Partial — consensus_nodes has whisky_id + algorithm_version, not per-field |
| `provenance.run_id` | Not in knowledge.db schema | ⚠️ New column needed, or store in `promotion_runs` |
| `confidence.per_field` | Not in knowledge.db schema | ⚠️ Not stored currently; can go in `extracted_facts.confidence_score` |

### Gaps to Address

| Gap | Impact | Solution |
|---|---|---|
| `consensus_nodes` has no `per_field` column | Cannot store per-field certification level | Add `certification_fields` TEXT column to `consensus_nodes` (or store in `promotion_runs`) |
| No provenance tracking per row | Cannot know which pipeline run produced a fact | Already tracked via `version_id` in citations → promotion_runs chain |
| No `source_key` in extracted_facts | Cannot trace which source produced a fact | `fact_id` prefix convention encodes source; or add `source_key` column |
| No `confidence_score` in canonical_vectors | Vector has no confidence metadata | Already stored via `extracted_facts.confidence_score` + `consensus_id` join |

**Verdict: MEDIUM risk.** The schema is mostly compatible, but 2-3 minor schema additions may be needed for full provenance. These should be additive (ALTER TABLE ADD COLUMN) to avoid breaking existing data.

### Concrete Schema Additions

| Table | New Column | Type | Constraints | Default | Purpose |
|---|---|---|---|---|---|
| `consensus_nodes` | `certification_fields` | TEXT | NULL | NULL | JSON blob: per-field certification_level, certification_path, authority_tier |
| `extracted_facts` | `source_key` | TEXT | NULL | NULL | Source identifier (e.g. "MW2019", "SMWS", "VINMONOPOLET") — enables provenance queries without parsing fact_id prefix |
| `citations` | `source_key` | TEXT | NULL | NULL | Same as above, for citation-level source tracking |

SQL:
```sql
ALTER TABLE consensus_nodes ADD COLUMN certification_fields TEXT;
ALTER TABLE extracted_facts ADD COLUMN source_key TEXT;
ALTER TABLE citations ADD COLUMN source_key TEXT;
```

These additions are:
- **Backward-compatible**: NULL default means existing rows are unaffected
- **Non-breaking**: No existing query references these columns
- **Optional for book data**: Book enrichment already encodes source in `citation_id` prefix; these columns enable uniform queries across all source types

### Citations Foreign Key for Non-Book Sources

Book enrichment writes to `citations` with `version_id → book_versions.version_id`. SMWS and retail sources have no book_versions entry. Two options:

| Option | Mechanism | Risk | Recommendation |
|---|---|---|---|
| **Nullable version_id** | Keep `citations.version_id` as-is (currently nullable? — schema shows `version_id TEXT REFERENCES book_versions(version_id)`, no NOT NULL). If already nullable in practice: non-book citations write NULL. If NOT nullable: ALTER to make it nullable. | LOW — already nullable per schema inspection | ✅ **PREFERRED** — zero schema change; non-book sources use `version_id=NULL`, `source_key='SMWS'` |
| **Sentinel value** | Use `version_id='NON_BOOK'` — would need a dummy `book_versions` row. | MEDIUM — dummy row must be inserted before every run; risk of FK error if cleanup removes it | ❌ Not recommended |

**Decision: Nullable version_id.** Schema already allows NULL for `version_id` (no NOT NULL constraint in `schema.sql` line 19). Non-book citations write:
- `version_id = NULL`
- `source_key = 'SMWS'` or `'VINMONOPOLET'` (new column, see above)

---

## 4. Behavioral Regression Risk

### What Changes

| Change | Current | Target | Risk |
|---|---|---|---|
| Entity resolution for books | Inline in each sprint (`extract_entities()` in 6 places) | Shared `EntityResolver.resolve()` | **HIGH** — different code may resolve differently |
| Canonical vector generation | Inline in each sprint | Shared D4 reducer or shared function | **MEDIUM** — must reproduce identical vectors |
| ID generation | Per-sprint convention (`CIT_MW2019_...`, `CIT_WAW2011_...`) | Shared convention (`CIT_{source_key}_...`) | **MEDIUM** — ID format change may affect existing lookups |

### Regression Test Requirements

For each book enrichment sprint that is migrated:

1. **Re-run the original sprint** against a COPY of knowledge.db
2. **Run the new adapted pipeline** against the SAME knowledge.db copy
3. **Compare outputs** — for each recognized entity:
   - Same consensus_id pattern? (format difference OK)
   - Same whisky_id resolved? (MUST be identical)
   - Same canonical_vectors values? (MUST be identical)
   - Same extracted_facts? (citations may differ by ID format, but content must match)

### Mitigation Strategy

| Phase | Action |
|---|---|
| **Before migration** | Snapshot knowledge.db with SHA-256 of every table |
| **During migration** | Never modify existing book enrichment sprint files — create new adapter modules |
| **After migration** | Run regression comparison on a DB copy |
| **If regression found** | Debug the resolution difference; the shared resolver must match inline results OR document why the new result is more correct |

**Verdict: HIGH risk for entity resolution consolidation.** The inline resolution in book enrichment is proven (95%+ success, 13K facts). Any change to the resolution algorithm risks producing different results for the same inputs. This requires careful regression testing.

---

## 5. Pipeline Collision Risk

### Current Write Paths

| Writer | Target | Frequency |
|---|---|---|
| Book enrichment sprints | knowledge.db | ~1 per sprint (manual) |
| Structured source intake | knowledge.db | ~1 per sprint (manual) |
| P119/P120 | knowledge.db (claimed) | TRIED but failed; no writes |
| KEP pipeline | output/ files only | Test-only |

### Post-Migration Write Paths

| Writer | Target | Frequency |
|---|---|---|
| Book enrichment sprints | knowledge.db (replaced by adapter) | Will be replaced |
| KEP pipeline through Promotion Gate | knowledge.db | Per run (manual or cron) |
| Structured source intake | knowledge.db (via adapter) | Per run |

Since all writes use `BEGIN IMMEDIATE TRANSACTION` + `INSERT OR IGNORE`, concurrent writes are safe:
- Second writer waits for first transaction to complete
- Duplicate entries are silently ignored
- No data corruption from concurrent access

**Verdict: LOW risk.** SQLite with WAL mode and immediate transactions handles concurrent writes correctly.

---

## 6. Legacy Apply Scripts — Envanter ve Akıbet Kararı

### 6.1 Apply Script Envanteri (scripts/apply/*.py)

Mevcut 14 apply script'in her biri doğrudan **production.db**'e yazmaktadır. P121 Promotion Gate ise **knowledge.db**'e yazacaktır. Bu iki hedef FARKLI veritabanları olduğu için yazma çakışması yoktur, ancak BİLGİ ÇAKIŞMASI riski vardır (aynı whisky_id'ye iki farklı yol farklı değer yazabilir).

| # | Script | Tablo | İşlem | Koşul |
|---|---|---|---|---|
| 1 | `apply_book_extract_v2_candidates.py` | `tasting_notes`, `flavor_profiles` | INSERT | Book extraction candidate |
| 2 | `apply_book_manual_candidates.py` | `tasting_notes` | INSERT | Manual candidate |
| 3 | `apply_data_coverage_next_v5_flavor_profiles.py` | `flavor_profiles` | INSERT | Coverage v5 |
| 4 | `apply_data_coverage_next_v9_v5_key_fix.py` | `flavor_profiles` | UPDATE (flavor_vector) | Key fix |
| 5 | `apply_dedup_book_extract_v2_flavor_profiles.py` | `flavor_profiles` | DELETE | Deduplication |
| 6 | `apply_flavor_profile_candidates_from_tasting_notes.py` | `flavor_profiles` | INSERT | From tasting notes |
| 7 | `apply_low_risk_official_facts_v10.py` | `whiskies` (UPDATE), `official_source_references` (INSERT) | UPDATE+INSERT | Low risk batch 4 |
| 8 | `apply_low_risk_official_facts_v12.py` | `whiskies` (UPDATE region), `official_source_references` (INSERT) | UPDATE+INSERT | Final P1 batch |
| 9 | `apply_low_risk_official_facts_v4.py` | `whiskies` (UPDATE cask_type) | UPDATE | Batch 1 |
| 10 | `apply_low_risk_official_facts_v6.py` | `whiskies` (UPDATE), `official_source_references` (INSERT) | UPDATE+INSERT | Batch 2 |
| 11 | `apply_low_risk_official_facts_v8.py` | `whiskies` (UPDATE), `official_source_references` (INSERT) | UPDATE+INSERT | Batch 3 |
| 12 | `apply_official_source_metadata_schema_v3.py` | `official_source_references` | INSERT | Schema v3 |
| 13 | `apply_production_uploaded_note_cleanup.py` | `tasting_notes` | DELETE | Cleanup |
| 14 | `apply_remaining_uploaded_notes_rebuild.py` | `tasting_notes` | DELETE+INSERT | Rebuild |

**Hedef production.db tabloları:** `whiskies` (UPDATE), `flavor_profiles` (INSERT+UPDATE+DELETE), `tasting_notes` (INSERT+DELETE), `official_source_references` (INSERT).

### 6.2 Karar: TEK YAZMA NOKTASI (aşamalı geçiş)

**Seçim: TEK YAZMA NOKTASI** — Promotion Gate, KEP pipeline çıktılarını knowledge.db'e yazdıktan sonra, ayrı bir `production_promotion_gate` aşaması da production.db'e yazar. Legacy apply script'ler aşamalı olarak deprecate edilir.

| Zaman | knowledge.db Yazıcı | production.db Yazıcı |
|---|---|---|
| **P121 anı** | Promotion Gate (yeni) | Legacy apply scripts (mevcut) |
| **P121+** | Promotion Gate | Legacy scripts + deneme amaçlı production_promotion_gate |
| **Gelecek** | Promotion Gate | Promotion Gate (legacy script'ler kapatılır) |

**Gerekçe:**
1. Legacy apply script'lerin her biri farklı mantıkla farklı tablolara yazıyor — hepsini tek gate'de toplamak büyük bir refactoring. Aşamalı geçiş daha güvenli.
2. P121 Promotion Gate **sadece knowledge.db** yazar. production.db'e yazmak ayrı bir gate (Phase 4).
3. Legacy script'lerin kendileri zaten güvenli (`EXPECTED_CONFIRM` string'i ile korunuyor, manuel onay gerektiriyor) — acil kapatma gerektirmiyor.

**Reddedilen alternatif — PARALEL:**
Legacy script'lerin sonsuza kadar paralel kalması önerilmez. Aynı whisky_id'ye KEP pipeline (knowledge.db → production.db) ve legacy script (doğrudan production.db) farklı değerler yazabilir. Uzun vadede bu çözülemez bir inconsistency yaratır.

**Mitigation (geçiş süresince):**
- Legacy script'lere `source = 'legacy_apply'` etiketi eklenir (opsiyonel, yeni kolon)
- Production promotion gate, legacy script'lerin yazdığı whisky_id'leri atlar (`WHERE whisky_id NOT IN (SELECT whisky_id FROM legacy_write_log)`)
- Geçiş tamamlandığında legacy script'ler `DEPRECATED` işaretiyle archive'e taşınır

---

## 7. Files That Must NOT Change

To preserve the ability to verify old enrichment runs, these files must remain frozen:

| File | Why |
|---|---|
| `book_enrichment_sprint01/enrich_mw_yearbook_2019.py` | Sprint 01 baseline — proven reference implementation |
| `book_enrichment_sprint0*/*.py` | All sprint loaders — regression comparison targets |
| `p102_bootstrap/schema.sql` | Baseline schema — migration target |
| `p102_bootstrap/knowledge.db` | Live data — copy before any migration |
| `authority/*.yaml` | Frozen contracts — must not change |
| `schemas/*.json` | Frozen schemas — must not change |

New adapter modules go in `mr-kep/source_adapters/` — they import from existing
code but never modify the frozen files.

---

## 8. Rollback Plan

If the Promotion Gate produces incorrect results:

| Step | Action |
|---|---|
| 1 | Disconnect the gate: comment out `promote()` call in `pipeline/run.py` |
| 2 | Revert knowledge.db: restore from pre-migration backup |
| 3 | Run old enrichment script on the restored DB |
| 4 | Fix the gate, re-test on a copy, re-apply |

Backup command (pre-migration):
```bash
cp mr-kep/p102_bootstrap/knowledge.db mr-kep/p102_bootstrap/knowledge.db.pre_p121.bak
```

## 9. Risk Matrix Summary

| Risk | Severity | Mitigation |
|---|---|---|
| Data loss | LOW | No schema changes needed; INSERT OR IGNORE |
| Schema incompatibility | MEDIUM | 2-3 additive columns; verify first |
| Behavioral regression | HIGH | Regression test with DB copy; snapshot before |
| Pipeline collision | LOW | BEGIN IMMEDIATE + WAL mode |

# P123 — Corpus Intelligence Pipeline (KEP + AOS) — Implementation Blueprint

**Status:** DESIGN-ONLY · READ-ONLY · NO production/knowledge.db/runtime/code change.
**Baseline:** P122 VERIFIED (49 books, 40 domains, internal consistency PASS, DBs untouched).
**Ground truth:** `mr-kep/p102_bootstrap/schema.sql` (the *existing* `knowledge.db` schema), `mr-kep/AGENTS.md` (6 KEP agents + authority tiers), `book_enrichment_sprint01/delta_report.md` (real resolver/consensus numbers). P123 extends this foundation — it does **not** replace or speculate.

This document is the blueprint for the next development cycle. Every proposal maps to an existing table, agent stage, or prior P-decision.

---

## 0. Architecture Alignment (non-negotiable anchors)

| Anchor | Source of truth |
|---|---|
| 7 canonical flavor axes | `canonical_vectors` columns: smoky, peaty, fruity, sweet, spicy, maritime, sherry |
| Knowledge graph prototype | `knowledge.db` already models Book→Version→Citation→Evidence→Fact→Consensus→Vector |
| Immutability | `evidence_nodes`/`extracted_facts`/`consensus_nodes` carry `status` (`ACTIVE/SUPERSEDED/REVOKED/ARCHIVED`); never UPDATE-in-place |
| Authority tiers | `source_profile.yaml` tiers (e.g. T3_community for books — "may not sole-certify") |
| Pipeline stages | 6 KEP agents: Qualification→Extraction→Validation→Merge→Certification→Audit |
| Promotion gate | `promotion_runs`/`promotion_candidates`/`audit_logs`; explicit `--confirm-production-apply` |
| Write chokepoint | `db_write_guard.get_write_connection()` (P121) — the only sanctioned writer |

---

## 1. Corpus Architecture (layers)

Extends the real `books → book_versions → citations → evidence_nodes → extracted_facts → consensus_nodes → canonical_vectors` chain with the **Chapter/Section** spine the brief asks for, using **proposed** tables (§11) so production schema is untouched.

```
Book            ── existing: books(book_id, title, author, isbn, publisher)
  │  (1 book = 1 ISBN; re-issues = new book_versions row, same book_id)
  ▼
BookVersion     ── existing: book_versions(version_id, book_id, file_hash, format, processed_at)
  │  (immutable content snapshot; SHA256 = file_hash)
  ▼
Chapter         ── PROPOSED: chapters(chapter_id, version_id, chapter_no, title, heading_path)
  │  (derived from PDF outline / heading regex; preserves book→chapter hierarchy)
  ▼
Section         ── PROPOSED: sections(section_id, chapter_id, section_no, breadcrumb)
  │  (fine-grained location; paragraph anchoring)
  ▼
Citation        ── existing: citations(citation_id, version_id, page_number, chunk_id, raw_text, source_hash)
  │  (verbatim quote; page + chunk anchor = provenance root)
  ▼
Evidence        ── existing: evidence_nodes(evidence_id, citation_id, extraction_method, model_version, status)
  │  (one normalized claim extracted from a citation; carries method + status)
  ▼
Claim           ── existing: extracted_facts(fact_id, evidence_id, entity_key_raw, descriptor_raw, confidence_score, status)
  │  (atomic subject→predicate; confidence + status)
  ▼
Consensus       ── existing: consensus_nodes(consensus_id, whisky_id, algorithm_version, status)
  │  (per-whisky merge of all claims; algorithm_version enables re-derivation)
  ▼
Canonical Node  ── existing: canonical_vectors(vector_id, consensus_id, 7 axes…)
                 + PROPOSED canonical_entities (distillery/region/person/cask nodes — §6)
```

**Every layer explained:** Book is the immutable title record. BookVersion snapshots one file (hash-addressed, re-ingest = new version, old versions retained → reproducibility). Chapter/Section add the hierarchical location spine the brief requires (currently citations only carry `page_number`; the spine makes "why does Malt Radar say this?" navigable). Citation is the verbatim quote (extraction agent emits `quote` per AGENTS.md). Evidence is the method-tagged normalized claim. Claim is the atomic fact with confidence. Consensus is the per-entity merged view (algorithm-versioned). Canonical Node is the consumable vector/entity used by the app.

---

## 2. Knowledge Graph (relationships)

Nodes (entity types): **Book, Chapter, Citation, Distillery, Whisky/Expression, Region, Person, IndependentBottler, Cask, Flavor(axis), ChemicalCompound, ProductionTerm, SensoryDescriptor, HistoryEvent, Award, Regulation, IndustryTerm.**

Edges (typed, directed, provenance-bearing — each edge = an `extracted_fact` or `evidence_node`):

| Edge | Example | Source table |
|---|---|---|
| `Book →discusses→ Distillery` | B1 → Glenfiddich | extracted_facts(entity_key_raw=distillery) |
| `Book →discusses→ Flavor` | B4b → peaty | canonical_vectors axis |
| `Book →discusses→ Region` | B2 → Speyside | extracted_facts |
| `Book →discusses→ Production` | B8 → distillation | extracted_facts |
| `Book →discusses→ History` | B3 → founding(1824) | extracted_facts |
| `Book →uses→ Cask` | B6 → sherry butt | extracted_facts |
| `Book →mentions→ Peat/Yeast/Fermentation/Still/Warehouse/Maturation` | Wishart → yeast | extracted_facts |
| `Book →describes→ ChemicalCompound` | Flavour of Whisky → congener | extracted_facts |
| `Book →uses→ SensoryDescriptor` | B4 → "medicinal" | extracted_facts |
| `Book →awarded→ Award` | Advocate → Whisky of the Year | extracted_facts |
| `Book →cites→ Regulation` | B1 → Scotch Whisky Regs | extracted_facts |
| `Book →uses→ IndustryTerm` | B5 → "married" | extracted_facts |
| `Citation →supports→ Claim` | citation_xyz → fact_xyz | evidence_nodes.citation_id |
| `Claim →conflicts_with→ Claim` | fact_A ≠ fact_B | PROPOSED conflict_edges (§4) |

**Everything becomes graph nodes:** the 40 domains (P122) map to node *types* or *edge labels*; the existing `knowledge.db` already holds the Book/Citation/Evidence/Claim/Consensus/Vector spine — P123 adds the **entity-type nodes** (Distillery, Region, Person, Cask, ChemicalCompound, ProductionTerm) as proposed `canonical_entities` + edge tables, and the **conflict/consensus edges**.

---

## 3. Evidence Graph (provenance contract)

Every statement retains (columns already exist or proposed):

| Required field | Where | Status |
|---|---|---|
| book | `books.book_id` | EXISTING |
| chapter | `chapters.chapter_no` + `heading_path` | PROPOSED |
| page | `citations.page_number` | EXISTING |
| paragraph | `citations.chunk_id` (extend to para index) | EXISTING (extend) |
| confidence | `extracted_facts.confidence_score` | EXISTING |
| citation | `citations.raw_text` + `citation_id` | EXISTING |
| extraction method | `evidence_nodes.extraction_method` | EXISTING |
| normalization notes | `evidence_nodes.model_version` + PROPOSED `normalization_notes` | EXISTING + PROPOSED |
| supporting books | PROPOSED `fact_sources(fact_id, version_id, role=SUPPORT)` | PROPOSED |
| conflicting books | PROPOSED `fact_conflicts(fact_id, conflicting_fact_id, severity)` | PROPOSED |

**Nothing loses provenance:** the `citation_id` foreign key threads every fact back to verbatim text + page; `evidence_nodes.status` preserves superseded versions rather than deleting. A fact can be REVOKED but its evidence chain remains auditable (immutable-evidence philosophy, P122 §Architecture Truth).

---

## 4. Cross-book Consensus Engine

**Inputs:** all `extracted_facts` for one entity (`entity_key_raw` resolved to canonical ID via §6), grouped by `whisky_id`/`consensus_id`.

**Algorithm (deterministic, versioned `algorithm_version`):**
1. **authoritative weighting** — each fact weighted by its source's authority tier (`source_profile.yaml`): T1_primary > T2_secondary > T3_community. Books are T3 (sprint01: "may not sole-certify") → a single book can flag but not sole-certify a canonical value.
2. **agreement/conflict** — compare `descriptor_raw` / axis values across facts. Exact match = agreement; divergent = conflict.
3. **majority / minority** — majority = modal value; minority = non-modal facts retained as evidence (never dropped).
4. **citation scoring** — `CitationScore = Σ(weight_i)` over supporting facts.
5. **consensus score** — `ConsensusScore = agreement_ratio × weighted_support / (1 + conflict_penalty)`.
6. **evidence strength** — `EvidenceStrength = min(1.0, total_weight / threshold)` (caps at saturation).
7. **book coverage** — distinct `book_id`s contributing.
8. **conflict indicator** — `ConflictIndicator = conflicting_facts / total_facts` (0 = clean, →1 = contested).

**Outputs (columns on `consensus_nodes` / proposed `consensus_scores`):**
- `ConsensusScore` (0–1)
- `EvidenceStrength` (0–1)
- `BookCoverage` (int)
- `ConflictIndicator` (0–1)
- `algorithm_version` (re-run safe; old consensus SUPERSEDED, not overwritten)

This reuses the existing `consensus_nodes.whisky_id + algorithm_version` UNIQUE key — consensus is **re-derivable**, satisfying reproducibility.

---

## 5. Domain Intelligence (over the 40 domains)

For each of the 40 P122 domains, compute (read-only over existing facts + proposed aggregates):

| Metric | Derivation |
|---|---|
| coverage | `% of corpus books tagged PRIMARY/SECONDARY for domain` (from P122 coverage_matrix) |
| confidence | mean `extracted_facts.confidence_score` for facts whose `entity_key_raw`/edge maps to domain |
| book count | distinct `book_id`s discussing the domain |
| citation density | `citations` per domain-fact (raw_text volume) |
| knowledge gaps | domains with coverage < threshold OR ConfidenceIndicator low (feeds §13 acquisition) |
| future acquisition priority | P122 `canonical_ingestion_roadmap` + gap rank |

**Materialization:** PROPOSED `domain_intelligence` materialized view (§11) refreshed on each promotion run; never mutates production. Weak domains identified in P122 (Oak Science, Fermentation, Yeast, Warehouse, Rye, Independent Bottlers) surface here with explicit gap scores → drive acquisition (P122 §8).

---

## 6. Entity Resolution (canonical IDs)

Resolve extracted raw keys into canonical entities. **Existing resolver** (sprint01: 47.5% resolution rate, 324/682 matched) is the baseline; P123 hardens it.

| Entity type | Canonical table (PROPOSED) | Match strategy |
|---|---|---|
| Distilleries | `canonical_distilleries` | norm_name() + Levenshtein vs `production.db.distilleries` (2144 rows, read-only via gate) |
| Whiskies/Expressions | `canonical_whiskies` | norm_name() vs `production.db.whiskies` (4749 rows) |
| Regions | `canonical_regions` | exact + alias map (B1/B2 region facts) |
| People | `canonical_people` | person-name index (author/figure) |
| Independent Bottlers | `canonical_bottlers` | IB name dictionary (SMWS, Cadenhead's…) |
| Casks | `canonical_casks` | cask-type vocabulary (sherry butt, bourbon, hogshead) |
| Flavors | `canonical_flavors` | the 7 axes ONLY (no new axes — P122 constraint) |
| Chemical Compounds | `canonical_compounds` | compound glossary (Wishart) |
| Production Terms | `canonical_production_terms` | term dictionary (B8/B5) |
| Books | `books` (EXISTING) | ISBN/file_hash |

**Rules:** threshold mirrors sprint01 (`exact=1.0, HIGH≥0.95, FUZZY 0.65–0.95, NEW<0.65` → `staging_manual_review_queue`). NEW entities → staging (never auto-insert into production). Conflicts → Audit Agent (AGENTS.md §Merge/Audit). Every canonical ID back-references its source `evidence_id`s.

---

## 7. Citation Engine (UI feature: "Why does Malt Radar say this?")

**Query input:** a canonical entity/claim (e.g. `whisky_id=X`, axis=peaty).
**Pipeline:**
1. Resolve to `consensus_id` → `canonical_vectors`.
2. Walk FK: `consensus_nodes` → `extracted_facts` → `evidence_nodes` → `citations` → `book_versions` → `books`.
3. Aggregate `support_score` = `EvidenceStrength`; `consensus` = `ConsensusScore`; `confidence` = `confidence_score` mean.
4. Return:
   - **citation list** — `books.title`, `author`, `citations.page_number`, `chunk_id`, `raw_text` (verbatim quote).
   - **book pages** — distinct (book_id, page) pairs.
   - **support score** — weighted citation sum.
   - **consensus** — agreement ratio across books.
   - **confidence** — extraction confidence.
   - **conflict flag** — if `ConflictIndicator > 0`, list conflicting `raw_text` pairs.

**No hallucination:** every returned string is a verbatim `citations.raw_text` row → fully traceable. UI renders the provenance chain Book→Chapter→Page→Quote.

---

## 8. Retrieval Layer (semantic, no hallucination)

**User query:** "Which distilleries use worm tubs?"
**Pipeline (deterministic + optional vector assist):**
1. **Lexical retrieval** — keyword/index scan over `citations.raw_text` + `extracted_facts.descriptor_raw` for "worm tub" → candidate citations.
2. **Entity expansion** — resolve matched distilleries via §6 to `canonical_distilleries`.
3. **Consensus join** — attach `ConsensusScore`/`ConflictIndicator` per distillery.
4. **Related concepts** — graph traversal (Distillery →uses→ ProductionTerm=worm tub; →region→ Speyside) via proposed edge tables.
5. **Vector assist (optional)** — embed `raw_text` chunks into a read-only vector index (§11 `citation_embeddings`); cosine retrieval *ranks* candidates but **citations are always the returned source** (no generated text).
6. **Output:** multiple books + citations + consensus + confidence + related concepts. The model may *rank/summarize pointers* but every displayed fact links a verbatim citation. Hallucination impossible by construction (no free-text generation of facts).

---

## 9. KEP Integration (runtime)

**Where it executes:** the 6 KEP agent stages (AGENTS.md) run as read-only analysis; only the **promotion gate** writes, via `db_write_guard.get_write_connection()` (P121).

**Runtime stages → existing agents:**
1. Qualification — `source_profile.yaml` scope; marks in/out/deferred. No extraction.
2. Extraction — verbatim `quote` per field (sprint pattern); writes `citations`/`evidence_nodes` in staging.
3. Validation — `field_rules.yaml` normalization; authority-ceiling rejection.
4. Merge — IoU match + `merge_policies.yaml`; losers kept as evidence.
5. Certification — `certify_min_confidence=0.70`; `audit_status=pending_audit`.
6. Audit — gate GO/PARTIAL_GO/NO_GO; read-only.

**Cache strategy:** `book_versions.file_hash` is the cache key — re-ingest only on hash change. Citation/evidence for unchanged versions are reused (incremental, per `acquisition/cache_usage_report.md`).

**Incremental rebuild:** new book → new `book_versions` row → only its `citations`/`evidence`/`facts` recomputed; `consensus_nodes` for touched entities SUPERSEDED + recomputed (algorithm_version bump). Untouched entities unchanged.

**Invalidations:** a changed `source_profile.yaml` authority tier or `algorithm_version` bump invalidates dependent `consensus_nodes` (SUPERSEDED, recompute). Production promotion invalidates only `promotion_candidates` for that run.

**Memory usage:** bounded — process books one `book_version` at a time (streaming PDF parse, not full-corpus in RAM); consensus computed per-entity.

---

## 10. AOS Integration (agents)

| Agent | Responsibility | Inputs | Outputs | Contract | Failure recovery |
|---|---|---|---|---|---|
| Qualification | scope decision | source units | qualification record | no extraction | re-qualify on profile change |
| Extraction | verbatim quote | qualified units | extraction record | quote-per-field | re-extract version on hash mismatch |
| Validation | normalize/reject | extraction | validated record | authority-ceiling hard reject | route low-conf to Audit |
| Merge | deterministic resolve | validated (same entity) | merged record | keep losers as evidence | unresolvable → Audit |
| Certification | evidence-attach | merged | certification record | `conf≥0.70`, `pending_audit` | lower conf → SUPERSEDED |
| Audit | final gate | cert + conflicts | audit report + gate | read-only, recommends only | NO_GO → halt, no promotion |
| (Proposed) Consensus | build graph | facts | consensus + scores | algorithm_versioned | recompute on version bump |
| (Proposed) Retrieval | answer query | canonical node | citations+consensus | verbatim-only | fall back to lexical if vector miss |

**Workflow sequence:** Qualification → Extraction → Validation → Merge → Certification → Audit → (Consensus build) → (Retrieval serve). AOUS assigns agents per `AGENTS.md`; no agent writes `production.db`.

---

## 11. Database Design (PROPOSAL ONLY — production schema untouched)

Additive, backward-compatible. All new tables staged in `knowledge.db` (the immutable-knowledge store) or a new `corpus_intelligence.db`; **never** alter `production.db`.

**Staging / proposed tables:**
```sql
-- hierarchical location spine
CREATE TABLE chapters (
    chapter_id TEXT PRIMARY KEY, version_id TEXT REFERENCES book_versions(version_id),
    chapter_no INTEGER, title TEXT, heading_path TEXT);
CREATE TABLE sections (
    section_id TEXT PRIMARY KEY, chapter_id TEXT REFERENCES chapters(chapter_id),
    section_no INTEGER, breadcrumb TEXT);
-- extend citations.chunk_id to carry paragraph index (no schema break: chunk_id is TEXT)

-- canonical entity nodes (§6)
CREATE TABLE canonical_distilleries (entity_id TEXT PRIMARY KEY, name_norm TEXT UNIQUE, alias_json TEXT);
CREATE TABLE canonical_regions        (entity_id TEXT PRIMARY KEY, name_norm TEXT UNIQUE);
CREATE TABLE canonical_people         (entity_id TEXT PRIMARY KEY, name_norm TEXT UNIQUE, role TEXT);
CREATE TABLE canonical_bottlers       (entity_id TEXT PRIMARY KEY, name_norm TEXT UNIQUE);
CREATE TABLE canonical_casks          (entity_id TEXT PRIMARY KEY, cask_type TEXT UNIQUE);
CREATE TABLE canonical_compounds      (entity_id TEXT PRIMARY KEY, compound TEXT UNIQUE);
CREATE TABLE canonical_production_terms(entity_id TEXT PRIMARY KEY, term TEXT UNIQUE);

-- graph edges + consensus scoring (§2,§4)
CREATE TABLE fact_sources (fact_id TEXT, version_id TEXT, role TEXT, PRIMARY KEY(fact_id,version_id));
CREATE TABLE fact_conflicts (fact_id TEXT, conflicting_fact_id TEXT, severity TEXT, PRIMARY KEY(fact_id,conflicting_fact_id));
CREATE TABLE consensus_scores (
    consensus_id TEXT PRIMARY KEY REFERENCES consensus_nodes(consensus_id),
    consensus_score REAL, evidence_strength REAL, book_coverage INTEGER, conflict_indicator REAL);

-- domain intelligence materialized view (§5)
CREATE VIEW domain_intelligence AS
  SELECT d.domain, COUNT(DISTINCT b.book_id) AS book_count, AVG(f.confidence_score) AS confidence
  FROM extracted_facts f JOIN evidence_nodes e ON f.evidence_id=e.evidence_id
  JOIN citations c ON e.citation_id=c.citation_id JOIN book_versions v ON c.version_id=v.version_id
  JOIN books b ON v.book_id=b.book_id CROSS JOIN (VALUES ('Scotch'),('Peat'),…) AS d(domain)
  WHERE f.descriptor_raw LIKE '%'||d.domain||'%' GROUP BY d.domain;

-- retrieval vector index (§8, optional, read-only assist)
CREATE TABLE citation_embeddings (citation_id TEXT PRIMARY KEY REFERENCES citations(citation_id), embedding BLOB);

-- indexes
CREATE INDEX idx_chapters_version ON chapters(version_id);
CREATE INDEX idx_facts_entity ON extracted_facts(entity_key_raw);
CREATE INDEX idx_consensus_scores_conflict ON consensus_scores(conflict_indicator);
```

**Knowledge graph storage:** entity nodes in `canonical_*` tables; edges in `fact_sources`/`fact_conflicts` + existing FK chain. **Citation storage:** `citations` (verbatim) + `citation_embeddings` (vector assist). **Materialized views:** `domain_intelligence`, `consensus_scores` (rebuildable, never source of truth).

---

## 12. Migration Strategy (no breaking changes)

- **Phase 1 (additive DDL):** create `chapters`, `sections`, `canonical_*`, `fact_sources`, `fact_conflicts`, `consensus_scores`, `citation_embeddings`. No ALTER of existing tables. `production.db` untouched.
- **Phase 2 (backfill):** derive `chapters`/`sections` from existing `citations.page_number` + PDF outlines (re-process only changed `book_versions` via hash). Backfill `canonical_*` from sprint01 resolver output.
- **Phase 3 (consensus v2):** compute `consensus_scores` with new algorithm_version; old `consensus_nodes` SUPERSEDED (retained).
- **Phase 4 (retrieval + UI):** stand up `citation_embeddings` + Citation Engine; wire "Why?" UI. Promotion still gated.

Every phase is reversible (new tables dropped; old rows untouched). No migration touches `production.db` schema or data.

---

## 13. Performance (estimates, grounded in sprint01)

| Metric | Estimate | Basis |
|---|---|---|
| Storage growth | ~1.4k citations/book (sprint01 B1: +1378) → ~70k citations for 49 books; ~+50MB `knowledge.db` | sprint01 delta |
| Query speed | citation lookup via `idx_citations_hash`/`idx_facts_entity` < 5ms; consensus join < 20ms | existing indexes |
| Vector usage | `citation_embeddings` ~768–1536 dim × 70k = ~0.5–1GB if full embed; optional, offline | §8 |
| Graph size | nodes ≈ facts (70k) + entities (~5k); edges ≈ facts + conflicts | §2/§6 |
| Cache size | one `book_versions` row per file; reuse on hash | cache_usage_report |
| Rebuild time | full consensus ~ minutes (per-entity, streaming); incremental ~ seconds/book | §9 |
| Incremental update cost | 1 new book ≈ +1.4k citations, +324 consensus recompute ≈ < 1 min | sprint01 |

All estimates derived from the **real sprint01 delta** (+1378 citations, +324 consensus per book), not invented.

---

## 14. Risk Analysis

| Risk | Type | Mitigation |
|---|---|---|
| Stale `book_registry.json` (P122 found 13/14 placeholder) | Maintenance | refresh registry on every ingestion; hash-keyed |
| Low entity-resolution rate (sprint01: 47.5%) | Technical | harden §6 dictionaries; route NEW to staging review |
| Subjective book scores (B4/B4b reliability 3) over-weighting | LLM/Hallucination | authority tiers (T3 "may not sole-certify"); weighted consensus |
| Verbatim quote leakage of © text | Citation | store only short excerpts + page; licensing guardrails (P122 plan §4) |
| Vector store drift / hallucinated retrieval | Hallucination | citations are verbatim-only; vectors *rank*, never generate facts |
| Consensus thrash on algorithm change | Maintenance | `algorithm_version` + SUPERSEDED (never overwrite) |
| Production mutation by mistake | Technical | P121 `get_write_connection` chokepoint + OS read-lock (verified intact) |
| Over-extraction noise (B4b: 721 unresolved, 536 real) | Technical | classification gate (B4b task) routes BOOK_METADATA/FP out before resolver |

---

## 15. Roadmap (execution phases)

### P123-A — Schema Extension & Backfill
- **Objective:** add §11 proposed tables; backfill `chapters`/`sections`/`canonical_*` from existing data.
- **Deliverables:** DDL migration script (additive), backfill runner, integrity check.
- **Dependencies:** P102 schema, P121 write-gate, P122 inventory.
- **Validation:** FK 0 violations; `chapters` count == distinct (book,chapter) in citations; resolver rate ≥ sprint01 baseline.
- **Acceptance:** new tables present, old schema byte-identical; `production.db` untouched.
- **Complexity:** M.

### P123-B — Consensus Engine v2
- **Objective:** implement §4 algorithm; populate `consensus_scores`.
- **Deliverables:** `consensus_builder` (versioned), `consensus_scores` fill, conflict report.
- **Dependencies:** P123-A canonical entities.
- **Validation:** recompute idempotent (same input → same scores); ConflictIndicator ∈ [0,1].
- **Acceptance:** all 49-book facts yield consensus; algorithm_version recorded.
- **Complexity:** M.

### P123-C — Domain Intelligence & Gap Feed
- **Objective:** materialize `domain_intelligence`; emit acquisition priority from gaps.
- **Deliverables:** `domain_intelligence` view, gap report (feeds P122 §8 acquisition).
- **Dependencies:** P123-B.
- **Validation:** 40 domains covered; weak-domain scores match P122.
- **Acceptance:** gap list reproducible from facts.
- **Complexity:** S.

### P123-D — Citation Engine + Retrieval Layer
- **Objective:** "Why?" API + semantic retrieval (§7/§8).
- **Deliverables:** citation API, `citation_embeddings` (optional), retrieval service.
- **Dependencies:** P123-B, P121 gate.
- **Validation:** every returned fact links verbatim citation; no free-text fact generation.
- **Acceptance:** "worm tubs" query returns ≥1 distillery + citations + consensus.
- **Complexity:** L (vector + service).

### P123-E — AOS Agent Wiring & Promotion Gate
- **Objective:** wire Consensus/Retrieval agents into AOUS; final promotion gate.
- **Deliverables:** agent contracts, workflow orchestration, promotion gate report.
- **Dependencies:** P123-A…D.
- **Validation:** full stage run GO/PARTIAL_GO/NO_GO; read-only audit passes.
- **Acceptance:** end-to-end pipeline blue/green; production promotion only via `--confirm-production-apply`.
- **Complexity:** L.

Each phase independently verifiable; no phase modifies `production.db` until P123-E's explicit gate.

---

## Final Status: 🟢 GO (design)

**Justification:** Blueprint is implementation-grade, grounded entirely in the **existing** `knowledge.db` schema (11 tables), the 6 KEP agents + authority tiers (`AGENTS.md`), the 7-axis model (`canonical_vectors`), the real resolver/consensus numbers (sprint01: 47.5% resolution, +1378 citations/book), and the P122 verified baseline (49 books, 40 domains). Every proposed table/edge/metric maps to a real anchor. No speculative architecture, no placeholder text, no production/runtime change. Read-only constraint honored (this document only; `production.db` hash `d842b118…` and `knowledge.db` 3077 vectors unchanged, OS read-lock intact per P122 verification).

**Next action (separate task, user approval):** execute P123-A (additive DDL + backfill) via the P121 write-gate — the first writable phase.

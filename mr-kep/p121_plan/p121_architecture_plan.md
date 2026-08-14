# P121 — KEP Productionization Architecture Plan

## 1. Current State

### Problem
KEP is architecturally specified but not operational for real data. Multiple standalone pipelines exist, each reinventing the same stages. The canonical KEP pipeline runs on test fixtures only.

### Root Cause
No **Source Adapter Contract** normalizes diverse source types into a single pipeline format. No **Promotion Gate** writes certified output to any database. Every new source builds its own pipeline.

### Target Architecture

```
SOURCE LAYER                        PIPELINE LAYER                  STORAGE LAYER
──────────────────────────────────  ──────────────────────────────  ────────────────────

[SMWS PDFs] ──→ Source Adapter ──┐
[Books]      ──→ Source Adapter ──┤
[Retail CSV] ──→ Source Adapter ──┼──→ KEP Pipeline ──→ Promotion Gate ──→ knowledge.db
[Web Review] ──→ Source Adapter ──┤                                        ──→ production.db
[NotebookLM] ──→ Source Adapter ──┘
                                  ↑
                     Source Adapter Contract
                     (normalized Fixture JSON)
```

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Single pipeline entry point | `pipeline/run_pipeline()` | Already exists, works, deterministic |
| Target database | `knowledge.db` (primary) | Already contains 13K+ facts from book sprints; schema proven in production |
| Promotion to production | `production.db` via future gate | Production promotion is a separate concern; knowledge.db is the enrichment store |
| Entity resolution | Shared service (not per-source) | Currently 4+ implementations giving different results |
| Flavor canonicalization | D4 reducer (refactored) | Already proven for 7-axis mapping |

---

## 2. Source Adapter Contract

### Interface: What every adapter must produce

```python
@dataclass
class SourceFixture:
    """Normalized input to run_pipeline()."""
    document_id: str               # deterministic hash
    source_key: str                # from authority/source_priority.yaml
    surface_signals: dict          # url, mime_type, filename, title, whisky_hint
    extracted_fields: dict         # raw values: {field_name: value}
    flavor_axes: dict | None       # {axis_name: 0-100} if applicable
    raw_text: str | None           # for evidence quotes
    authority_tier: str            # T1/T2/T3
    evidence_type: str             # expert_quote / primary_source_quote / etc.
```

### Required Adapters

| Source Type | Priority | Existing Code | Reusable? |
|---|---|---|---|
| **SMWS PDF** | HIGH | `p119_smws_extraction/raw_extractions.csv` | Partial — extraction logic is not committed; would need a PDF→fixture script |
| **Book PDF/EPUB** | HIGH | Book enrichment sprints' `extract_entities()` | Yes — refactor into reusable adapter module |
| **Retail CSV** | MEDIUM | Structured Source Intake CSVs | Yes — generic CSV→fixture parser |
| **Web Review** | MEDIUM | `acquisition/adapters/*` (dead code) | No — interfaces exist but never wired; needs real HTTP + parser |
| **NotebookLM** | LOW | Output in non-canonical 16-20 axis format | Needs 20-axis→7-axis reducer (D4 reducer can do this) |

---

## 3. Pipeline Integration

### What changes in the KEP pipeline

| Component | Change | Impact |
|---|---|---|
| `pipeline/run.py` | Accept `SourceFixture` objects directly (not just fixture file path) | Backward-compatible; file path still works |
| `qualification_engine/` | No change — already accepts `source_key + surface_signals` | Already correct |
| `evidence_engine/` | No change — already produces P64-compatible evidence from qualification | Already correct |
| `certification_engine/` | No change — already applies paths A-F | Already correct |
| `pipeline/run_batch_csv()` | Expand to accept any adapter output (not just CSV) | Needs interface update |
| **Entity Resolution** | Extract from inline book sprint code → shared module | **Major refactor** (see resolver_consolidation_plan.md) |

### What must be REMOVED from the pipeline

| Item | Reason |
|---|---|
| `run_batch_csv()` data extraction logic | Merges extraction into pipeline — should be separated per adapter pattern |
| Hardcoded `SOUCE-P76` in `run_batch_csv()` | Source key must come from the adapter, not be hardcoded |

---

## 4. Promotion Gate Design

### Function
After `pipeline/run_pipeline()` produces `certification.json` + `canonical_output.json`, the Promotion Gate:

1. Reads certification state per field (certified / proposed / rejected)
2. For each **certified** field: writes to knowledge.db
3. For **proposed** fields: writes to knowledge.db with `audit_status=pending_audit`
4. For **all** fields: writes evidence to evidence_nodes + citations
5. Reports: count of certified vs proposed vs rejected

### Target: knowledge.db tables

| KEP Artifact | knowledge.db Table | Status |
|---|---|---|
| `evidence_ledger` entries | `citations` + `evidence_nodes` | Both exist, exact schema TBD |
| `extracted_fields` | `extracted_facts` | Exists |
| `certification` per-field consensus | `consensus_nodes` | Exists |
| `canonical_output.flavor_axes` | `canonical_vectors` | Exists |
| Promotion candidates | `promotion_candidates` | Exists |

### Detailed design in `promotion_gate_design.md`

---

## 5. Migration Phases

```
PHASE 1: Adapter Layer (greenfield)
  ├── SourceAdapter base class + contract
  ├── SMWS adapter (recover P119 extraction logic)
  ├── Book adapter (refactor enrichment_01 extract_entities)
  └── CSV adapter (generic structured data intake)

PHASE 2: Entity Resolution Consolidation
  ├── Canonical EntityResolver class (shared service)
  ├── Production.db lexicon loader (reuse from enrichment_01)
  └── Fuzzy matching + SMWS code resolution

PHASE 3: Promotion Gate
  ├── knowledge.db writer (reuse from save_to_knowledge_db)
  ├── production.db writer (gated, require confirm phrase)
  └── Delta report generator

PHASE 4: Pipeline Wiring
  ├── Adapter → pipeline → promotion gate (end-to-end)
  ├── Batch orchestrator (process N sources)
  └── Retire standalone enrichment sprints
```

---

## 6. Files That Change

| File | Action |
|---|---|
| `mr-kep/pipeline/run.py` | MODIFY — accept SourceFixture, add promotion gate call |
| `mr-kep/pipeline/promotion_gate.py` | CREATE — new module |
| `mr-kep/resolution/entity_resolver.py` | CREATE — canonical resolver |
| `mr-kep/source_adapters/base_adapter.py` | CREATE — adapter contract |
| `mr-kep/source_adapters/smws_adapter.py` | CREATE — SMWS PDF → fixture |
| `mr-kep/source_adapters/book_adapter.py` | CREATE — book PDF → fixture |
| `mr-kep/source_adapters/csv_adapter.py` | CREATE — retail CSV → fixture |
| `mr-kep/acquisition/run_pipeline.py` | REMOVE or DEPRECATE — simulated pipeline |
| `mr-kep/p96_pipeline/` | REMOVE or DEPRECATE — superseded |
| `book_enrichment_sprint0*/*.py` | NO CHANGE until migration — leave as-is until adapters proven |

### Files that do NOT change

- `authority/` — frozen contracts
- `schemas/` — frozen JSON schemas
- `evidence/` — frozen evidence spec
- `certification_engine/` — works correctly
- `qualification_engine/` — works correctly
- `evidence_engine/` — works correctly

# KEP Runtime Verification Report — P120 Audit

## 1. Is KEP Fully Operational?

**NO — KEP is architecturally defined but NOT fully operational.**

The canonical Sprint 2 pipeline (qualification → evidence → execution → certification → canonical output) has:
- ✅ Working engine implementations (every stage has valid code)
- ✅ Real schemas and authority contracts
- ✅ Deterministic, read-only, evidence-first design
- ❌ **Never processes real source data** — only test fixtures (`fixtures/sample_whisky.json`)
- ❌ **No promotion gate** — certified output (certification.json, canonical_output.json) never reaches any database
- ❌ **No live acquisition** — the acquisition pipeline is a simulation with hardcoded metrics

### What IS operational:
- **Book Enrichment Sprints** (Sprint 01–09) — these ARE real data pipelines, but they are standalone scripts that bypass KEP entirely
- **Structured Source Intake** (Vinmonopolet, Alko, HTFW, WhiskyNotes) — retail data piped directly to knowledge.db
- **D4 Reducer** — canonical 7-axis flavor mapping (standalone)

### The problem:
The data flows that work (books, retail) don't use KEP at all.
The KEP pipeline that exists has never been fed real data.
Every ingestion path reinvented its own pipeline instead of using the canonical one.

---

## 2. Which Stage Is the Weakest Link?

### 🔴 PROMOTION / WRITE GATE (Stage 6 — missing entirely)

The canonical KEP pipeline ends at `canonical_output.json`. There is **no stage that writes certified results to knowledge.db or production.db**. The file `pipeline/run.py` has no promotion step. The `certification_engine/__init__.py` comments explicitly say: *"Does NOT write production. Promotion only on a later explicit apply gate (read-only verification)."*

That gate was **never built**.

### 🔴 ACQUISITION (Stage 0 — simulated only)

The acquisition pipeline (`mr-kep/acquisition/`) has real module interfaces but:
- `run_pipeline.py` hardcodes every metric
- Only 3 mock URLs ever processed
- No real HTTP fetches
- Content cache never persisted
- Adapters (MasterOfMalt, Whiskybase, WhiskyNotes) exist but are never wired

### 🔴 ENTITY RESOLUTION (recurring failure)

Entity resolution is reimplemented in **at least 4 places**:
1. `evidence_engine/engine.py` — `resolve_source()` maps source_key → authority_tier
2. `p96_pipeline/entity_resolver.py` — its OWN resolver
3. Book enrichment sprints — inline resolution against production.db
4. P119 SMWS — its own resolution (only 1/792 succeeded)

The P119 failure rate (791/792 unresolved) shows that entity resolution is the hardest problem, and having 4 different implementations makes it worse — they all disagree.

---

## 3. Can Every Future Source Flow Through ONE Canonical Pipeline?

**NO — not without changes.**

### Required Capabilities That Do NOT Exist

| Missing Capability | Blocked Sources |
|---|---|
| **Real HTTP/Monitoring** — live acquisition from web URLs → any web source | WhiskyFun, Malt-Review, Dramface, retail sites |
| **PDF/EPUB→Structured Entity extraction** — generic extraction for books (current book sprints use hand-written per-book code) | Books (currently per-source scripts, not a generic pipeline) |
| **Deterministic entity resolution against production.db** (working for books, failed for SMWS) | SMWS (1/792 → any code name–only source) |
| **Promotion gate** — certified output → database write | ALL sources (the canonical pipeline's output has no destination) |
| **Multi-source consensus** — merging evidence from multiple sources for the same entity | Any whisky with >1 source (currently each source writes independently to knowledge.db) |

### Current Source-Specific Blockers

| Source | Can Flow Through KEP? | Blocker |
|---|---|---|
| **Books** | Partial — would need PDF→entity extraction stage | Book sprints must be refactored to feed into KEP instead of writing directly to knowledge.db |
| **SMWS** | No — would need entity resolution improvement | 99.9% unresolved rate makes the pipeline useless for SMWS code names |
| **Retail CSVs** | Partial — structured DataSource → CSV intake → KEP | Would need a CSV→fixture bridge |
| **Web sources** | No — no live HTTP acquisition | Acquisition pipeline is simulated |
| **NotebookLM** | No — no intake path | Output targets a non-canonical 16-20 axis flavor schema |

### The One Missing Link

A single **KEP Adapter Interface** that normalizes ANY source (book PDF, SMWS archive, retail CSV, web review, NotebookLM export) into the fixture format that `pipeline/run_pipeline()` expects, followed by a **Promotion Gate** that writes certified output to `knowledge.db` or `production.db`.

Without that interface, every new source will continue to spawn its own standalone pipeline (the pattern seen across P45, P96, P119, book sprints, structured source intake, acquisition).

---

## Verdict Summary

| Question | Answer |
|---|---|
| Is KEP fully operational? | **NO** — engines work but pipeline ends at output files with no real data path |
| Weakest link? | **Promotion Gate (missing)** + **Entity Resolution (fragmented)** |
| One canonical pipeline possible? | **NO** — needs (1) Source Adapter Interface, (2) Promotion Gate, (3) Unified Entity Resolution, (4) Live Acquisition |

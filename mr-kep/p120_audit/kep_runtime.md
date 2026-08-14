# KEP Runtime Status — P120 Audit

## Current State: Non-functional for Real Data

The KEP (Knowledge Extraction Pipeline) is a well-specified architectural framework with
working engine implementations, but it has NEVER been executed against real source data.

---

## Architecture: Two Worlds

### World A: The KEP Pipeline (designed, never deployed)

```
Source → Qualification → Evidence → Execution → Certification → Canonical Output → [no write gate]
```

- 5 working engines with real code
- Deterministic, evidence-first design
- Authority model with 3 tiers, 5 merge policies, 6 certification paths
- Targets: 7 canonical flavor axes, P65 canonical output schema
- **Status: Test-only.** Only ever run against `fixtures/sample_whisky.json`
- **Weakest link: No promotion gate.** Certified output has no destination.

### World B: Real Data Pipelines (deployed, never through KEP)

Book enrichment sprints, structured source intake, and P119 SMWS extraction each built their own pipeline logic:
- Own entity resolution (4 different implementations)
- Own consensus building (2 different implementations)
- Own vector generation (3 different implementations)
- Own database loaders (each sprint writes differently)

**Status: Real data, duplicated logic, no shared framework.**

---

## Critical Path Item: P119/P120 SMWS Orphan

P119 extracted 803 SMWS PDFs → 792 expressions with 7-axis flavor vectors.
P120 claimed "successful promotion" — **but the data never reached any database.**

| Artifact | Location | Exists? |
|---|---|---|
| Raw extractions | `p119_smws_extraction/raw_extractions.csv` | ✅ 792 rows |
| Resolved entities | `p119_smws_extraction/resolved_entities.csv` | ✅ 1 resolved |
| Flavor vectors | `p119_smws_extraction/canonical_vectors_staging.csv` | ✅ 792 vectors |
| Promotion | `p120_smws_promotion/promotion_ready.csv` | ✅ CSV file |
| In knowledge.db | `p102_bootstrap/knowledge.db` | ❌ ZERO rows |
| In production.db | `output/import/production.db` | ❌ ZERO rows |

The extraction scripts that generated this data are **not committed** to the repository.
The pipeline that produced the output is unreproducible.

---

## What Would Need to Change for KEP to Be Fully Operational

### Hard Requirement: Promotion Gate
File: `mr-kep/certification_engine/__init__.py` line 260+: *"Does NOT write production."*
This was intentional design (deferred gate) but the gate was never implemented.
Needed: `promotion_gate.py` that takes canonical_output.json → `knowledge.db` or `production.db`.

### Hard Requirement: Source→Fixture Bridge
The KEP pipeline eats a fixture JSON with `surface_signals` and `extracted_fields`.
Every real source type needs an adapter that produces this format:
- SMWS PDF → fixture.json
- Book PDF → fixture.json (per expression)
- Retail CSV → fixture.json (per expression)  
- Web review → fixture.json (per review)

### Hard Requirement: Live HTTP Acquisition
The `acquisition/` directory has interfaces but the orchestrator uses hardcoded mock URLs.
Needed: Wire HttpFetcher → ChangeDetector → ContentCache → KEP pipeline.

### Soft Requirement: Unified Entity Resolution
Currently 4+ different implementations, each giving different results for the same input.
Needed: One canonical entity resolver that all pipelines call.

---

## Architecture Drift Summary

| Designed | Actual | Drift |
|---|---|---|
| One canonical pipeline for all sources | 5+ standalone pipelines per source type | SEVERE |
| KEP pipeline writes to promotion gate → DB | KEP pipeline writes to output/ files only | BROKEN PATH |
| Acquisition pipeline acquires real web data | Acquisition pipeline uses hardcoded metrics | SIMULATION |
| Evidence engine discovers → cert bridge fills | Book sprints bypass evidence entirely | BYPASS |
| Certification engine certifies all fields | Book sprints have their own consensus | DUPLICATED |
| Entity resolution is a shared service | 4 different implementations exist | FRAGMENTED |
| 7 canonical flavor axes everywhere | Book/NotebookLM still use 16-20 axes | NON-CANONICAL |

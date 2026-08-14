# P65 — Definition of Done & GO/NO-GO

> Phase P65 — Extraction Contracts & Canonical Output. Spec/schema only; no
> scraper, parser, extractor, or download code. Deterministic, evidence-first,
> read-only, no fabrication. Compatible with P62, P63, P64, Sprint 1.

## Deliverables produced

| File | Purpose |
|------|---------|
| `extraction_contract.md` | The 6 contract objects: input_manifest, source_profile, extraction_request, extraction_result, evidence_bundle, validation_report. |
| `canonical_output.md` | The 7-part canonical output model. |
| `canonical_output.schema.json` | JSON Schema (draft-07) for the canonical output. |
| `field_mapping.md` | Source→canonical field mapping (Official, WhiskyFun, Whisky Advocate, Whiskybase, Books). |
| `validation_contract.md` | required/optional fields, normalization, enum rules, null policy, gate. |
| `bundle_spec.md` | extraction / evidence / certification bundle envelopes. |
| `examples/extraction_bundle.json` | Example extraction bundle (validated). |
| `examples/evidence_bundle.json` | Example evidence bundle (validated). |
| `examples/certification_bundle.json` | Example certification bundle (validated). |

## Definition of Done

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Extraction Contract — all 6 objects defined | ✅ |
| 2 | Canonical Output — 7 parts (entity, metadata, evidence, provenance, confidence, certification, merge_candidates) | ✅ |
| 3 | Canonical Field Mapping — all 5 sources | ✅ |
| 4 | Validation Contract — required/optional/normalization/enum/null | ✅ |
| 5 | Bundle format — 3 bundles specified + example instances | ✅ |
| 6 | 6 required outputs produced (+3 example bundles) | ✅ |
| 7 | canonical_output.schema.json valid draft-07; examples conform | ✅ |
| 8 | Compatible with P62 (SRC_011–013 as source_name/expert_review) | ✅ |
| 9 | Compatible with P63 (source_class, entity_type, certification paths) | ✅ |
| 10 | Compatible with P64 (evidence ledger entries, EV- ids, hashes) | ✅ |
| 11 | Compatible with Sprint 1 (canonical fields, 7 flavor axes, authority tiers; no schema clobber) | ✅ |
| 12 | Deterministic (fixed seed, closed enums, checksums) | ✅ |
| 13 | Evidence-first + no fabrication (null for absent; non-null ⇒ evidence) | ✅ |
| 14 | No scraper/parser/extractor/import code | ✅ |
| 15 | No production mutation (read-only) | ✅ |
| 16 | AOUS-compatible | ✅ |

## GO / NO-GO

### GO requires ALL of:
- [x] 6 extraction contract objects fully specified.
- [x] 7-part canonical output + valid JSON Schema; example bundles conform.
- [x] Field mapping for all 5 sources, authority-ceiling respected.
- [x] Validation contract covering required/optional/normalization/enum/null + gate.
- [x] 3 bundle formats + referential integrity (bundles reference evidence ids).
- [x] Full compatibility with P62/P63/P64/Sprint 1 (enums + ids reused, no clobber).
- [x] Deterministic, evidence-first, no fabrication, read-only, no code.

### NO-GO if ANY of:
- Canonical output allows arbitrary/invented fields (not closed).
- A source maps into a field above its authority ceiling as a certifier.
- A non-null field permitted without backing evidence (fabrication).
- A null field carries value-claiming evidence (contradiction).
- Enums diverge from P63/P64/Sprint 1.
- Any scraper/parser/extractor/import code written, or production mutated.

## AOUS Compatibility
The 6 contract objects map 1:1 onto the Sprint-1 agents (Extraction produces
extraction_result + evidence_bundle; Validation produces validation_report; Merge
consumes merge_candidates; Certification produces certification_bundle; Audit
enforces P64 rules). All shapes are machine-readable, closed, and reuse existing
enums — the single-source-of-truth authority layer is referenced, not
duplicated. **Verdict: AOUS-compatible.**

## Verdict: **GO** (contracts + canonical output complete; no code, no data, no production write, by design).

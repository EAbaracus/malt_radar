# Promotion Review

**Package:** P303 â€” Promotion Decision Package (DOCUMENTATION ONLY)
**Date:** 2026-07-18
**Status:** Pre-promotion review. No data changed. No certification changed. No promotion executed.

---

## 1. Candidate Records

| Field | Value (verified from `staging_editorial.db`, read-only) |
|---|---|
| `evidence_id` | `EDR-b6108f7ac8d252af` |
| `raw_name` | `Ardbeg 10` |
| `normalized_name` | `ardbeg 10` |
| `source_id` | `whiskyfun` |
| `flavor_vector_json` | `{"smoky":0.9,"peaty":0.85,"fruity":0.3,"sweet":0.2,"spicy":0.5,"maritime":0.8,"sherry":0.0}` |
| `provenance_state` | `staging_unverified` |
| `match_status` | `unmatched` |
| `extraction_method` | `structured_extraction` |
| `evidence_confidence` | `1.0` |

Single candidate present. No other P301-derived rows exist in staging.

---

## 2. Evidence Summary

- Source artifact: `mr-kep/fixtures/sample_whisky.json` (pre-produced, real; not a live scrape).
- Qualification: 1 unit, `in_scope=True`.
- Evidence Engine: returned candidate list, no error.
- Extraction Execution: `State.COMPLETED`, 10 evidence records.
- Canonicalization: 7 flavor axes resolved; flavor vector emitted.
- Flavor Mapping: 7 canonical axes (`d4_reducer.flavor_mapper.FlavorMapper`).
- Deduplication: `SemanticDeduplicator` â†’ `duplicate=False`.
- Staging write: 1 row inserted into `staging_editorial_reviews` (real 25-column schema).

---

## 3. Pipeline Execution Summary

| Stage | Module | Result |
|---|---|---|
| Load pending source | `run.py` sources scan | 1 source discovered |
| Qualification | `qualification_engine.engine.run_batch` | in_scope |
| Evidence | `evidence_engine.engine.run` | candidate list, no error |
| Extraction Execution | `extraction_execution.engine.ExecutionEngine` | COMPLETED, 10 records |
| Certification | `certification_engine.certify` | **HOLD** |
| Canonicalization | `run.py` (real `extracted_fields`) | 7 axes |
| Flavor Mapping | `d4_reducer.flavor_mapper.FlavorMapper` | 7 axes |
| Deduplication | `graph.semantic_deduplicator.SemanticDeduplicator` | duplicate=False |
| Staging write | `staging_editorial.db` | 1 row |
| Reporting | JSON writers | 4 reports |

`statistics.json`: `total=1, completed=1, failed=0, staging_written=1, duplicates=0`.

---

## 4. Certification State

**HOLD** â€” not `CLEAN`. The candidate is not certified-clean and is therefore not promotion-eligible until the hold is resolved and a human approval is recorded.

---

## 5. Known Limitations

- Certification is `HOLD` (not `CLEAN`); root cause not established in this package.
- `provenance_state` is `staging_unverified` â€” provenance has not been ratified.
- No `promotion_manifest` has been produced or sealed.
- No human `GO` / approval flag exists.
- Input was a pre-produced fixture, not a live external source (live acquisition is a separate future epic).
- `match_status = unmatched` â€” not linked to a master whisky record.

---

## 6. Reviewer Checklist

See `reviewer_checklist.md`. All items are **unchecked** pending human review.

---

## 7. Approval Decision Field

```
APPROVAL DECISION:  [ ____________________________ ]   (blank â€” pending human review)
REVIEWER:           [ ____________________________ ]
DATE:               [ ____________________________ ]
```

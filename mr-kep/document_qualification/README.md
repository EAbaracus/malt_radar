# MR-KEP — Document Qualification (`document_qualification/`)

> **Phase P67 — Document Qualification & Extraction Planning.** This directory
> is **design/specification only**. It defines the deterministic layer that, for
> any incoming document, decides: (1) is it worth processing, (2) what extraction
> strategy it needs, (3) expected metadata yield, (4) confidence before
> extraction, (5) estimated processing cost.
>
> **No extraction. No OCR. No parsing. No scraping. No implementation. No
> production interaction.** P62–P66 are NOT modified.

## How it fits

```
incoming document (surface metadata only)
        │
        ▼
   qualification_rules.md   ← order of evaluation, output contract, hard overrides
        │
        ▼
   document_classes.md      ← 12 classes × 10 fixed attributes
        │
        ▼
   qualification_score_model.md  ← 0–100 weighted score + 5 gate bands
        │
        ▼
   quality_gates.md         ← G0–G5 deterministic gates (pre-extraction)
        │
        ▼
   processing_strategy_matrix.md  ← recommended pipeline per class
   expected_metadata_yield.md     ← expected fields + pre-extraction confidence
        │
        ▼
   qualification_record  →  feeds P65 input_manifest / source_profile
```

## Files

| File | Role |
|------|------|
| `README.md` | This file. |
| `qualification_rules.md` | Evaluation order, output contract, hard overrides. |
| `qualification_score_model.md` | Weighted score (0–100) + thresholds (Reject … High Priority). |
| `document_classes.md` | 12 required classes × 10 attributes (fixed constants). |
| `processing_strategy_matrix.md` | Recommended pipeline (P66 vocabulary) per class. |
| `expected_metadata_yield.md` | Expected canonical fields + pre-extraction confidence. |
| `quality_gates.md` | G0–G5 deterministic gates before extraction. |
| `qualification_examples.md` | Worked examples (illustrative, no asserted values). |

## The 12 document classes
Book, Magazine, Official PDF, Product Sheet, Marketing Brochure, Auction
Catalogue, Archived Snapshot, Research Paper, Blog Article, Review Website
Export, Database Dump, Scanned Document.

## Score → gate bands (deterministic)
- **0–24** Reject · **25–44** Archive Only · **45–59** Extract Later ·
  **60–79** Extract Normally · **80–100** High Priority
- Hard overrides: `license_risk == 1.0` → Reject; `license_risk >= 0.6` → Archive
  Only; `T3 ∧ identity < 0.2` → Reject; OCR-blocked scan → Archive Only.

## Compatibility (no changes made)
- Authority tiers (T1/T2/T3) + source classes: **P63**.
- Canonical field names + null policy: **P65**.
- Evidence ledger / append-only: **P64**.
- Six-agent + P66 pipeline vocabulary: **Sprint 1 / P66**.
- AOUS-reusable: every decision is a pure function of declared constants.

## Verification
Ad-hoc read-only checks (no suite) confirm: all 8 files present, score bands
valid, all 12 classes covered, all gates G0–G5 defined, thresholds fixed, no
implementation artifacts, no production interaction. See the verification report
in the delivery message.

# Qualification Score Model — MR-KEP P67

> Design only, deterministic, evidence-first, read-only. No implementation.
> Companion to `qualification_rules.md` and `document_classes.md`.

## Score (0–100): weighted sum of 10 normalized factors

Each factor is normalized to **0.0–1.0**; weights sum to **1.00**. The score is
`round(100 * Σ factor_i * weight_i)`, deterministic to the integer.

| # | Factor | Weight | Source (where the value comes from) |
|---|--------|:------:|--------------------------------------|
| 1 | Authority | 0.20 | `document_classes.authority_tier` → T1=1.0, T2=0.7, T3=0.2 |
| 2 | Metadata Density | 0.15 | `document_classes.metadata_density` (0–1) |
| 3 | Extraction Complexity | 0.10 | inverse of `extraction_complexity` (1−complexity) |
| 4 | Historical Value | 0.10 | `document_classes.historical_value` (0–1) |
| 5 | Flavor Value | 0.10 | `document_classes.flavor_usefulness` (0–1) |
| 6 | Identity Value | 0.10 | `document_classes.identity_usefulness` (0–1) |
| 7 | Expected Noise | 0.10 | inverse of `expected_noise` (1−noise) |
| 8 | License Risk | 0.05 | inverse of `license_risk` (1−risk) |
| 9 | OCR Quality | 0.05 | `document_classes.ocr_quality` (0–1); 1.0 if born-digital |
| 10 | Expected Evidence Count | 0.05 | `min(expected_evidence_count/12, 1.0)` |

> Weights: 0.20 (Authority) + 0.15 (Density) + 5×0.10 (Complexity, Historical, Flavor, Identity, Noise) + 3×0.05 (License, OCR, EvidenceCount) = 1.00. Deterministic by construction.

**Determinism note:** a class's factor values are fixed constants in
`document_classes.md`. The score is therefore a pure lookup + arithmetic — no
runtime inference, no model call.

## Determinism of factor derivation

- `authority_tier` → Authority: T1_authoritative=1.0, T2_expert=0.7,
  T3_community=0.2. (P63 tiers.)
- `extraction_complexity` (0–1, see document_classes) → factor = `1 − complexity`.
- `license_risk` (0–1) → factor = `1 − risk`. At risk=1.0 this factor =0 AND the
  hard override forces Reject (rules.md).
- `ocr_quality` (0–1): born-digital PDFs/text = 1.0.
- `expected_evidence_count`: count of `{class × field}` rows that map to a
  canonical field in `expected_metadata_yield.md`; capped at 12.

## Thresholds (deterministic bands)

| Gate | Score band | Meaning |
|------|-----------|---------|
| **Reject** | 0–24 | Not worth processing (low authority/density/value or overridden). |
| **Archive Only** | 25–44 | Keep for provenance; do not extract yet (e.g. OCR-blocked scan). |
| **Extract Later** | 45–59 | Queue; low urgency / low yield. |
| **Extract Normally** | 60–79 | Standard pipeline. |
| **High Priority** | 80–100 | Front of queue. |

Bands are **inclusive lower, exclusive upper** except the top (80–100). A score
of exactly 80 → High Priority. Hard overrides (rules.md) can force a gate
regardless of band (e.g. license_risk=1.0 → Reject even at 100).

## Worked class-score table (pre-override)

Computed from `document_classes.md` constants (illustrative, all values visible
in `document_classes.md`):

| Document Class | Authority | Density | Complexity(inv) | Hist | Flavor | Identity | Noise(inv) | License(inv) | OCR | EvCount | **Score** | Base Gate |
|----------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Official PDF | 1.0 | 0.9 | 0.8 | 0.6 | 0.1 | 0.95 | 0.9 | 0.9 | 1.0 | 1.0 | **93** | High Priority |
| Product Sheet | 1.0 | 0.85 | 0.85 | 0.3 | 0.2 | 0.95 | 0.9 | 0.95 | 1.0 | 1.0 | **91** | High Priority |
| Research Paper | 0.7 | 0.7 | 0.6 | 0.9 | 0.4 | 0.7 | 0.8 | 0.9 | 1.0 | 0.75 | **78** | Extract Normally |
| Magazine | 0.7 | 0.6 | 0.6 | 0.5 | 0.8 | 0.6 | 0.6 | 0.85 | 1.0 | 0.75 | **70** | Extract Normally |
| Review Website Export | 0.7 | 0.7 | 0.7 | 0.3 | 0.9 | 0.4 | 0.6 | 0.8 | 1.0 | 0.9 | **71** | Extract Normally |
| Database Dump | 0.9 | 0.8 | 0.4 | 0.4 | 0.2 | 0.9 | 0.8 | 0.9 | 1.0 | 1.0 | **81** | High Priority |
| Archived Snapshot | 0.7 | 0.5 | 0.5 | 0.8 | 0.3 | 0.6 | 0.7 | 0.8 | 0.9 | 0.6 | **63** | Extract Normally |
| Marketing Brochure | 1.0 | 0.5 | 0.7 | 0.2 | 0.1 | 0.7 | 0.5 | 0.7 | 1.0 | 0.5 | **64** | Extract Normally |
| Book | 0.7 | 0.8 | 0.45 | 0.9 | 0.85 | 0.7 | 0.7 | 0.8 | 0.3* | 0.9 | **73** | Extract Normally (*OCR likely) |
| Auction Catalogue | 0.7 | 0.75 | 0.5 | 0.7 | 0.3 | 0.85 | 0.6 | 0.9 | 0.4* | 0.8 | **70** | Extract Normally (*OCR likely) |
| Blog Article | 0.2 | 0.4 | 0.8 | 0.2 | 0.5 | 0.2 | 0.5 | 0.7 | 1.0 | 0.3 | **45** | Extract Later |
| Scanned Document | 0.7 | 0.5 | 0.1 | 0.7 | 0.4 | 0.5 | 0.7 | 0.8 | 0.0 | 0.4 | **47** | Extract Later → Archive Only (OCR gate) |

*Book / Auction Catalogue / Scanned Document: OCR likely → OCR Quality factor
lower; if born-digital (OCR=1.0) re-score with OCR=1.0 (their gate may rise to
Extract Normally). The OCR gate in `quality_gates.md` decides before extraction.

## Cost estimation (deterministic, separate from score)

`estimated_cost` derived from three class attributes:
- OCR need == true → +1 cost unit
- table_likelihood ≥ 0.6 → +1
- extraction_complexity ≥ 0.6 → +1

| Units | Cost |
|-------|------|
| 0 | Low |
| 1 | Medium |
| 2–3 | High |

## Compatibility
- Authority tiers and source classes reuse P63.
- Canonical field names come from P65.
- Pipeline stage vocabulary from Sprint 1 + P66 (no schema change).
- Thresholds are fixed integers — fully deterministic, AOUS-reusable as a pure
  scoring function.

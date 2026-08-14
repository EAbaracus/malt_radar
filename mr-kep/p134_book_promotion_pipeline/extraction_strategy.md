# P134 — Extraction Strategy (READ-ONLY Design)

- doc_version: P134-1
- defines per-field extraction method, expected confidence, automation level.
- grounded in real staging shapes (`staging_book_flavor_profiles`, `flavor_evidence`, NotebookLM).

## Extraction methods
| method | use | tooling |
|---|---|---|
| Regex | structured labels (ABV `(\d+\.?\d*)%`, age `(\d+)\s*Year`, cask #, ISBN) | `re` over OCR text |
| OCR | scanned PDFs → text | Tesseract / cloud OCR; page-aligned |
| LLM | unstructured prose → fields (tasting notes, descriptors, vectors) | prompt + schema-constrained output |
| Lookup | join to existing entities (distillery name→distillery_id, smws_code→whisky_id) | deterministic dict/SQL |
| Manual | review-queue resolution | human |
| Hybrid | LLM draft + regex validation + lookup reconciliation | pipeline default |

## Per-field extraction plan
| field | method | expected conf | automation |
|---|---|---|---|
| distillery | Lookup (name→id) + LLM detect | 0.85–0.95 | high (lookup), med (LLM) |
| age | Regex `(\d+)\s*Years?` → fallback LLM | 0.90 (regex), 0.70 (LLM) | high |
| abv | Regex `(\d+\.?\d*)%` | 0.95 | high |
| nas | LLM/keyword ("No Age Statement") | 0.85 | med |
| cask_type | Regex + LLM normalize | 0.85 | med |
| cask_number | Regex (SMWS only) | 0.98 | high |
| tasting_notes (nose/palate/finish) | LLM section-split | 0.80 | med |
| flavor_vector (7-axis) | LLM score 0-100 → normalize | 0.75 | med |
| flavor_tags | LLM keyword extract | 0.80 | med |
| region/country | Lookup (knowledge_regions) + LLM | 0.80 | med |
| founded_year/owner | LLM + cross-book corroboration | 0.70 | low (REVIEW) |
| bottler | Regex BOTTLER_RE + LLM | 0.80 | med |
| brand | Lookup + LLM | 0.80 | med |
| awards | LLM + dedupe | 0.75 | low |

## Confidence sources (3 signals, combined)
1. **extraction_confidence** — method reliability (regex > lookup > LLM).
2. **parser_confidence** — OCR/text-quality score (from `flavor_evidence.parser_confidence`).
3. **signal_confidence** — agreement across ≥2 sources (from `staging_flavor_profile_candidates.signal_confidence`).
Final `overall_confidence = f(extraction, parser, signal)` — see confidence_engine.md.

## Automation tiers
- **FULL**: regex/lookup fields (abv, age, cask_number, distillery lookup) → auto-promote if conf≥threshold.
- **SEMI**: LLM fields with validator (tasting notes, flavor_tags) → auto-append, review on low conf.
- **MANUAL**: historical facts, identity, conflicts → always `staging_manual_review_queue`.

## Existing pipeline evidence (real)
- `staging_book_flavor_profiles.extraction_method` column exists (null in sample → to be filled by P135).
- `flavor_evidence.extraction_confidence=1.0, parser_confidence=1.0` for SMWS (structured source).
- `staging_flavor_profile_candidates_full` already computes `source_confidence, signal_confidence, overall_confidence, duplicate_risk` → P135/P138 reuse these columns directly.

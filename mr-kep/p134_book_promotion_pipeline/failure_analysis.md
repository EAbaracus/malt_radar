# P134 — Failure Analysis (READ-ONLY Design)

- doc_version: P134-1
- every failure mode + mitigation. Grounded in real schema quirks observed during discovery.

## 1. OCR failures
| failure | cause | mitigation |
|---|---|---|
| Garbled text | scan quality | `parser_confidence` gate; re-OCR or route to manual |
| Wrong page mapping | multi-column | page-aligned chunking; provenance audit |
| Missed ABV/age | font/table | regex fallback + LLM cross-check |

## 2. Entity resolution failures
| failure | cause | mitigation |
|---|---|---|
| Wrong entity (false MERGE) | generic name "Speyside, Spey" matches 73 whiskies | fuzzy ≥0.85 on (name+age+abv); ambiguous → REVIEW (seen in P127.5: 53 product_name→multi-id collisions) |
| Wrong bottler | IB vs OB confusion | BOTTLER_RE; REVIEW if ambiguous |
| Wrong expression | same name diff age | treat as distinct expression (merge_policy §3) |
| Crosswalk gap (P129) | uuid↔W no strong match | SMWS-code backfill on W rows; else manual queue |

## 3. Numeric conflicts
| failure | cause | mitigation |
|---|---|---|
| Conflicting ABV | book vs incumbent ±>0.1 | REVIEW (conflict_resolution §1) |
| Conflicting age | different edition | distinct expression, never overwrite |
| Founded_year drift | books disagree | `review_conflict_log`, present all, no auto-pick |

## 4. Sensory / flavor failures
| failure | cause | mitigation |
|---|---|---|
| Divergent vectors | book A smoky=80, book B=20 | knowledge.db consensus (mean weighted); ≥2 sources OR T2≥0.90 |
| Axis scale mismatch | NotebookLM 0-100 vs flavor_evidence 0-1 vs canonical unknown | normalize to 0-100 (normalization_rules §3) — **scale must be verified per axis in P135** |
| `rich` vs `maritime` | source uses rich, canonical uses maritime | documented mapping (rich→tag, not axis); never silent equivalence |
| Duplicate tasting notes | same note in 2 books | dedupe on (whisky, note_hash); append distinct only |

## 5. Vocabulary / schema drift
| failure | cause | mitigation |
|---|---|---|
| `aroma_tags` REAL not TEXT | legacy schema bug | P138 flags; coerce to NULL; schema fix deferred |
| `foo` scratch table | noise | ignore; exclude from pipeline |
| `finish_type` REAL | mistyped | treat as text APPEND-ONLY |
| Unknown region | book region not in knowledge_regions (23) | map to canonical; new region → REVIEW |

## 6. Provenance / legal failures
| failure | cause | mitigation |
|---|---|---|
| Copyright prose in user field | book text promoted verbatim | C6: only derived facts promoted; tasting prose stays in evidence layer |
| Missing citation | extraction forgot source | C1: reject promotion; no citation → no promotion |
| Price leakage | book mentions price | C7 firewall: price never staged |

## 7. Pipeline-level failures
| failure | cause | mitigation |
|---|---|---|
| Non-idempotent re-run | missing source_hash key | C2 dedupe on (entity,field,source_hash) |
| Lost rows | chunk drop | count verification: input books = output staged (per P127.5 coverage proof) |
| Gate bypass | direct RW | OS read-only lock + `get_write_connection` only |

## 8. Known real blockers carried from prior phases
- **B1** (P128): target `knowledge.db` empty → consensus stage has no live target until bootstrapped.
- **B2** (P128/P129): uuid↔W crosswalk weak-only (0 exact/strong) → SMWS-vector promotion to consensus blocked.
- **B3** (P128): P128 C1 unmet — 726/726 MERGE rows lack `source_citation_id`.
- These are NOT pipeline bugs; they are prerequisites (see implementation_plan.md D-phases).

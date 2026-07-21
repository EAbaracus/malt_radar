# P203 — Confidence Model

## Current confidence signals (evidence from `matching.py`)
`MatchDecision.match_confidence = round(best_ratio, 3)` for `exact`/`fuzzy`; `0.0` for
`unmatched`. `manual_review` carries the raw ratio too (passed through, not zeroed).
There is **no independent confidence model** — confidence == name-similarity ratio.

### Thresholds (verbatim from `matching.py`)
```
THRESH_HIGH   = 0.94   MARGIN_HIGH   = 0.03   → status "exact"
THRESH_REVIEW = 0.88   MARGIN_REVIEW = 0.04   → status "fuzzy"
THRESH_MANUAL = 0.82                         → status "manual_review"
< 0.82                                        → status "unmatched"
```
### Downgrade rules
- If `exact`/`fuzzy` but age hint ≠ target age → force `manual_review`.
- If `exact` but source first token not in target norm_name → downgrade to `fuzzy`.

### knowledge.db per-field confidence (separate, richer model)
`confidence` table records `field_conf, extraction_conf, parser_conf, signal_conf,
source_conf, source_tier` per `(entity_key, field_name)`. `evidence` carries
`confidence` + `signal_confidence` (cross-source agreement). This is the model P203
should extend to *identity* confidence.

## Proposed canonical confidence composition (design)
For a candidate match, compute a blended score:
```
identity_confidence = w1*name_ratio
                    + w2*alias_boost        (exact alias hit → +; class-weighted)
                    + w3*token_ratio
                    + w4*phonetic_ratio
                    + w5*crosswalk_strength (exact/strong > weak)
                    + w6*source_tier_factor
```
- Map to decision bands (reuse existing bands):
  - ≥ 0.94 & margin ≥ 0.03 → **exact** (auto-accept, IMMUTABLE fields)
  - ≥ 0.88 & margin ≥ 0.04 → **fuzzy** (auto-accept, REPLACEABLE/APPEND fields)
  - ≥ 0.82 → **manual_review** (→ `review_queue` issue_type `identity`)
  - < 0.82 → **unmatched** (candidate for net-new entity)

## Reuse targets (do not reinvent)
- `authority/confidence.yaml`, `authority/source_priority.yaml`,
  `resolution/source_resolution_model.yaml` — already consumed by
  `evidence_engine/engine.py` (`resolve_source`) for tier/evidence_type. The identity
  confidence model should read the same files so source tier feeds `w6`.
- `knowledge.confidence` ledger — the audit trail for every field; identity merges
  should write here too via `merge_history`.

## Crosswalk confidence (from `p129`/`p132`)
- EXACT 0, STRONG 4 (0.5%), MEDIUM 6 (0.8%), WEAK 465 (58.9%), NO_MATCH 315 (39.9%).
- The 4 "strong" are **expression-level mismatches** (SMWS single-cask vs core-range
  40% ABV) — a documented false-positive risk. → crosswalk strength must be capped and
  human-reviewed; never auto-merge on weak/strong alone.

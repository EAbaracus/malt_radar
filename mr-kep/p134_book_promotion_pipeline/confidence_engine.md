# P134 — Confidence Engine (READ-ONLY Design)

- doc_version: P134-1
- per-field + per-record confidence; promotion thresholds. Consistent with P128 global bands.

## Signals (from extraction_strategy.md)
- `extraction_confidence` (method reliability): regex/lookup=0.95, LLM=0.75, manual=1.0
- `parser_confidence` (OCR quality): 0.0–1.0 from `flavor_evidence.parser_confidence`
- `signal_confidence` (cross-source agreement): from `staging_flavor_profile_candidates_full.signal_confidence`
- `source_confidence` (authority tier mapped to 0–1): T1=1.0, T2=0.9, T3=0.75, T4=0.6

## Per-field confidence formula
```
field_conf = w1*extraction_conf
           + w2*parser_conf
           + w3*signal_conf
           + w4*source_conf
weights default: w1=0.4, w2=0.2, w3=0.2, w4=0.2  (normalize to sum 1)
```
- If only one signal available (e.g. single book, no cross-source), set missing weights to 0 and renormalize.
- Example: SMWS flavor_evidence → extraction=1.0, parser=1.0, signal=n/a, source(T3)=0.75
  → field_conf = 0.5*1.0 + 0.25*1.0 + 0.25*0.75 = 0.9375 (HIGH).

## Per-record confidence
```
record_conf = min over promoted fields of field_conf
            (weakest-link: a record promotes only as fast as its weakest field)
```
- For APPEND-ONLY fields, record_conf uses the appended field's conf, not the whole record.

## Promotion threshold bands (P128 global)
| band | range | action |
|---|---|---|
| HIGH | ≥ 0.90 | auto-apply to REPLACEABLE; append to APPEND-ONLY |
| MEDIUM | 0.70–0.89 | append-only + citation; REPLACEABLE → REVIEW |
| LOW | 0.50–0.69 | REVIEW-REQUIRED (staging queue) |
| REJECT | < 0.50 | discard (AMBIGUOUS bucket) |

## Decision gates
- **Automatic promotion threshold**: field_conf ≥ 0.90 AND field class ∈ {APPEND-ONLY, REPLACEABLE} AND citation ready AND not price.
- **Manual review threshold**: field_conf < 0.90 OR field class = REVIEW-REQUIRED OR conflict detected.
- **Reject threshold**: field_conf < 0.50 OR identity single-word/generic (conf 0.4) OR price field.

## Authority × confidence interaction
- Overwrite of REPLACEABLE only if `field_conf ≥ threshold` AND `incoming_tier ≤ incumbent_tier`.
- High-confidence LOW-authority (T4) cannot overwrite T2 incumbent even at conf 0.95.

## Why min() for record
- Prevents a 0.95 abv from dragging a 0.55 founded_year into auto-promotion. Each field routed independently to its own gate; record-level is for reporting/audit only.

## Audit outputs
- `overall_confidence` recorded on staging rows (already column in `staging_flavor_profile_candidates_full`).
- promotion logs `promotion_audit_log` with per-field conf + citation hash.

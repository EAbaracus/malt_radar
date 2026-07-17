# P135 — Risk Analysis (READ-ONLY Plan)

- doc_version: P135-1
- enrichment failure modes + mitigation. Real schema quirks from P134/P135 discovery.

## 1. Wrong overwrite
- cause: MEDIUM-conf book overwrites HIGH-conf incumbent on REPLACEABLE field.
- mitigation: authority×confidence gate (P134 §6); overwrite only if incoming_tier ≤ incumbent_tier AND conf≥threshold. IMMUTABLE/REVIEW fields never auto.

## 2. Expression collision
- cause: same name, different age/abv from two sources → mistaken MERGE.
- mitigation: age mismatch = distinct expression (P128 §3); never overwrite age; new age→new whiskies row flagged related.

## 3. Book hallucination (LLM)
- cause: NotebookLM/LLM invents ABV/region not in source.
- mitigation: SEMI automation; LLM fields → review if conf<0.90; cross-check against SMWS where both present; parser_confidence gate.

## 4. Axis mismatch
- cause: source 0–100 vs evidence 0–1 vs canonical 0–945/0–5523 scale confused.
- mitigation: normalize ALL to 0–100 input (measured canonical ranges: smoky 0–945, sweet 0–5523, maritime 0–2121); P136 reads actual per-axis min/max before locking direction; `rich`/`oak`→tags not axes.

## 5. Duplicate tasting notes
- cause: same note in SMWS + 2 books.
- mitigation: note_hash dedupe on (whisky_id, source_hash, text); `duplicate_risk` column honored; single append + source_count++.

## 6. Normalization drift
- cause: cask_type vocabulary diverges across batches ("1st fill bourbon" vs "first-fill bourbon barrel").
- mitigation: canonical vocabulary table (P134 §4); normalize before staging; CI test on vocabulary set.

## 7. Join failure / mis-join
- cause: book whisky_name fuzzy match → wrong whisky_id (generic "Speyside, Spey" matched 73).
- mitigation: fuzzy ≥0.85 on (name+age+abv); else REVIEW. 774 non-joinable book rows → `staging_manual_review_queue` (not forced).

## 8. Citation gap (C1)
- cause: extraction forgets source → promotion rejected.
- mitigation: citation row mandatory per field; gate refuses apply if citation count ≠ change count.

## 9. Price leakage
- cause: book mentions price → accidentally written.
- mitigation: C7 firewall; price fields excluded at transform stage; post-batch price-column hash compare.

## 10. NULL corruption
- cause: empty source string overwrites incumbent value with NULL.
- mitigation: empty source → skip field; never overwrite with NULL; `''`/`'None'`→SQL NULL only on insert, never on merge.

## 11. Crosswalk gap (B4 blocker)
- cause: uuid↔W no strong match (P129: 0 exact/strong) → vectors can't reach consensus.
- mitigation: D2 SMWS-code backfill on W rows; else B4 routes 443 MERGE overlaps to review; 283 MERGE no-match excluded.

## 12. Non-idempotent re-run
- cause: missing source_hash key → double append.
- mitigation: C2 dedupe on (entity,field,source_hash); re-run no-op.

## 13. Gate bypass
- cause: direct RW outside gate.
- mitigation: OS read-only lock + `get_write_connection` only; post-write `integrity_check`+`foreign_key_check`.

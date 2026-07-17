# P135 — Transformation Specification (READ-ONLY Plan)

- doc_version: P135-1
- concrete transforms. Reuses P134 normalization_rules.md; adds production-specific detail.

## 1. normalize age
- `12 Years` / `12 YO` / `12 year old` → `12` (REAL).
- `NAS` / `No Age Statement` → age=NULL, nas=1.
- Range check: 0 < age < 60 else REVIEW.
- Conflict rule (P128 §3): different age = distinct expression, NOT overwrite.

## 2. normalize ABV
- `54.8%` / `54.8 % ABV` / `Alc. 54.8%` → `54.8` (REAL, 1 decimal).
- Tolerance ±0.1 vs incumbent → keep incumbent + cite; beyond → REVIEW.

## 3. normalize cask_type
- Source column differs: SMWS=`cask_type` (staging_smws), books=`cask_or_maturation` (staging_book).
- Canonical vocabulary (P134 §4): `first-fill bourbon barrel`, `refill bourbon barrel`, `first-fill sherry butt`, `oloroso`, `PX`, `quarter cask`, `wine cask`, `port pipe`, `virgin oak`, `hogshead`, `butt`, `barrel`, `puncheon`.
- APPEND-ONLY: multiple casks accumulate (delimiter `;`).

## 4. normalize bottler
- BOTTLER_RE matches: Cadenhead's, Signatory, Gordon & MacPhail, Douglas Laing, Independent Bottlers.
- SMWS = society IB (bottler inferred, not explicit) → set bottler only if named third-party.
- Canonical name normalization (apostrophe variants).

## 5. normalize region / country
- region → `knowledge_regions.region_name` (23 canonical). Unmatched → REVIEW.
- country → canonical set (Scotland, Japan, USA, Ireland, Taiwan, England, Wales, India, Australia, Canada).
- SMWS region text ("Highlands, Speyside") → map to canonical `Speyside`/`Highlands` etc.

## 6. canonical flavour axes
- **Critical scale finding** (measured): `canonical_vectors` axes are NOT 0–100 — smoky 0–945, sweet 0–5523, maritime 0–2121.
- Source scales: NotebookLM/staging_book = **0–100 integer**; `flavor_evidence` = **0–1 float**.
- **Decision**: normalize ALL to 0–100 for staging/consensus input. Map to canonical at promotion via linear scale OR store canonical as-is and compare on 0–100 normalized view. P136 MUST read actual per-axis min/max from `canonical_vectors` and fix the direction (larger=more intense, confirmed).
- Axis set: canonical 7 = smoky, peaty, fruity, sweet, spicy, maritime, sherry. Source `rich`/`oak`/`winey`/etc → fold into `flavor_tags`, NOT vector axes.

## 7. merge tasting notes
- Each source note = new APPEND row in `tasting_notes` (nose/palate/finish), provenance in `source_doc`/`source_entry_number`.
- SMWS verbatim note → split into nose/palate/finish sections (regex on "nose"/"palate"/"finish" headers; fallback: whole note→palate).
- Book note_summary → append as distinct row (different source_system).

## 8. deduplicate notes
- Hash (whisky_id, source_hash, normalized_text). Identical note from 2 books → single append + increment source_count.
- `staging_flavor_profile_candidates_full.duplicate_risk` column pre-flags → honor it.

## 9. citation preservation
- Every applied change writes `official_source_references` row: entity_type, entity_id, source_category, source_name, field_name, field_value, confidence, license_risk, copyright_risk.
- source_doc = book file_hash (from `book_versions.file_hash`). SMWS → source_pdf name.
- C1: no citation → no promotion.

## 10. confidence propagation
- field_conf = 0.4·extraction + 0.2·parser + 0.2·signal + 0.2·source (P134 §6).
- SMWS: extraction=1.0, parser=1.0, source(T3)=0.75 → ~0.94 HIGH.
- Book LLM: extraction=0.75, parser~0.8, signal~0.7, source(T2)=0.9 → ~0.79 MEDIUM.
- Propagate to `data_confidence` (recomputed max) + `flavor_data_confidence`.

## 11. NULL handling
- `''` / `'null'` / `'None'` / `'nan'` → SQL NULL. Never store literal "None".
- `aroma_tags` currently REAL → coerce to NULL; flag for schema fix (P134 D4).
- Empty source value → skip field (do not overwrite incumbent with NULL).

## 12. Idempotency
- Key: (entity_type, entity_id, field_name, source_hash). Re-run = no-op (C2).

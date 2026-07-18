# P203 — Matching Strategy

## Current matcher (reuse the logic, extend coverage)
Source: `mr-kep/editorial/matching.py` — a faithful copy of the proven
`scripts/external_sources/match_structured_ml_whiskey_source_to_production.py`.

### Pipeline stages
1. **normalize** — `normalize_text()` lowers, strips ABV/age/vintage/cask-strength
   tokens, removes generic words (`whisky, scotch, single malt, blended, malt, …`),
   strips punctuation. (Verbatim thresholds/behavior preserved.)
2. **candidate generation** — all `whiskies(name, whisky_id, age)` loaded read-only
   into memory as `(norm_name, age)`.
3. **scoring** — `SequenceMatcher(None, src, tgt).ratio()`; best + second-best kept.
4. **decision** — by ratio + margin + age/brand rules (see `confidence_model.md`).
5. **crosswalk** — *currently absent from the matcher*; crosswalk logic lives only in
   the deferred `p129` staging CSV.

### Strategies available today
- **exact** — ratio ≥ 0.94 AND margin ≥ 0.03 → `exact`.
- **normalized** — same as exact but on `normalize_text` output (this IS the normalized path).
- **token** — *not implemented*. No token-set / bag-of-words comparison exists.
- **phonetic** — *not implemented*. No soundex/metaphone/jaro in `mr-kep` (grep-confirmed).
- **fuzzy** — ratio ≥ 0.88 AND margin ≥ 0.04 → `fuzzy`.
- **manual_review** — ratio ≥ 0.82 → `manual_review`; also forced when age mismatch
  detected or first token missing.
- **unmatched** — ratio < 0.82 → `unmatched`.

### Strategies required by P203 (design, not built here)
| Strategy | Why needed | Reuse target |
|---|---|---|
| **alias lookup** | `matching.py` ignores `entity_aliases` | query `entity_aliases` before fuzzy |
| **multi-entity** | only `whiskies` matched today | mirror matcher for distillery/brand/bottler |
| **token / set** | "Glenlivet 12" vs "12 yo Glenlivet" word-order flips | add `token_set_ratio` alongside `SequenceMatcher` |
| **phonetic** | "BenRiach" vs "Benriach", "Glendronach" vs "GlenDronach" | add soundex/metaphone as a soft signal |
| **crosswalk** | bridge UUID↔W for book entities | activate P129 only on exact/strong, gated (D5) |

## Reuse, don't replace
- Keep `normalize_text` as the single canonical normalizer (promote `B4b` OCR rules into it).
- Keep `SequenceMatcher` thresholds (0.94/0.88/0.82) as the fuzzy baseline.
- Add token + phonetic as *additional* signals feeding the confidence model, not as replacements.

## Source-dependent matching today (the problem P203 solves)
Each source currently funnels into the SAME whisky-name matcher, but:
- alias coverage differs per source (book aliases unmodeled; editorial casual names unmodeled),
- distillery/brand/bottler have NO matcher,
- cross-source identity (SMWS code, Whiskybase id) is only loosely bridged.
P203 defines ONE matcher that consults `entity_aliases` + `external_entities` + fuzzy
for ALL entity types and ALL sources.

# P134 — Normalization Rules (READ-ONLY Design)

- doc_version: P134-1
- canonical vocabularies + transforms. Applied BEFORE validation/consensus.

## 1. Numeric normalization
| field | raw → canonical | rule |
|---|---|---|
| abv | `54.8%` → `54.8` | strip `%`, parse float, 1 decimal |
| abv | `54.8 % ABV` → `54.8` | regex strip tokens |
| age | `12 Years` → `12` | extract int; `12 YO`→`12`; `NAS`→null+set nas=1 |
| age | `10.5` → `10.5` | keep float |
| coordinates | `57.123, -4.567` → float pair | parse decimal; validate range (Scotland 55–59 lat) |
| founded_year | `1824` → int | strip text; flag if >current year or <1400→REVIEW |

## 2. Text normalization
| field | rule |
|---|---|
| distillery name | unicode NFC; lowercase compare; strip punctuation for match; keep canonical title-case for storage |
| whisky name | trim; collapse whitespace; standardize quotes; keep original in `original_name` |
| region | map to `knowledge_regions.region_name` canonical set (23 known) |
| country | ISO-ish canonical (`Scotland`,`Japan`,`USA`,`Ireland`,`Taiwan`…) |
| cask_type | canonical vocabulary (see §4) |
| bottler | canonical name via BOTTLER_RE (Cadenhead's, Signatory, Gordon & MacPhail…) |

## 3. Flavor axis normalization
- Source scales: NotebookLM/staging use **0–100 integer**; `flavor_evidence` uses **0–1 float**; `canonical_vectors` uses **integer** (observed 0–~2000 range).
- Normalize all to **0–100 integer** for consensus input:
  - 0–1 float → ×100 round.
  - `canonical_vectors` raw (0–2000) → must be inspected; if 0–100 keep, else scale. **Action: P135 must read actual min/max per axis before fixing scale** (not assumed).
- Axis alignment: canonical 7 = `smoky, peaty, fruity, sweet, spicy, maritime, sherry`.
  - Source `rich` (NotebookLM/staging) is **NOT** in canonical 7 → map `rich`→ supplemental descriptor, OR fold into `sweet`/`rich_body`? **Decision (Phase 5):** keep `rich` as 8th dimension in staging only; consensus emits 7 canonical; `rich` carried as `flavor_tags` entry. Documented, not silently dropped.
  - `oak, winey, malty, nutty, herbal, waxy, oily, light_body, rich_body, floral` (staging extras) → map to `flavor_tags` text, not vector axes.

## 4. Canonical cask vocabulary
`first-fill bourbon barrel`, `refill bourbon barrel`, `first-fill sherry butts`, `oloroso sherry`, `PX`, `quarter cask`, `wine cask`, `port pipe`, `virgin oak`, `hogshead`, `butt`, `barrel`, `puncheon` — lowercase, hyphen-normalized, de-pluralized for matching.

## 5. Provenance normalization
- book SHA: from `book_versions.file_hash`; store in `source_doc` (tasting_notes) / `field_value` provenance.
- source_category: map source→tier (T1/T2/T3/T4) per authority table.

## 6. Null handling
- empty string `''` or `'null'`/`'None'` → SQL NULL (never store literal "None").
- `aroma_tags` currently REAL → coerce to NULL if not parseable text; P138 flags for schema fix.

## 7. Duplicate detection
- dedupe on (entity_type, entity_id, field_name, source_hash) — promotion_contract C2 idempotency.
- byte-duplicate books (#11/#42) → dedupe at ingest via file_hash.

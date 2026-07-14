# Document Classes — MR-KEP P67

> Design only, deterministic, evidence-first, read-only. Defines the **10
> attributes** for each of the **12 required document classes**. Values are fixed
> constants used by `qualification_score_model.md`. No implementation.

## Attribute legend

| Attribute | Range | Meaning |
|-----------|-------|---------|
| authority_tier | T1_authoritative / T2_expert / T3_community | Source authority (P63). |
| metadata_density | 0.0–1.0 | Fraction of canonical fields the class typically carries. |
| expected_fields | canonical subset (P65) | Fields this class is known to provide. |
| flavor_usefulness | 0.0–1.0 | Whether it carries useful sensory/flavor signal. |
| identity_usefulness | 0.0–1.0 | Whether it anchors distillery/brand/whisky identity. |
| ocr_need | true/false | Requires OCR before structured extraction. |
| table_likelihood | 0.0–1.0 | Probability it contains parseable tables. |
| image_usefulness | 0.0–1.0 | Whether embedded images carry extractable metadata. |
| risk | 0.0–1.0 | Combined license/legal risk. |
| recommended_pipeline | stage list (P66 vocab) | Ordered extraction stages (no code). |

## The 12 classes (full matrix)

| Class | authority | density | flavor | identity | ocr_need | table | image | risk |
|-------|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Book | T2_expert | 0.80 | 0.85 | 0.70 | true | 0.40 | 0.20 | 0.20 |
| Magazine | T2_expert | 0.60 | 0.80 | 0.60 | false | 0.50 | 0.40 | 0.15 |
| Official PDF | T1_authoritative | 0.90 | 0.10 | 0.95 | false | 0.70 | 0.30 | 0.10 |
| Product Sheet | T1_authoritative | 0.85 | 0.20 | 0.95 | false | 0.40 | 0.50 | 0.05 |
| Marketing Brochure | T1_authoritative | 0.50 | 0.10 | 0.70 | false | 0.30 | 0.70 | 0.30 |
| Auction Catalogue | T2_expert | 0.75 | 0.30 | 0.85 | true | 0.80 | 0.30 | 0.10 |
| Archived Snapshot | T2_expert | 0.50 | 0.30 | 0.60 | false | 0.40 | 0.30 | 0.20 |
| Research Paper | T2_expert | 0.70 | 0.40 | 0.70 | false | 0.60 | 0.30 | 0.10 |
| Blog Article | T3_community | 0.40 | 0.50 | 0.20 | false | 0.20 | 0.50 | 0.30 |
| Review Website Export | T2_expert | 0.70 | 0.90 | 0.40 | false | 0.30 | 0.20 | 0.20 |
| Database Dump | T2_expert | 0.80 | 0.20 | 0.90 | false | 0.90 | 0.00 | 0.10 |
| Scanned Document | T2_expert | 0.50 | 0.40 | 0.50 | true | 0.50 | 0.20 | 0.20 |

## Per-class detail

### Book
- **expected_fields:** distillery_name, region, country, nose, palate, finish,
  flavor_axes, age_statement (historical), cask_type.
- **image_usefulness:** 0.20. **recommended_pipeline:** detect_type → qualify →
  ocr_gate → extract(text/prose) → normalize → evidence_ledger → validate.

### Magazine
- **expected_fields:** nose, palate, finish, flavor_axes, score, region.
- **image_usefulness:** 0.40. **recommended_pipeline:** detect_type → qualify →
  extract(prose+table) → normalize → evidence_ledger → validate.

### Official PDF
- **expected_fields:** distillery_name, region, country, abv, age_statement,
  cask_type.
- **image_usefulness:** 0.30. **recommended_pipeline:** detect_type → qualify →
  extract(structured/table) → normalize → evidence_ledger → validate.

### Product Sheet
- **expected_fields:** distillery_name, abv, age_statement, cask_type, region,
  country.
- **image_usefulness:** 0.50. **recommended_pipeline:** detect_type → qualify →
  extract(structured) → normalize → evidence_ledger → validate.

### Marketing Brochure
- **expected_fields:** distillery_name, region, country, image caption metadata.
- **image_usefulness:** 0.70 (images carry most signal). **recommended_pipeline:**
  detect_type → qualify → extract(text+image_caption) → normalize →
  evidence_ledger → validate.

### Auction Catalogue
- **expected_fields:** distillery_name, region, country, abv, age_statement,
  cask_type, vintage.
- **table_likelihood:** 0.80. **recommended_pipeline:** detect_type → qualify →
  ocr_gate → extract(table) → normalize → evidence_ledger → validate.

### Archived Snapshot
- **expected_fields:** distillery_name, region, country, historical facts.
- **recommended_pipeline:** detect_type → qualify → extract(prose) → normalize →
  evidence_ledger → validate (Wayback source per P63).

### Research Paper
- **expected_fields:** region, country, cask_type, distillation history, chemistry.
- **recommended_pipeline:** detect_type → qualify → extract(prose+table) →
  normalize → evidence_ledger → validate.

### Blog Article
- **expected_fields:** nose, palate, finish, flavor_axes (subjective, T3).
- **image_usefulness:** 0.50. **recommended_pipeline:** detect_type → qualify →
  extract(prose) → normalize → evidence_ledger → validate (low priority).

### Review Website Export
- **expected_fields:** nose, palate, finish, flavor_axes, score.
- **recommended_pipeline:** detect_type → qualify → extract(structured_parse) →
  normalize → evidence_ledger → validate.

### Database Dump
- **expected_fields:** distillery_name, region, country, abv, age_statement,
  cask_type, score (structured, T2 per P65 book/structured_metadata mapping).
- **table_likelihood:** 0.90. **recommended_pipeline:** detect_type → qualify →
  extract(structured/tabular) → normalize → evidence_ledger → validate.

### Scanned Document
- **expected_fields:** varies (pre-OCR unknown; assume identity + official
  fields if legible).
- **recommended_pipeline:** detect_type → qualify → **ocr_gate (blocking)** →
  extract → normalize → evidence_ledger → validate. If OCR impossible → Archive
  Only.

## Determinism
All attribute values above are constants. The Qualification Agent reads them; it
does not estimate or infer them at runtime. A document is assigned exactly one
class by surface signals (rules.md). No class is ever synthesized or guessed when
attributes are unknown → `unknown` → Reject.

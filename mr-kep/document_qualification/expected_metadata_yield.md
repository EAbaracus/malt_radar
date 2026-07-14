# Expected Metadata Yield — MR-KEP P67

> Design only, deterministic, evidence-first, read-only. Estimates the canonical
> fields a class is expected to populate (used by the Qualification Agent's
> `expected_fields` + `expected_evidence_count`). Field names are the P65
> canonical set. No value is asserted — only which fields are *expected present*.

## Yield table (canonical fields per class)

| Class | Expected canonical fields | Expected evidence count* |
|-------|---------------------------|:---:|
| Book | distillery_name, region, country, nose, palate, finish, flavor_axes, age_statement, cask_type | 9 |
| Magazine | nose, palate, finish, flavor_axes, score, region | 6 |
| Official PDF | distillery_name, region, country, abv, age_statement, cask_type | 6 |
| Product Sheet | distillery_name, region, country, abv, age_statement, cask_type | 6 |
| Marketing Brochure | distillery_name, region, country (image caption) | 3 |
| Auction Catalogue | distillery_name, region, country, abv, age_statement, cask_type, vintage | 7 |
| Archived Snapshot | distillery_name, region, country, historical identity | 4 |
| Research Paper | region, country, cask_type, distillation history | 4 |
| Blog Article | nose, palate, finish, flavor_axes (subjective T3) | 4 |
| Review Website Export | nose, palate, finish, flavor_axes, score | 5 |
| Database Dump | distillery_name, region, country, abv, age_statement, cask_type, score | 7 |
| Scanned Document | (pre-OCR unknown → identity + official fields if legible) | 4 |

\* `expected_evidence_count` = number of class×field rows that map to a canonical
field (capped at 12 for scoring). Used as factor #10 in the score model.

## Yield confidence (deterministic)

`confidence_before_extraction = authority_factor * density`
where `authority_factor` = (T1=1.0, T2=0.7, T3=0.2) and `density` =
`metadata_density` from `document_classes.md`.

| Class | authority | density | confidence_before_extraction |
|-------|:---:|:---:|:---:|
| Official PDF / Product Sheet | 1.0 | 0.90/0.85 | 0.90 / 0.85 |
| Book | 0.7 | 0.80 | 0.56 |
| Database Dump | 0.9* | 0.80 | 0.72 (*T2 structured per P65) |
| Review Website Export | 0.7 | 0.70 | 0.49 |
| Magazine | 0.7 | 0.60 | 0.42 |
| Auction Catalogue | 0.7 | 0.75 | 0.53 |
| Archived Snapshot | 0.7 | 0.50 | 0.35 |
| Research Paper | 0.7 | 0.70 | 0.49 |
| Marketing Brochure | 1.0 | 0.50 | 0.50 |
| Blog Article | 0.2 | 0.40 | 0.08 |
| Scanned Document | 0.7 | 0.50 | 0.35 |

> This is a *pre-extraction* expectation only. Actual certified confidence uses
> `authority/confidence.yaml` (P65+P63) after evidence is gathered.

## Compatibility
- Field names identical to P65 `canonical_output`.`metadata`.
- `confidence_before_extraction` is a planning estimate; the real per-field
  confidence flows through P63/P64/P65 once extracted.
- No schema change; no fabrication (fields absent at extraction → null per P65
  null policy).

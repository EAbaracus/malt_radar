# Validation Contract — MR-KEP P65

> Spec/docs only, deterministic, evidence-first, read-only, no fabrication.
> Companion to `canonical_output.schema.json` and `authority/field_rules.yaml`.
> Produces the `validation_report` object (see `extraction_contract.md`).

Every `extraction_result` (canonical output) is checked against this contract
before it may enter Merge/Certification. All checks are deterministic.

## 1. Required fields
An admissible canonical output MUST contain (non-empty):
- `schema_version`
- `entity.entity_type`, `entity.entity_key`
- `provenance.extractor_id`, `provenance.extractor_version`,
  `provenance.run_id`, `provenance.generated_at`, `provenance.deterministic=true`
- `confidence.overall`, `confidence.per_field`
- `certification.per_field`
- At least ONE non-null `metadata` field WITH ≥1 backing `evidence` entry.

A missing required field ⇒ `validation_report.gate = FAIL`.

## 2. Optional fields
- `entity.entity_id` (null allowed until resolved), `entity.display_name`.
- Any individual `metadata` field may be null (coverage gap).
- `merge_candidates` (empty when single-source).
- `certification.per_field[*].certification_path`, `authority_tier`.

Optional fields never cause FAIL; a null required-by-product field (e.g. identity
for a whisky) yields a `WARN` and a PARTIAL gate, not FAIL.

## 3. Normalization rules (from `authority/field_rules.yaml`)
| Field | Normalization | Canonical form |
|-------|---------------|----------------|
| distillery_name | trim_canonical_case | trimmed canonical-case string |
| region | canonical_region_enum | enum member |
| country | iso_country_enum | ISO country |
| abv | strip_percent_cast_real | REAL number (strip `%`, `,`→`.`) |
| age_statement | extract_first_integer_year | integer years |
| cask_type | canonical_cask_enum | enum member |
| nose/palate/finish | raw_text | trimmed text |
| flavor_axes | canonical_7axis | 7 axes, each 0.0–1.0 |
| score | scale_0_to_100 | number 0–100 |
| community_rating | scale_0_to_5 | number 0–5 |

A value that cannot be normalized ⇒ the field is set null + `WARN` +
`normalization_ok=false` (never store the malformed raw value as if valid).

## 4. Enum rules
Closed enums (schema-enforced, `additionalProperties:false`):
- `entity.entity_type` ∈ {distillery, brand, whisky, bottling}
- `evidence[*].source_class` / `merge_candidates[*].source_class` ∈ the 7 P63
  classes.
- `certification.per_field[*].certification_level` ∈ {uncertified, proposed,
  certified, rejected}; `certification_path` ∈ {A,B,C,D,E,F,null};
  `authority_tier` ∈ {T1_authoritative, T2_expert, T3_community, null}.
- `flavor_axes` keys ∈ the 7 canonical axes only.
Any value outside its enum ⇒ `enum_violations += 1` ⇒ `gate = FAIL`.

## 5. Null policy
- **Absent data is null** — never `""`, never `0`, never a placeholder, never a
  guessed value (no fabrication).
- A `null` field MUST have NO evidence entry claiming a value for it (a null with
  backing "evidence" is a contradiction ⇒ FAIL).
- A non-null field MUST have ≥1 evidence entry (evidence-first ⇒ else FAIL).
- Identity fields (distillery_name/region/country) null on a `whisky`/`bottling`
  ⇒ WARN + PARTIAL (coverage gap), not FAIL.

## Validation gate
| Gate | Condition |
|------|-----------|
| PASS | all required present, 0 enum violations, null policy OK, normalization OK. |
| PARTIAL | required present + enums OK, but WARNs (coverage gaps / normalization null). |
| FAIL | any required missing, any enum violation, or any null-policy contradiction. |

Deterministic: the same canonical output always yields the same
`validation_report`. The report is read-only and never mutates the result or
production.

# Quality Gates — MR-KEP P67

> Design only, deterministic, evidence-first, read-only. Defines the gates that
> run **before** any extraction. They protect the pipeline from wasted work,
> license exposure, and OCR-blocked documents. No implementation, no production
> interaction.

## G0 — Existence & Integrity Gate
- **Check:** the document reference exists and has a deterministic `document_id`
  (hash of source_url|title|header-sha). Missing/blank → **Reject**.
- **Deterministic:** pure hash; idempotent.

## G1 — Classifiability Gate
- **Check:** exactly one of the 12 classes is assignable from surface signals.
  If `unknown` → **Reject** (never guessed — no fabrication).
- **Deterministic:** surface-signal rules only; no inference model.

## G2 — License / Risk Gate
- **Check:** `license_risk` (from `document_classes.md`) evaluated.
  - `license_risk == 1.0` → **Reject** (hard override, rules.md).
  - `license_risk >= 0.6` → **Archive Only** (store, no extract).
  - else pass.
- **Deterministic:** constant lookup.

## G3 — Authority Worthiness Gate
- **Check:** `T3_community` AND `identity_usefulness < 0.2` → **Reject** (noise
  source). Otherwise pass.
- **Deterministic:** constant lookup.

## G4 — OCR Readiness Gate (blocking for OCR classes)
- **Check:** if `ocr_need == true`:
  - text layer present OR OCR stage available AND `ocr_quality > 0.0` → pass.
  - else → **Archive Only** (cannot extract until OCR exists).
- **Deterministic:** declared `ocr_need` + declared `ocr_quality`.

## G5 — Score Threshold Gate
- **Check:** apply the `qualification_score_model.md` bands:
  - 0–24 → **Reject**
  - 25–44 → **Archive Only**
  - 45–59 → **Extract Later**
  - 60–79 → **Extract Normally**
  - 80–100 → **High Priority**
- Hard overrides (G2/G3) take precedence over the band.
- **Deterministic:** integer-band comparison + fixed overrides.

## Gate precedence (deterministic order)

```
G0 → G1 → G2 → G3 → G4 → G5
```
A failing gate short-circuits; the first failing gate sets the disposition. G5 is
the final scoring band after all hard overrides.

## Output of qualification

The Qualification Agent emits a `qualification_record` (rules.md) carrying the
final `gate`, `qualification_score`, `recommended_pipeline`, `expected_fields`,
`confidence_before_extraction`, `estimated_cost`, and a deterministic
`rationale`. This record feeds the P65 `input_manifest` / `source_profile` — it
never itself extracts or writes production.

## Compatibility
- Gate vocabulary aligns with Sprint 1 `HERMES.md` (checkpoint, deterministic,
  read-only verification) and P65 bundles (qualification record is a pre-stage
  checkpoint).
- No changes to any P62–P66 schema.
- AOUS-reusable: gates are pure functions of declared constants → an AOUS agent
  can evaluate them without code generation.

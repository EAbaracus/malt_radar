# Qualification Examples — MR-KEP P67

> Design only, deterministic, evidence-first, read-only. Illustrative
> qualification records showing the layer's decisions. **No values are asserted**
> — these are dispositions derived from `document_classes.md` constants + the
> score model. Placeholder ids/urls only.

## Example 1 — Official PDF (producer technical sheet)
- **Surface:** PDF from producer domain, official header.
- **Class:** Official PDF. **Attributes:** authority T1, density 0.90, complexity
  0.2, hist 0.6, flavor 0.1, identity 0.95, noise 0.1, risk 0.1, ocr 1.0, evcount
  (6/12→0.5? capped 1.0) → see model (score **93**).
- **Gates:** G0✓ G1✓ G2(pass) G3✓ G4(n/a) G5 → **High Priority**.
- **Pipeline:** detect_type → qualify → extract(structured/table) → normalize →
  evidence_ledger → validate.
- **Expected fields:** distillery_name, region, country, abv, age_statement,
  cask_type. **confidence_before_extraction = 0.90**. **Cost = Low**.

## Example 2 — Scanned Document (pre-OCR)
- **Surface:** image/scan MIME, no text layer.
- **Class:** Scanned Document. **Attributes:** authority T2, density 0.50,
  ocr_need true, ocr_quality 0.0.
- **Gates:** G4 fails (no text layer) → **Archive Only** (blocking OCR gate),
  regardless of score.
- **Disposition:** stored for provenance; extraction deferred until OCR stage.
- **Cost = High** if later OCR'd.

## Example 3 — Blog Article (low authority)
- **Surface:** personal blog, T3.
- **Class:** Blog Article. **Attributes:** authority T3 (0.2), identity 0.20,
  density 0.40 → score **45** (model table). G3: T3 AND identity<0.2? identity=0.2
  → not <0.2 → passes G3. G5 band 45–59 → **Extract Later**.
- **Pipeline:** prose extract → normalize → evidence_ledger (T3, penalized).
- **Expected fields:** nose/palate/finish/flavor_axes (subjective). **confidence
  before = 0.08**.

## Example 4 — Licensed-but-risky marketing brochure
- **Surface:** brand PDF, but license_risk = 0.30 (G2 pass at <0.6) and score 64
  → **Extract Normally**. Contrast: if license_risk were 0.7 → **Archive Only**
  (G2 override), even though score is fine.

## Example 5 — Unknown document
- **Surface:** unrecognizable source, no class assignable.
- **Gates:** G1 fails (unknown) → **Reject**. Never guessed; no fabrication.

## Example 6 — Database Dump
- **Surface:** structured CSV export, T2 structured (P65).
- **Class:** Database Dump. Score **81** → **High Priority**. Pipeline:
  structured/tabular extract → normalize → evidence_ledger → validate. **Cost =
  Low**.

## Determinism check
In every example, the same surface attributes always yield the same class, score,
gates, and pipeline. No example depends on runtime inference or model calls — the
layer is a pure lookup + arithmetic, fully AOUS-reusable.

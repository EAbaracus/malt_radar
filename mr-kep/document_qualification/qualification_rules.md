# Qualification Rules — MR-KEP P67

> **Phase:** P67 — Document Qualification & Extraction Planning. **Design only**
> — no extraction, OCR, parsing, scraping, or download. Deterministic,
> evidence-first, read-only, no fabrication, no production interaction. Does NOT
> modify P62–P66. AOUS-reusable.

## Purpose

Before any document is fetched or parsed, the **Qualification Agent** (Sprint 1
`AGENTS.md`) evaluates it against these deterministic rules and emits a
**qualification record** (consumed downstream by the P65 `input_manifest` /
`source_profile`). Qualification answers five questions with NO content access
beyond surface metadata:

1. Is the document **worth processing**? →gates (Reject … High Priority)
2. What **extraction strategy** does it need? →recommended pipeline
3. What **metadata yield** is expected? →`expected_metadata_yield.md`
4. What is the **confidence before extraction**? →authority tier + density
5. What is the **processing cost**? →complexity / OCR / table factors

## Determinism invariant

Every decision is a pure function of surface attributes
(`document_classes.md`) + the fixed `qualification_score_model.md` weights and
thresholds. Given the same surface attributes, the same class, score, gate, and
pipeline result — no randomness, no model inference at qualify time.

## The qualification record (output contract, not implementation)

```
qualification_record = {
  document_id,            # deterministic hash of (source_url|title|sha-of-header)
  document_class,         # one of the 12 classes
  detected_attributes,    # the 10 attributes from document_classes.md
  qualification_score,    # 0-100, deterministic
  gate,                   # Reject|Archive Only|Extract Later|Extract Normally|High Priority
  recommended_pipeline,   # ordered stage list (no code)
  expected_fields,        # canonical field subset (P65)
  confidence_before_extraction,  # 0-1, from authority tier + density
  estimated_cost,         # Low|Medium|High (deterministic from complexity/ocr/table)
  rationale               # human-readable, deterministic summary
}
```

## Order of evaluation (deterministic)

1. **Classify** the document into exactly one of the 12 classes (by surface
   signals: URL/domain, MIME, filename, publisher, structure). Tie → lowest-
   priority class wins (fail-safe toward caution).
2. **Load** the class's 10 attribute values from `document_classes.md`.
3. **Compute** `qualification_score` per `qualification_score_model.md`.
4. **Apply** threshold + hard overrides → `gate`.
5. **Select** `recommended_pipeline` from `processing_strategy_matrix.md`.
6. **Estimate** expected yield (fields) + cost.
7. **Emit** the qualification record.

## Hard overrides (applied before threshold bands)

- `license_risk == 1.0` → **Reject** (explicit no-go; never extracted).
- `document_class == scanned_document` AND `ocr_quality == 0.0` AND no text
  layer → capped at **Archive Only** (cannot extract until OCR stage exists).
- `authority_tier == T3_community` AND `identity_value < 0.2` → **Reject**
  (low-value noise source).

## No-fabrication guards

- If surface attributes are insufficient to assign a class confidently, the
  document is assigned `unknown` → **Reject** (never guessed).
- `expected_fields` lists only canonical fields the class is known to carry;
  absent fields resolve to `null` at extraction (P65 null policy).
- Qualification never asserts a value — only a disposition.

## Compatibility

- Authority tiers (T1/T2/T3) and source classes reuse P63.
- Canonical field names reuse P65.
- Pipeline stage names reuse the Sprint 1 six-agent + P66 extraction architecture
  vocabulary (fetch → detect_type → qualify → ocr_gate → extract → normalize →
  evidence_ledger → validate → merge → certify). No schema changes.

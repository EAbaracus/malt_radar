# Qualification Engine (P72) - Architecture Notes

## Module Design
The Qualification Engine implements the P67 specification using a strict functional approach.

- `config.py` acts as the single source of truth for the attribute values defined in `document_classes.md`, `expected_metadata_yield.md`, and `qualification_score_model.md`. The constants here drive the entire system deterministically.
- `classifier.py` evaluates only surface signals (such as domains, file extensions, and explicit indicators like ISBN) and returns precisely one of the 12 document classes. If none match, it gracefully fails to `unknown`.
- `scorer.py` applies the 10-factor weighted scoring model to compute a deterministic integer between 0 and 100.
- `gates.py` implements the quality gates (G0–G5), honoring hard overrides (such as license risk and OCR readiness blocks) before falling back to the scoring bands.
- `strategy.py` synthesizes the processing strategy matrix, providing the recommended pipeline stages and estimating extraction yield based purely on classification constants.
- `emit.py` validates the final record against `schemas/qualification.schema.json` using `jsonschema`.
- `engine.py` orchestrates the sequential flow (`Classify -> Score -> Gate -> Emit`) for a batch of input units.

## Key Properties Maintained
1. **Determinism:** Given identical surface signals, the engine produces exactly the same qualification output. Scores are calculated deterministically without LLM intervention or non-deterministic inference.
2. **Idempotency:** Running the batch multiple times with the same input produces an identical output document. There are no side effects to external systems or databases.
3. **No Production Interaction:** The engine only computes results in memory and validates against schemas. It does not read from or write to `production.db`.
4. **No Schema Changes:** The engine cleanly aligns with the existing P67 design and `schemas/qualification.schema.json` format without modifying any Sprint 1 architectures or contracts.
5. **No Data Fabrication:** Missing data is explicitly mapped to `unknown` or `None`. The engine does not guess or interpolate properties.

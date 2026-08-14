# P96.5: Extraction Quality Recovery Implementation Plan

## Goal
Halt production promotion and insert a mandatory **Entity Resolution & NER (Named Entity Recognition) Recovery Layer (P96.5)**. This phase repairs the flawed Book Intelligence extraction pipeline by actively matching extracted textual entities against the real `production.db`, filtering out book formatting noise and generic vocabulary.

## Architecture: `mr-kep/p96_5_recovery/`

We will build the deterministic P96.5 Recovery Engine:

1. **`db_connector.py`**: Connects strictly read-only to `output/import/production.db` and loads the canonical lexicon (`whiskies.name`, `whiskies.original_name`, `distilleries.name`, and `entity_aliases.alias_name`).
2. **`noise_filter.py`**: Implements deterministic filtering of non-entity book artifacts (e.g., TOC, index terms, page numbers, OCR garble, adjectives like "flavor").
3. **`ner_resolver.py`**: Executes strict and fuzzy matching of the remaining `entity_key` strings against the canonical DB lexicon, assigning valid `whisky_id`s.
4. **`p96_5_orchestrator.py`**: The central controller mapping P96's `consensus.json` through the recovery layers to output the regenerated, sanitized P97 candidates.

## Staging Output Contracts
Outputs will be securely isolated in `mr-kep/output/p96_5_recovery/`:
- `repaired_entities.json` (Valid whiskies mapped to `whisky_id`)
- `unresolved_entities.json` (Failed matches requiring review)
- `false_positives_log.json` (Caught noise words)
- `recovery_statistics.json` (Match rates, FPR, counts)
- `regenerated_p97_candidates.json` (Cleaned vectors ready for D4/P97)
- `validation_report.md`

## User Review Required
- **Mock P96 Input vs. Real Database:** Because P96 previously generated simulated vectors against garbage names, this P96.5 script will read the raw P96 `consensus.json`, bounce those garbage strings against the *real* `production.db` (which will naturally catch them as false positives), and also inject a few simulated "good" strings to prove the DB mapping engine (`entity_key` -> `whisky_id`) actually works correctly. Are you comfortable with this methodology to prove the NER/DB hookup?

Reply with **APPROVE** to proceed with P96.5 Implementation and repair the pipeline!

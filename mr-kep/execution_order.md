# Execution Order

The objective is to maximize production coverage while strictly adhering to the deterministic pipeline rules.

### Immediate Backlog
1. `alko_whisky_preview.csv`
2. `low_risk_retail_probe_v11.csv`
3. `whiskybase_export_sample.csv`

### To Be Skipped
- `manual_curated_tasting_notes_url_extract_draft.csv` (1 entity is not worth the execution sprint overhead).

### To Be Deferred
- **SMWS USA TASTING NOTES ARCHIVE**
- **45 PDF/EPUB Books**
*Reason: These sources cannot be processed deterministically. They require the frozen knowledge extraction pipeline, NLP, and heavy text parsing which violate the current rapid entity-discovery sprint mode.*

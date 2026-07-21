# P119 Extraction Report

## Pipeline Performance
- **Time Elapsed:** 0.78 seconds
- **Success Rate:** 98.63%
- **Failed Extractions:** 9 (including 8 requiring OCR)

## Methodology
- **Structured Fields:** Extracted using strict regex boundary matching.
- **Entity Resolution:** Cross-referenced extracted `cask_no` directly against `whiskies.name` and `whiskies.original_name` in `production.db`.
- **Flavor Vectorization:** Translated prose into 7-axis canonical vectors by evaluating hit frequencies against standard sensory keywords (normalized out of 1.0).

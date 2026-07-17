# Execution Strategy

## Recommendation
**Next Source:** `low_risk_retail_probe_v11.csv` (Vinmonopolet)

**Reasoning:**
1. **Highest verified coverage gain:** 39 net-new entities deterministically verifiable.
2. **Lowest implementation effort:** Uses the exact same intake pipeline as HTFW and ALKO.
3. **Lowest duplication risk:** Easily mapped via direct SQL matching.

## Strategic Pivot Warning
After `low_risk_retail_probe_v11.csv`, the remaining deterministic yield drops to single digits (Whiskybase sample = 4). At that point, the deterministic intake strategy will offer no meaningful coverage gain. The project must then pivot to processing the SMWS archive or the PDF Books using the evidence-driven knowledge extraction pipeline.

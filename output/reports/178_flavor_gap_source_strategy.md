# 178 — Flavor Gap Source Strategy

## Candidate sources
* **Mevcut production_data.csv / flavor CSV**: Contains historical flavor records and tasting profiles for up to 500 whiskies, mapped heuristics.
* **Master of Malt tasting notes**: Reliable source of nose, palate, and finish notes. Highly structured.
* **The Whisky Exchange tasting notes**: Excellent supplementary source for official releases and independent bottlings.
* **Whiskybase metadata**: Vast community database containing detailed release versions, age statement, and cask info (subject to robots.txt compliance).
* **Distillery official pages**: High-fidelity official flavor description and cask maturation sheets.
* **Mevcut local CSV/Claude/NotebookLM çıktıları**: Normalization matrices and tags extracted using LLM mapping.

## Quality Gate Metrics
* Total analyzed: 1709
* High confidence exact matches: 36
* Auto candidates after quality gate: 20
* Manual review due to unknown distillery: 1080
* Manual review due to zero flavor vector: 1334
* Manual review due to entity normalization issue: 59
* Auto import: NO
* Manual review required: YES

## Matching rules
1. **Exact Product Name Match**: Matches product name and distillery exactly (e.g. "Aberlour 12 Year Old").
2. **Fuzzy Token Match**: Token containment with age/edition verification.
3. **Distillery-Only Match**: Brand alignment used as a fallback or for custom profiles.

## False-positive prevention
* Strict age and vintage checks (e.g., preventing matching "Glenfiddich 12" to "Glenfiddich 18").
* Ordinal release rejection (e.g., distinguishing "Port Ellen 11th Release" from "Port Ellen 15th Release").
* Hard-coded brand blacklist to prevent generic marks from matching specific editions (e.g., "Monkey Shoulder", "Mister Sam").

## Confidence scoring
* **High**: Name + distillery matches exactly, age and edition align perfectly.
* **Medium**: Token overlap matches with minor differences (spelling, word order) but matching age/ABV.
* **Low**: Only brand matches, or age/edition details are missing.
* **None**: No reference matched.

## Import policy
* No automatic database import.
* Candidate CSV must be validated by a human or script first.
* Changes are additive and will be staged in the `staging_manual_review_queue` table before production release.

## Manual review policy
* All low/medium confidence matches are marked as `manual_review`.
* Discrepancies in age or edition are auto-flagged for human verification.
* Any changes to core flavor scores require auditor sign-off.

## Risks
* Age/Edition mismatch resulting in incorrect radar charts in the mobile app.
* False-positive matches for private casks or special editions.

## Next step recommendation
* Human audit of the `output/review/flavor_gap_candidates.csv` file.
* Develop automated scrapers targeting MoM/TWE details page under strict compliance.

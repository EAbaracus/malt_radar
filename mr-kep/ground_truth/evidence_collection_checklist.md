# Evidence Collection Checklist
## GSD Human Certification · Malt Radar MR-KEP

> **Document type:** Design — per-entry review checklist  
> **Authority:** P69 §15 (Human Review Checklist) · P69 §8 (Evidence Requirements) · `field_rules.yaml` · `confidence.yaml`  
> **Print or use digitally for each entry. One copy per GSD entry per revision.**

---

## Instructions

- Work through all 41 items in order.
- Mark each item **PASS** or **FAIL**.
- Any single FAIL → entry goes to HOLD. Do not skip ahead.
- Record the failing item number in the entry header as `hold_gate`.
- When all 41 items PASS, proceed to confidence computation and gate evaluation.

---

## Entry Header

```
Reviewer:          ________________
Review Date:       ________________
GSD ID:            GSD-NNNN
Revision:          rN
Candidate:         ________________ (from candidate_list.csv)
Session start:     ________________
Session end:       ________________
```

---

## SECTION I — IDENTITY (8 Items)

```
[ ] I-1   canonical_name is unambiguous and stable.
          It matches a universally recognised product (not a distillery or range name).
          EVIDENCE: Official distillery URL noted → ___________________________________

[ ] I-2   distillery is the actual PRODUCING distillery.
          Not a brand, blending house, broker, or regional alias.
          EVIDENCE TYPE: T1 (bottle_print or primary_source_quote)
          Source URL confirmed live: YES / NO
          Quote recorded: YES / NO

[ ] I-3   country uses the canonical ISO country name (e.g. "Scotland" not "UK" or "GB").
          EVIDENCE TYPE: T1
          Value: _________________

[ ] I-4   region is from the canonical region enum and geographically matches the distillery.
          Scottish regions: Speyside / Islay / Highland / Islands / Lowland / Campbeltown
          Non-Scottish: "Japanese" / "American" / "Irish" / etc.
          EVIDENCE TYPE: T1
          Value: _________________

[ ] I-5   official_authority.official_url was opened and visited during this review session.
          It explicitly confirms the identity claims (not merely mentions the product).
          URL: _________________________________________________________________

[ ] I-6   official_authority.authority_tier = "T1_authoritative".
          It is a distillery/producer website, regulatory body, or appellation register.
          NOT Wikipedia. NOT a retailer. NOT a review site.
          Confirmed: YES / NO

[ ] I-7   No unresolved identity conflict remains.
          If two T1 sources disagreed, reject_on_conflict was applied → HOLD was set.
          OR: only one T1 source; no conflict exists.
          Conflict status: NONE / RESOLVED / HOLD_REQUIRED

[ ] I-8   confidence.identity ≥ 0.90 (computed in §6 of certification_workflow.md).
          Computed value: _______
```

---

## SECTION M — METADATA (8 Items)

```
[ ] M-1   abv_percent is stored as a FLOAT, not a string.
          Correct:   43.0 | 46.5 | 60.0
          Incorrect: "43%" | "43" | "43.0%" | null when known
          Value recorded: _______

[ ] M-2   abv_percent matches the source quote after normalization (strip % then CAST REAL).
          Source quote: "________________________________"
          Normalized:   _______

[ ] M-3   age_statement_years is an INTEGER or null (when NAS).
          If NAS, nas=true confirmed by T1 source stating "No Age Statement" or equivalent.
          Correct:   12 | 18 | null
          Incorrect: "12yo" | "12 Years" | 12.0
          Value: _______  nas: TRUE / FALSE

[ ] M-4   If nas=true: a T1 source explicitly confirms NAS status (not inferred).
          Source URL: ___________________________________________
          Quote: "____________________________________________________"

[ ] M-5   cask_type uses the canonical cask enum.
          Canonical values: Bourbon | Sherry | Rum | Port | Cognac | Virgin Oak |
                           Refill | Mizunara | Madeira | Wine | Pedro Ximenez | Other
          Value: _________________
          Source URL: _________________

[ ] M-6   All metadata evidence_references contain: source_url AND non-empty quote.
          abv evidence: source_url ________ quote _______ chars
          age evidence: source_url ________ quote _______ chars
          cask evidence: source_url ________ quote _______ chars

[ ] M-7   No metadata field has "inferred" as its sole evidence_type.
          Each of abv, age_statement, cask_type has T1 evidence.
          Confirmed: YES / NO

[ ] M-8   confidence.metadata ≥ 0.80 (computed).
          Computed value: _______
```

---

## SECTION F — FLAVOR PROFILE (8 Items)

```
[ ] F-1   All 7 flavor axes are present and non-null.
          smoky:   ______  peaty:    ______  fruity: ______  sweet: ______
          spicy:   ______  maritime: ______  sherry: ______
          All in [0.0, 10.0]: YES / NO

[ ] F-2   All axis values are numbers in range [0.0, 10.0].
          No axis value is null, a string, or outside bounds.
          Confirmed: YES / NO

[ ] F-3   dominant_axis matches the axis with the highest numerical score.
          Highest value axis: _______  dominant_axis field reads: _______
          Match: YES / NO

[ ] F-4   flavor_derivation_method is set to one of the three permitted values:
            expert_consensus      → ≥2 independent T2 sources
            single_expert         → 1 T2 source
            inferred_from_notes   → descriptors only, ≥2 notes required
          Value: _________________

[ ] F-5   If flavor_derivation_method = "inferred_from_notes":
          ≥2 independent tasting notes from different publishers are cited.
          Note 1 URL: _________________  Publisher: _________________
          Note 2 URL: _________________  Publisher: _________________
          (Skip this item if not applicable; mark PASS)

[ ] F-6   axes_locked is set intentionally.
          TRUE = reviewer is confident; scores should not be overridden by pipeline.
          FALSE = open to pipeline refinement (only when confidence.flavor < 0.85).
          Value: TRUE / FALSE  Rationale: _________________________

[ ] F-7   confidence.flavor ≥ 0.70 (computed as mean of 7 axis confidences).
          Computed value: _______

[ ] F-8   Evidence_references cover all 7 axes.
          At least one evidence record cites each axis by name.
          smoky: Y/N  peaty: Y/N  fruity: Y/N  sweet: Y/N
          spicy: Y/N  maritime: Y/N  sherry: Y/N
```

---

## SECTION N — TASTING NOTES (7 Items)

```
[ ] N-1   tasting_notes.primary.nose, .palate, and .finish are all non-empty.
          At least 8 words each.
          nose length:   _______ words
          palate length: _______ words
          finish length: _______ words

[ ] N-2   review_url was opened during this review session.
          The text in the entry matches what the source actually says.
          URL visited: YES / NO
          Text match confirmed: YES / NO

[ ] N-3   The reviewer field identifies a named individual or recognised tasting panel.
          NOT anonymous. NOT "Staff pick". NOT distillery own copy.
          Reviewer name/panel: _________________________

[ ] N-4   Score (if present) is on 0–100 scale.
          If source uses a different scale (e.g. /10, /20, /5), conversion is documented
          in the evidence record with formula.
          Score: _______  Scale: _______  Conversion applied: YES / NO / N/A

[ ] N-5   No text is fabricated or paraphrased beyond what the source explicitly states.
          Every sentence or descriptor in nose/palate/finish appears in the cited source.
          Confirmed: YES / NO

[ ] N-6   If additional_notes[] entries are present, each has its own reviewer and review_url.
          Number of additional notes: _______
          Each has reviewer + URL: YES / NO / N/A (none)

[ ] N-7   confidence.tasting_notes ≥ 0.70 (computed as min of nose, palate, finish confidence).
          Computed value: _______
```

---

## SECTION E — EVIDENCE (6 Items)

```
[ ] E-1   Every field in canonical_metadata has ≥1 evidence record.
          abv: Y/N  age: Y/N  cask_type: Y/N  nas (if TRUE): Y/N
          colorant_added (if known): Y/N  chill_filtered (if known): Y/N

[ ] E-2   Every flavor axis has ≥1 evidence record.
          smoky: Y/N  peaty: Y/N  fruity: Y/N  sweet: Y/N
          spicy: Y/N  maritime: Y/N  sherry: Y/N

[ ] E-3   All evidence records contain all required fields:
          fact_id, field, value, confidence, authority_tier, evidence_type,
          source_key, source_url, quote, retrieved_at, won, conflict{}
          Spot-checked: YES / NO

[ ] E-4   No quote is an empty string.
          Grep/search evidence_references for quote:"" : FOUND / NOT FOUND

[ ] E-5   All source_urls are reachable.
          HTTP 200 check OR archive.org equivalent provided.
          Dead URLs remaining: _______ (must be 0 to pass)

[ ] E-6   Conflicting candidates are retained with won:false.
          No conflicting value was silently deleted.
          Number of conflicts found: _______  All retained: YES / NO / N/A
```

---

## SECTION C — COMPLIANCE (4 Items)

```
[ ] C-1   No price field exists anywhere in the record.
          Fields checked: price, retail_price, bar_price, historical_price,
                         average_price, price_per_cl, recommended_retail_price
          Search result: NONE FOUND / FOUND (FAIL — remove before proceeding)
          
          Evidence quotes also checked for price mentions: CLEAN / CONTAINS PRICE
          (If a quote contains a price, truncate the quote to exclude it and note truncation)

[ ] C-2   If Whisky Advocate is cited as a T2 source, a second independent T2 source
          is also present for the same field(s).
          Whisky Advocate cited: YES / NO
          If YES — second independent T2 present: YES / NO
          (Mark PASS if Whisky Advocate not cited)

[ ] C-3   confidence.authority ≥ 0.85.
          Computed value: _______
          Tier violations found: _______  (must be 0 for authority ≥ 0.85)

[ ] C-4   confidence.overall ≥ 0.70.
          Computed value: _______ (must equal min of all 5 dimensions)
          Dimensions: identity _______ metadata _______ flavor _______ 
                      tasting_notes _______ authority _______
          overall = min(above) = _______
```

---

## Checklist Sign-Off

```
Items PASS:          _____ / 41
Items FAIL:          _____ / 41

Failing items:       _______, _______, _______
Hold gate recorded:  YES / NO / N/A

CERTIFICATION RECOMMENDED:   YES / NO

If YES:
  certification_status → CERTIFIED
  review_status → VERIFIED
  benchmark_split:  train / validation / test
  certification_tier: Gold / Silver / Bronze

Reviewer signature:  _____________________
Review completed:    _____________________
GSD ID / Revision:   GSD-_____ / r_____
```

---

## Quick Reference: Confidence Thresholds

| Dimension | Formula | Must Be ≥ |
|-----------|---------|-----------|
| identity | min(distillery, country, region) + bonus | 0.90 |
| metadata | min(abv, age, cask_type) | 0.80 |
| flavor | mean(7 axes) | 0.70 |
| tasting_notes | min(nose, palate, finish) | 0.70 |
| authority | 1.0 − penalties | 0.85 |
| **overall** | **min(all above)** | **0.70** |

## Quick Reference: Evidence Type Base Confidence

| Type | Base Confidence |
|------|----------------|
| `bottle_print` | 0.98 |
| `primary_source_quote` | 0.95 |
| `expert_quote` | 0.90 |
| `aggregated_link` | 0.55 |
| `inferred` | 0.20 |

## Quick Reference: Conflict Policies (from merge_policies.yaml)

| Conflict Type | Policy |
|---------------|--------|
| T1 vs T1 identity disagreement | `reject_on_conflict` → HOLD |
| T1 vs T2 on identity fact | `authority_wins` → T1 wins, T2 kept |
| T2 vs T2 sensory | `latest_expert_wins` → more recent date wins |
| Multiple T2 flavor axes | `consensus_additive` → agreement elevates |
| ABV disagreement > 0.1% between T1s | `reject_on_conflict` → HOLD |
| Unresolvable | `route_to_audit` → HOLD |

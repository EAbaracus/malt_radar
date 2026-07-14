# Reviewer Guidelines
## GSD Human Certification · Malt Radar MR-KEP

> **Document type:** Design — human reviewer operating manual  
> **Authority:** AGENTS.md · P69 §6–§10 · P70 §4–§6  
> **No implementation. No production writes.**

---

## 1. Role Definition

A **GSD Reviewer** is the human agent responsible for:
- Researching and verifying facts about a candidate whisky entry.
- Recording verbatim evidence from authoritative sources.
- Computing confidence scores using the P69 model.
- Making the final certification decision.

**The reviewer is the only entity that can set `certification_status = CERTIFIED`.**  
The pipeline may read GSD entries. It may never write to them.

---

## 2. Reviewer Responsibilities

| Responsibility | Must Do | Must Never Do |
|----------------|---------|---------------|
| Identity | Confirm distillery, country, region against T1 source | Accept Wikipedia or secondary-only sources for identity |
| Metadata | Read the actual bottle spec or official producer page | Infer ABV or age from a third-party database without checking the source |
| Tasting notes | Copy verbatim from T2 expert review | Paraphrase, summarise, or combine quotes from multiple reviewers into one field |
| Flavor axes | Derive from stated descriptors in the source text | Fabricate scores; scores must be traceable to language in the evidence |
| Confidence | Apply confidence.yaml formulas exactly | Round manually or use averages where min() is specified |
| Conflicts | Retain all losing candidates with `won: false` | Drop conflicting values silently |
| Price | Exclude price from all fields and evidence quotes | Include any price reference, even in a quote excerpt |

---

## 3. Source Hierarchy

The reviewer must always prefer the highest available authority tier.

### Tier 1 (T1) — Authoritative

Required for identity, metadata, and official facts.

| Source Type | Examples |
|-------------|---------|
| Official distillery website | `glenfarclas.com/range/12-year-old` |
| Official producer technical sheet | PDF product specification |
| Regulatory register | SWA (Scotch Whisky Association) geographic indication |
| TTB COLAs online | US Alcohol label approval database |
| Official importer product page | First-party importer only |

**T1 requirement:** URL must be reachable (HTTP 200) or have an archive.org equivalent.
T1 sources must explicitly state the fact being claimed — not merely mention the product.

### Tier 2 (T2) — Expert

Required for sensory evaluation and flavor axes.

| Source | Priority | Notes |
|--------|----------|-------|
| WhiskyFun (Serge Valentin) | 10 | Preferred primary T2 source |
| Whisky Advocate | 9 | May not be sole T2 source (corroboration rule) |
| Jim Murray's Whisky Bible | 8 | Physical book; use ISBN + page as URL substitute |
| Master of Malt review | 7 | |
| The Whisky Exchange review | 6 | |
| Distillery blog (named reviewer) | 5 | Must name the individual reviewer |

**T2 prohibition:** Whisky Advocate may not be the sole T2 source for any field.
A second independent T2 must always be present when Whisky Advocate is cited.

### Tier 3 (T3) — Community

Supporting evidence only. May not certify any field independently.

| Source | Use |
|--------|-----|
| Reddit r/Scotch | Community sentiment only |
| Distiller.com | Aggregated score supporting only |
| Vivino (if applicable) | Aggregated only |
| Spirits review aggregators | Never cite as sole evidence |

---

## 4. Evidence Record Discipline

Every fact written to a GSD entry must have at least one `evidence_references[]` record.

### 4.1 Required Fields (from evidence.schema.json)

```json
{
  "fact_id":        "SHA-256 of (gsd_id + field + value_as_string)",
  "field":          "exact field name from field_rules.yaml",
  "value":          "the specific value being evidenced",
  "confidence":     0.9500,
  "authority_tier": "T1_authoritative",
  "evidence_type":  "bottle_print",
  "source_key":     "registered_source_identifier",
  "source_url":     "https://...",
  "quote":          "Verbatim excerpt from the source. Never empty.",
  "retrieved_at":   "2026-07-14",
  "won":            true,
  "conflict": {
    "resolved":     true,
    "reason":       "single_source",
    "losers_kept":  false
  }
}
```

### 4.2 The Quote Discipline

**The quote field must contain the exact words from the source.**

```
CORRECT:
  "quote": "Glenfarclas 12 Years Old. Strength: 43% vol. Maturation: Sherry Casks."

INCORRECT:
  "quote": "The website says it's 43%"
  "quote": ""
  "quote": "ABV confirmed as 43%"
  "quote": "sherry matured"
```

The quote is not your summary. It is the **verbatim extract from the source**,
sufficient for any future reviewer to locate the specific fact in the original document.

### 4.3 Conflict Recording

When two sources disagree on a value, **both must be recorded**.

```json
// Winning evidence record
{ "value": 43.0, "won": true, "conflict": { "resolved": true, "reason": "authority_wins", "losers_kept": true } }

// Losing evidence record (kept in the array)
{ "value": 43.2, "won": false, "conflict": { "resolved": true, "reason": "authority_wins", "losers_kept": true } }
```

**Losing values are never deleted.**

---

## 5. Normalization Rules (from field_rules.yaml)

The reviewer must apply these normalizations before recording any value.

| Field | Normalization | Example |
|-------|--------------|---------|
| `abv_percent` | `strip_percent_cast_real` | `"43%"` → `43.0` |
| `age_statement_years` | `extract_first_integer_year` | `"12 Years Old"` → `12` |
| `country` | `iso_country_enum` | `"Schottland"` → `"Scotland"` |
| `region` | `canonical_region_enum` | `"Speyside Region"` → `"Speyside"` |
| `distillery` (name) | `trim_canonical_case` | `"THE GLENFARCLAS"` → `"Glenfarclas"` |
| `type` | `canonical_type_enum` | `"Single malt"` → `"Malt"` |
| `cask_type` | `canonical_cask_enum` | `"American Oak Ex-Bourbon"` → `"Bourbon"` |
| Flavor axes | `canonical_7axis` | Values must be float in [0.0, 10.0] |

---

## 6. Flavor Axis Scoring Guide

Flavor scores are derived from language in T2 expert notes — they are never invented.

### 6.1 Derivation Method Decision

| Method | When to Use | Requirement |
|--------|-------------|-------------|
| `expert_consensus` | ≥2 independent T2 sources independently produce similar scores | Use mean of independent scores; record both as evidence |
| `single_expert` | Only one T2 source available | Set `axes_locked=false` unless `confidence.flavor ≥ 0.85` |
| `inferred_from_notes` | Reviewer derives scores from descriptors, not explicit scores | Requires ≥2 independent notes; explicit in evidence |

### 6.2 Scoring Heuristics

These are approximate translations of common tasting vocabulary to axis scores.
They do not override explicit numeric ratings from a T2 source.

| Descriptor Language | Axis | Approximate Score |
|--------------------|------|-----------------|
| "heavily peated", "intensely smoky", "peaty bonfire" | peaty / smoky | 8.0 – 10.0 |
| "quite peaty", "prominent smoke", "medicinal" | peaty / smoky | 5.5 – 7.9 |
| "hint of smoke", "light peat", "subtle smokiness" | peaty / smoky | 2.0 – 5.4 |
| "no smoke", "unpeated", "clean" | peaty / smoky | 0.0 – 1.9 |
| "sherry bomb", "full sherry", "Christmas cake" | sherry | 7.5 – 10.0 |
| "sherry influence", "dried fruit", "raisins" | sherry | 4.0 – 7.4 |
| "subtle sherry", "light wood spice" | sherry | 1.0 – 3.9 |
| "tropical fruit", "orchard fruit", "citrus" | fruity | 6.0 – 9.0 |
| "subtle fruitiness", "faint apple" | fruity | 2.0 – 5.9 |
| "sweet vanilla", "toffee", "honey" | sweet | 5.0 – 9.0 |
| "dry", "austere", "not sweet" | sweet | 0.0 – 3.0 |
| "salt spray", "seaweed", "coastal", "brine" | maritime | 5.0 – 9.0 |
| "pepper", "ginger", "warming spice" | spicy | 4.0 – 8.0 |

**Important:** When a T2 source provides explicit numeric scores (e.g. Whisky Advocate
90-point scale), do not override with the heuristic table. Convert the score:
```
axis_score = (source_score − 80) / 2   (maps 80–100 range to 0–10)
```
Only if the T2 source provides axis-specific scores or uses descriptor language alone.

### 6.3 Independent Source Requirement for Axes

For `flavor_derivation_method = expert_consensus`, sources must be:
- From **different publishers** (WhiskyFun + Whisky Advocate counts; two WhiskyFun
  reviews of the same expression by the same author do NOT count).
- Based on different tasting occasions (different review dates).
- Each producing axis-level or descriptor-level evidence independently.

---

## 7. Prohibited Content

The following must **never appear** in any GSD entry or evidence record:

| Prohibited | Reason |
|-----------|--------|
| Any price field | Product rule (AGENTS.md) — price never in UI or API |
| Prices in quote excerpts | Price must be redacted or the quote must be shortened to exclude it |
| Fabricated quotes | No fabrication policy (MR-KEP glossary) |
| Inferred values as sole evidence | Inferred type base confidence 0.20; sole inferred → cert block |
| Wikipedia as T1 source | Not authoritative for production metadata |
| Empty `source_url` | Every evidence record must have a real URL |
| `source_url: "localhost"` or placeholder | Invalid |
| Score not on 0–100 scale without normalization | Must document conversion |

---

## 8. Reviewer Quality Self-Check

Before submitting an entry for gate evaluation, the reviewer should ask:

```
□ Would I be comfortable if another expert checked every source_url I cited?
□ Is every quote verbatim — not my paraphrase?
□ Did I record the losing values in every conflict, or did I delete them?
□ Does the confidence.overall I computed match the formula min(identity,
  metadata, flavor, tasting_notes, authority)?
□ Is there any price anywhere in this record?
□ Could I reconstruct every axis score from the text of the cited notes?
□ Did I normalise abv as a float (43.0) and not a string ("43%")?
```

If the answer to any is "I'm not sure", stop and verify before proceeding.

---

## 9. Definition of Done (Reviewer)

A single entry is **done** when:

```
[ ] All 41 checklist items PASS (see evidence_collection_checklist.md)
[ ] All 10 certification gates PASS (see certification_workflow.md §4 Stage 7)
[ ] confidence.overall ≥ 0.70 and confidence.identity ≥ 0.90
[ ] No price fields
[ ] benchmark_split assigned
[ ] certification_tier assigned (Gold | Silver | Bronze)
[ ] Index updated
[ ] Signed with reviewer identifier and reviewed_at timestamp
```

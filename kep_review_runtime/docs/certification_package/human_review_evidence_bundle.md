# Human Review Evidence Expansion Bundle â€” P305.6

**Mode:** READ ONLY Â· Evidence preparation only Â· No code changes Â· No staging/production writes Â· No certification changes Â· No promotion Â· No commit/push/tag
**Date:** 2026-07-18
**Candidate:** `evidence_id = EDR-b6108f7ac8d252af` Â· `normalized_name = ardbeg 10`
**Purpose:** Expose all evidence behind the candidate so a human can independently decide. **This bundle does NOT decide approval. Certification remains HOLD.**

---

## 1. Candidate Identity

| Field | Value (verified from `staging_editorial.db`, read-only) |
|---|---|
| evidence_id | `EDR-b6108f7ac8d252af` |
| normalized_name | `ardbeg 10` |
| raw_name | `Ardbeg 10` |
| current certification state | **HOLD** |
| current provenance state | **staging_unverified** |
| authority tier | **T2_expert** |
| match_status | `unmatched` |
| extraction_method | `structured_extraction` |
| evidence_confidence | `1.0` |
| score_value | `92.0` |

---

## 2. Source Evidence (chain)

```
source (whiskyfun â€” independent whisky review blog)
   â†“  artifact
   mr-kep/fixtures/sample_whisky.json (document_id: MRKEP-SAMPLE-001)
   â†“  extraction
   extraction_execution.engine.ExecutionEngine â€” State.COMPLETED, 10 evidence records
   â†“  normalization
   kep_runtime/run.py canonicalize â†’ metadata_json + flavor_vector_json
   â†“  certification
   certification_engine/__init__.py â†’ aggregate state = HOLD
```

| Element | Detail |
|---|---|
| source identifier | `whiskyfun` |
| source type | independent blog review (`is_structured_export=true`) |
| source authority tier | `T2_expert` |
| artifact identifier | `MRKEP-SAMPLE-001` |
| content hash | `c0f37aa9251539ac7e82e19fa3611e1235e0489ea7db7b1da1e7ccd0a33b64ff` |
| acquisition timestamp | not available (fixture is a pre-produced artifact, not a live scrape) |

---

## 3. Raw Evidence Visibility (per field)

> Source text snippets extracted verbatim from `mr-kep/fixtures/sample_whisky.json` (real fixture). Confidence per field: 1.0 (from `evidence_confidence`). Authority tier: `T2_expert` for all fields.

### Required identity fields

#### distillery_name

| Attribute | Value |
|---|---|
| extracted value | `Ardbeg` |
| source text snippet | `"distillery_name": "Ardbeg"` (fixture line 24) |
| confidence | 1.0 |
| authority tier | T2_expert |
| transformation applied | none â€” verbatim from fixture `extracted_fields` |

#### region

| Attribute | Value |
|---|---|
| extracted value | `Islay` |
| source text snippet | `"region": "Islay"` (fixture line 25) |
| confidence | 1.0 |
| authority tier | T2_expert |
| transformation applied | none â€” directly from fixture |

#### country

| Attribute | Value |
|---|---|
| extracted value | `Scotland` |
| source text snippet | `"country": "Scotland"` (fixture line 26) |
| confidence | 1.0 |
| authority tier | T2_expert |
| transformation applied | none â€” directly from fixture |

#### abv

| Attribute | Value |
|---|---|
| extracted value (normalized) | `46.0` |
| original source value | `"46%"` (fixture line 27) â€” string with percent sign |
| source text snippet | `"abv": "46%"` (fixture line 27) |
| confidence | 1.0 |
| authority tier | T2_expert |
| transformation applied | percentage string `"46%"` parsed to float `46.0`; `score_value` = `92.0` stored |

#### age_statement

| Attribute | Value |
|---|---|
| extracted value | `10` |
| source text snippet | `"age_statement": 10` (fixture line 28) |
| confidence | 1.0 |
| authority tier | T2_expert |
| transformation applied | none â€” integer from fixture |

#### cask_type

| Attribute | Value |
|---|---|
| extracted value | `Ex-Bourbon` |
| source text snippet | `"cask_type": "Ex-Bourbon"` (fixture line 29) |
| confidence | 1.0 |
| authority tier | T2_expert |
| transformation applied | none â€” directly from fixture |

### Additional extracted fields (for completeness)

| field | value | source text snippet | confidence |
|---|---|---|---|
| nose | `Coastal peat smoke, lemon zest, green apple, vanilla` | `"nose": "Coastal peat smoke, lemon zest, green apple, vanilla"` | 1.0 |
| palate | `Rich peat smoke, dark chocolate, sea salt, black pepper` | `"palate": "Rich peat smoke, dark chocolate, sea salt, black pepper"` | 1.0 |
| finish | `Long, smoky with lingering peat, brine and oak spice` | `"finish": "Long, smoky with lingering peat, brine and oak spice"` | 1.0 |
| score | `92` | `"score": 92` | 1.0 |

---

## 4. Field-Level Decision Table

| field | value | confidence | actual authority | required authority | human decision needed |
|---|---|---|---|---|---|
| distillery_name | Ardbeg | 1.0 | **T2_expert** | **T1_authoritative** | (blank for reviewer) |
| region | Islay | 1.0 | **T2_expert** | **T1_authoritative** | (blank for reviewer) |
| country | Scotland | 1.0 | **T2_expert** | **T1_authoritative** | (blank for reviewer) |
| abv | 46.0 | 1.0 | **T2_expert** | **T1_authoritative** | (blank for reviewer) |
| age_statement | 10 | 1.0 | **T2_expert** | **T1_authoritative** | (blank for reviewer) |
| cask_type | Ex-Bourbon | 1.0 | **T2_expert** | **T1_authoritative** | (blank for reviewer) |

> The five T2-ceiling fields (nose, palate, finish, flavor_axes, score) are certifiable under the actual `T2_expert` authority and are NOT blockers. Only the six T1-ceiling identity fields above force HOLD.

---

## 5. Flavor Evidence

- **Seven-axis vector** (from `certification_engine/__init__.py` `FlavorMapper` output â†’ `flavor_vector_json`):

  ```json
  {"smoky": 0.9, "peaty": 0.85, "fruity": 0.3, "sweet": 0.2, "spicy": 0.5, "maritime": 0.8, "sherry": 0.0}
  ```

- **Evidence source:** fixture `extracted_fields.flavor_axes` (line 33â€“41)
- **Confidence:** 1.0
- **Normalization notes:** all 7 canonical axes present, each in [0,1]; `smoky`/`peaty`/`maritime` dominant (consistent with Islay peated single malt profile); `sherry` = 0.0 (no sherry-cask evidence in source). Mapping: fixture key names (`smoky`, `peaty`, etc.) map 1:1 to canonical axes; no axis merging required.

---

## 6. Duplicate / Matching Review

| Check | Result |
|---|---|
| Semantic dedup | `duplicate=False` â€” no semantic duplicate detected in staging |
| Match status | `unmatched` â€” record is NOT linked to a master whisky entry |
| Possible conflicts | none detected within staging; production cross-check NOT performed |
| Unresolved ambiguity | `match_confidence = None` â€” no matching algorithm was applied; the record exists independently in staging |

---

## 7. Certification HOLD Explanation

- **Why the engine returned HOLD:** `certification_engine/__init__.py` `aggregate_certification()` returns `HOLD` when **any field is `proposed`** (Path C). The six T1-ceiling identity fields have confidence â‰¥ `CERTIFY_MIN (0.70)` but an **actual authority of `T2_expert`** that does **not** satisfy the required `T1_authoritative` ceiling (`determine_certification_path` â†’ Path C â†’ `proposed`).
- **Which rules triggered HOLD:** `FIELD_CEILING` (`distillery_name`, `region`, `country`, `abv`, `age_statement`, `cask_type` â†’ `T1_authoritative`), combined with `authority_tier = T2_expert` at extraction time. The authority check `_tier_rank(authority_tier) <= _tier_rank(ceiling)` evaluates as `2 <= 1` â†’ **false** â†’ Path C.
- **Is this expected?** **YES** â€” this is correct deterministic engine behavior. HOLD is the expected fail-closed state for T2-sourced identity fields. It is NOT a defect.

---

## 8. Human Reviewer Questions

The following questions remain **pending the human reviewer's independent decision**. No answer is recorded here.

1. **Do you accept the available evidence for this candidate?**
   - All 10 fields present, confidence â‰¥ 0.70, no conflicts detected.
   - [ ] Accept   [ ] Reject   [ ] Request more

2. **Do you accept T2_expert authority for the affected fields?**
   - The six T1-ceiling identity fields were certified by a T2_expert source (whiskyfun). Accepting this authority resolves the HOLD.
   - [ ] Accept   [ ] Reject   [ ] Promote to T1

3. **Do you ratify the provenance chain?**
   - Current `provenance_state = staging_unverified`. Ratification requires validating `content_hash` against source and accepting source authenticity.
   - [ ] Ratify   [ ] Reject   [ ] Request additional verification

4. **Should certification move from HOLD to APPROVED?**
   - This is the aggregate outcome of questions 1â€“3.
   - [ ] Approve   [ ] Keep HOLD   [ ] Reject

---

## 9. Evidence Limitations

- **Missing evidence:** No master whisky link exists (`match_status = unmatched`, `match_confidence = None`). The candidate exists independently in staging without a relation to the master whisky table.
- **Unknowns:** The source artifact has no acquisition timestamp (it is a pre-produced fixture, not a live scrape). Provenance ratification has not been performed â€” the `staging_unverified` flag is structural, not a conclusion.
- **Assumptions that must NOT be made:**
  - Do NOT assume the T2 authority is sufficient for T1-ceiling fields without explicit human acceptance.
  - Do NOT assume provenance is ratified without an explicit approval.
  - Do NOT assume the certification HOLD is a defect â€” it is correct engine behavior.
  - Do NOT assume the candidate represents a complete, production-ready entry (it is unmatched and unverified).
  - Do NOT fabricate a master whisky link or match confidence â€” those are absent from the real data.

---

**This bundle contains evidence only. No decision has been made. Certification remains HOLD. Provenance remains staging_unverified.**

*Generated 2026-07-18 from read-only inspection of real artifacts: `staging_editorial.db`, `certification_engine/__init__.py`, `mr-kep/fixtures/sample_whisky.json`, `kep_runtime/reports/runtime_report.json`.*

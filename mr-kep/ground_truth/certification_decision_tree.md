# Certification Decision Tree
## GSD Human Certification · Malt Radar MR-KEP

> **Document type:** Design — deterministic decision guide  
> **Authority:** P69 §6 (Review Workflow) · P69 §7 (Certification Workflow) · AGENTS.md  
> **Use this tree after completing the evidence_collection_checklist.md.**  
> **No ambiguity is permitted. Every branch has exactly one output.**

---

## How to Use This Tree

1. Start at **ROOT**.
2. Answer the question at each node with YES or NO.
3. Follow the branch. Do not skip levels.
4. End at a terminal node: `CERTIFIED` · `HOLD` · `REJECTED` · `DRAFT_CONTINUE`.
5. Record the terminal node outcome in the entry header.

All decisions are deterministic — the same entry state always produces the same outcome.

---

## Decision Tree

```
══════════════════════════════════════════════════════════════════
ROOT
══════════════════════════════════════════════════════════════════

Is the entry in candidate_list.csv with a valid GSD-CAND-NNNN id?
│
├─ NO ──► STOP. Entry is not in scope. Do not create a GSD record.
│
└─ YES
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE A — ENTRY CREATION COMPLETE?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Has a GSD-NNNN ID been assigned and a JSON file created in entries/?
│
├─ NO ──► DRAFT_CONTINUE
│          Action: Complete Stage 1 (certification_workflow.md §4)
│          Return to NODE A when done.
│
└─ YES
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE B — IDENTITY VERIFIED? (Gate G1, G2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Are all product_identity fields non-null?
Is official_authority.official_url reachable (HTTP 200 or archive)?
Does the T1 source explicitly confirm distillery, country, region?
│
├─ NO to any ──► HOLD [G1 or G2]
│                Hold reason: record which sub-check failed.
│                Action: Find T1 source or resolve URL.
│                Move entry to review_queue/GSD-NNNN_r1_PENDING.json.
│
└─ YES (all three)
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE C — IDENTITY CONFLICT? (G2 sub-check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Do two or more T1 sources disagree on distillery, country, or region?
│
├─ YES ──► HOLD [G2-CONFLICT]
│           Policy: reject_on_conflict
│           Action: Record both values. Human must determine authoritative source.
│           Do not guess. Do not merge.
│
└─ NO (no conflict, or conflict already resolved)
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE D — METADATA EVIDENCED? (Gate G3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Does every canonical_metadata field have ≥1 T1 evidence record?
Fields: abv_percent, age_statement_years (or nas=true), cask_type_primary
Each evidence record must have: source_url (live) + non-empty quote
│
├─ NO ──► HOLD [G3]
│          Hold reason: record which field(s) lack T1 evidence.
│          Action: Locate bottle spec or official producer page.
│
└─ YES
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE E — ABV CONFLICT? (G3 sub-check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Do two or more T1 sources disagree on abv_percent by more than 0.1%?
│
├─ YES ──► HOLD [G3-ABV-CONFLICT]
│           Policy: reject_on_conflict
│           Action: Both values retained. Human resolves with third T1 source.
│
└─ NO
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE F — T2 EXPERT NOTE PRESENT? (Gate G4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Is tasting_notes.primary present with:
  • non-empty nose, palate, finish?
  • authority_tier = T2_expert?
  • review_url reachable (HTTP 200 or archive)?
  • reviewer = named individual or recognised panel?
│
├─ NO ──► HOLD [G4]
│          Hold reason: no T2 review found / URL dead.
│          Action: Find T2 review on WhiskyFun, Whisky Bible, or equivalent.
│
└─ YES
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE G — WHISKY ADVOCATE SOLE SOURCE? (G4 sub-check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Is Whisky Advocate the only T2 source for any field in this entry?
│
├─ YES ──► HOLD [G4-WA-SOLE]
│           Corroboration rule: Whisky Advocate may not be sole T2 source.
│           Action: Find a second independent T2 source.
│
└─ NO (Whisky Advocate not cited, or a second T2 is also present)
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE H — ALL 7 FLAVOR AXES POPULATED? (Gate G5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Are all 7 axes non-null and in [0.0, 10.0]?
smoky · peaty · fruity · sweet · spicy · maritime · sherry
│
├─ NO ──► HOLD [G5]
│          Hold reason: list missing or out-of-range axes.
│          Action: Derive missing axes from additional T2 source text.
│
└─ YES
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE I — INFERRED-ONLY FIELDS? (Gate G6)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Does any field have "inferred" as its only evidence_type?
(An inferred record as the SOLE evidence for that field)
│
├─ YES ──► HOLD [G6]
│           Hold reason: name the field(s) with inferred-only evidence.
│           Action: Find a quoted source or leave the field null.
│           Never certify an inferred-only fact.
│
└─ NO (every fact has at least one non-inferred evidence record)
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE J — ALL SOURCE URLS REACHABLE? (Gate G7)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Are all source_url values in evidence_references returning HTTP 200
OR having a valid archive.org equivalent URL?
│
├─ NO ──► HOLD [G7]
│          Hold reason: list unreachable URLs.
│          Action: Find archive.org equivalent and update source_url.
│          If no archive found for a primary-field source → HOLD persists.
│
└─ YES
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE K — ANY PRICE FIELDS? (Gate G8) ← CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Does the entry contain any price-related field or quote excerpt
containing a price (price, retail_price, bar_price, historical_price,
average_price, recommended_retail_price, etc.)?
│
├─ YES ──► IMMEDIATE RETURN TO DRAFT
│           Action: Remove all price fields and price-containing quote excerpts.
│           This is not a HOLD — it is a mandatory cleanup before any other gate.
│           Return to NODE K after cleanup.
│
└─ NO (confirmed: zero price fields)
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE L — CONFIDENCE OVERALL ≥ 0.70? (Gate G9)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Compute:
  overall = min(identity, metadata, flavor, tasting_notes, authority)
  (Use confidence.yaml formulas. Round 4dp, round_half_even.)
│
├─ overall < 0.70 ──► HOLD [G9]
│                      Hold reason: list the lowest-scoring dimension.
│                      Check confidence.weak_fields for specific targets.
│                      Action: Find additional evidence for weak fields.
│
└─ overall ≥ 0.70
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NODE M — CONFIDENCE AUTHORITY ≥ 0.85? (Gate G10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Compute:
  authority = 1.0 − (0.30 × tier_violations) − (0.15 × missing_tier_records)
  A "tier violation" = field certified below its authority_ceiling
  A "missing tier record" = field with no authority_tier recorded
│
├─ authority < 0.85 ──► HOLD [G10]
│                        Hold reason: list fields with tier violations.
│                        Action: Find higher-tier source for violating fields,
│                        or reclassify the evidence tier correctly.
│
└─ authority ≥ 0.85
     │
     ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TERMINAL NODE — ALL 10 GATES PASSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
G1 ✅  G2 ✅  G3 ✅  G4 ✅  G5 ✅
G6 ✅  G7 ✅  G8 ✅  G9 ✅  G10 ✅
     │
     ▼
CERTIFIED ✅
  Set: certification_status = CERTIFIED
  Set: review_status = VERIFIED
  Set: reviewed_at = [current ISO datetime]
  Set: reviewer = [your identifier]
  Assign: benchmark_split (train | validation | test)
  Assign: certification_tier (Gold | Silver | Bronze)
  Save: entries/GSD-NNNN.json
  Create: change_history/GSD-NNNN_history.jsonl (empty stub)
  Update: gsd_corpus_index.yaml
```

---

## HOLD Resolution Sub-Tree

When an entry is in HOLD, use this sub-tree each time the reviewer
returns to attempt resolution.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOLD RESOLUTION ROOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Has the blocking issue identified in hold_gate been resolved?
(New source found / URL archived / conflict resolved / field fixed)
│
├─ NO
│   │
│   How many review sessions has this HOLD persisted?
│   │
│   ├─ < 5 sessions ──► HOLD_CONTINUE
│   │                    Leave entry in review_queue/.
│   │                    Note session count in hold_reason.
│   │
│   └─ ≥ 5 sessions ──► ESCALATION DECISION
│                         │
│                         Is the blocking issue a fundamental
│                         data availability problem
│                         (no T1 source exists; distillery closed
│                          with no archive; expression discontinued
│                          with no documentation)?
│                         │
│                         ├─ YES ──► REJECTED
│                         │          Move to rejected/GSD-RJCT-NNNN.json
│                         │          Record rejection_reason and rejected_at
│                         │          Retire ID permanently in index
│                         │          Select replacement from candidate_list.csv
│                         │
│                         └─ NO ──► HOLD_CONTINUE with escalation note
│                                   Reviewer should seek additional source suggestions
│                                   from project owner before next session
│
└─ YES (blocking issue resolved)
     │
     Return entry to PENDING_REVIEW
     Re-enter certification decision tree at the failing gate node
     (Re-run only from the failing gate onward, not the full tree)
```

---

## Certification Tier Assignment Sub-Tree

After CERTIFIED is reached, assign the tier using this sub-tree.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIER ASSIGNMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

confidence.overall ≥ 0.95
AND identity ≥ 0.97
AND ≥2 independent T2 sources for sensory fields
AND T2 primary source is WhiskyFun or Jim Murray?
│
├─ YES ──► Gold
│
└─ NO
     │
     confidence.overall ≥ 0.85
     AND ≥1 T2 source (non-WA-sole)
     AND all metadata T1-evidenced?
     │
     ├─ YES ──► Silver
     │
     └─ NO (all other CERTIFIED entries) ──► Bronze
```

---

## Decision Log Template

Record every certification decision in this format for traceability:

```
GSD-ID:          GSD-NNNN
Reviewer:        ___________
Date:            ___________
Revision:        rN

Gate results:
  G1: PASS / FAIL  G2: PASS / FAIL  G3: PASS / FAIL
  G4: PASS / FAIL  G5: PASS / FAIL  G6: PASS / FAIL
  G7: PASS / FAIL  G8: PASS / FAIL  G9: PASS / FAIL
  G10: PASS / FAIL

Overall outcome:   CERTIFIED / HOLD [gate-id] / REJECTED
Hold reason:       ___________
Tier assigned:     Gold / Silver / Bronze
Split assigned:    train / validation / test
confidence.overall: _______
```

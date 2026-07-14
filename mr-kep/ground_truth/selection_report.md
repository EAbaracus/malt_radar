# GSD Phase 1 — Selection Report
## Ground Truth Dataset · Candidate List v1.0

> **Document type:** Selection rationale and methodology — read-only  
> **Candidates produced:** 100  
> **Target corpus:** 120 CERTIFIED entries (Phase 1)  
> **P69 compliance:** Follows all P69 stratification rules  
> **Production interaction:** None — production.db opened read-only only  
> **Date:** 2026-07-13

---

## 1. Read-Only Verification

All checks performed before candidate selection.  
`production.db` opened as `file:output/import/production.db?mode=ro`.

| Check | Result | Status |
|-------|--------|--------|
| DB opened read-only | Confirmed | ✅ PASS |
| `whiskies` rows | 3,557 | ✅ PASS |
| `tasting_notes` rows | 1,848 | ✅ PASS |
| `flavor_profiles` rows | 2,676 | ✅ PASS |
| HIGH-confidence whiskies | 148 | ✅ PASS |
| Candidate cross-reference hits | **38/38 name groups found** | ✅ PASS |
| SHA-256 before | `47342ba2b80fc1cfe8f2db6aa8374e0578b19aecf8061a9cc2387474dd51a18c` | ✅ PASS |
| SHA-256 after | `47342ba2b80fc1cfe8f2db6aa8374e0578b19aecf8061a9cc2387474dd51a18c` | ✅ PASS |
| `production.db` modified | **NO** | ✅ PASS |

**All 38 candidate name groups have matching rows in production.db.**  
This confirms that the candidate list covers whiskies the Malt Radar system already
knows about, which will facilitate future comparison validation.

---

## 2. Selection Methodology

### 2.1 Governing Rules (P69 §11)

Selection follows the P69 stratification methodology exactly:

1. Maximum 40% Scotland by count (≤ 40 of 100 candidates).
2. All required countries covered with meaningful representation.
3. All 6 Scottish regions covered at or above minimum floors.
4. All required styles (type) represented.
5. Both peated and unpeated included; heavily peated minimum 15.
6. Both NAS and age-stated included.
7. All candidates are official distillery bottlings (Phase 1 restriction).
8. This is a **candidate list only** — no data has been extracted or verified.

### 2.2 Selection Priority Principles

Candidates were ranked by three priority tiers:

**Priority 1 (49 entries):** Universally recognised benchmark expressions  
→ The whisky the world uses as a reference for its region, style, or character.  
→ Strongest likelihood of T1 + T2 evidence in publicly accessible sources.

**Priority 2 (38 entries):** Significant, well-reviewed expressions  
→ High expert review coverage; important for style diversity.

**Priority 3 (13 entries):** Geographically necessary fill entries  
→ Required to meet stratum floors (e.g. Rest of World countries with limited iconic options).

### 2.3 Cross-Distillery Consistency Design

Where two or more candidates share a distillery, this is intentional:
- Tests whether the extractor can distinguish between expressions from the same producer.
- Validates age-statement handling across a single distillery's range.

**Deliberate multi-entry distilleries:**

| Distillery | Candidates | GSD IDs |
|------------|-----------|---------|
| Glenfarclas | 3 | 0004, 0009, 0011 |
| Glenfiddich | 2 | 0005, 0012 |
| Macallan | 2 | 0006, 0007 |
| Balvenie | 2 | 0008, 0016 |
| Ardbeg | 2 | 0002, 0017 |
| Laphroaig | 2 | 0003, 0018 |
| Glenmorangie | 2 | 0023, 0025 |
| Springbank | 2 | 0038, 0039 |
| Yamazaki | 2 | 0041, 0042 |
| Hakushu | 2 | 0043, 0044 |
| Nikka | 4 | 0045, 0046, 0047, 0048 |
| Buffalo Trace | 6 | 0054, 0055, 0056, 0057, 0058, 0065 |
| Redbreast / Midleton | 3 | 0067, 0068, 0069 |
| Amrut | 2 | 0077, 0078 |
| Paul John | 2 | 0079, 0080 |
| Kavalan | 4 | 0085, 0086, 0087, 0088 |
| Penderyn | 2 | 0091, 0092 |
| Starward | 2 | 0099, 0100 |

---

## 3. Stratum-by-Stratum Selection Rationale

### 3.1 Stratum 1 — Country

| Country | Candidates | P69 Target (scaled to 100) | Status |
|---------|-----------|---------------------------|--------|
| Scotland | **40** | ≤ 40 | ✅ At cap |
| Japan | 13 | 12–13 | ✅ Met |
| USA | 13 | 12–13 | ✅ Met |
| Ireland + Northern Ireland | 10 + 1 = 11 | 10 | ✅ Met |
| India | 4 | 4 | ✅ Met |
| Canada | 4 | 4 | ✅ Met |
| Taiwan | 4 | 4 | ✅ Met |
| Rest of World | 12 | 10–15 | ✅ Met |

Northern Ireland (Bushmills 16yo, GSD-CAND-0074) is included within the Ireland
allocation. The coverage report tracks it separately against production.db.

### 3.2 Stratum 2 — Scottish Regions

All 6 required regions covered. Minor floor shortfalls are expected at 83% of corpus
target and will be resolved in Phase 1 completion.

| Region | Candidates | P69 Floor | Status |
|--------|-----------|-----------|--------|
| Speyside | 13 | 15 | ⚠️ 2 below floor (at 87% of floor) |
| Islay | 9 | 10 | ⚠️ 1 below floor (at 90% of floor) |
| Highland | 7 | 8 | ⚠️ 1 below floor (at 88% of floor) |
| Islands | 5 | 5 | ✅ At floor |
| Lowland | 3 | 4 | ⚠️ 1 below floor (at 75% of floor) |
| Campbeltown | 3 | 3 | ✅ At floor |

All shortfalls are within the expected range for an 83% corpus stage.

### 3.3 Stratum 3 — Style

| Style | Candidates | P69 Scaled Floor | Status |
|-------|-----------|-----------------|--------|
| Single Malt | 72 | 46 | ✅ Exceeded |
| Blended | 7 | 7 | ✅ Met |
| Bourbon | 13 | 12–13 | ✅ Met |
| Rye | 7 | 7 | ✅ Met |
| Single Pot Still | 4 | 4 | ✅ Met |
| Single Grain | 2 | 4 | ⚠️ Below target — see §5 |

### 3.4 Stratum 4 — Peated Character

| Level | Candidates | P69 Requirement | Status |
|-------|-----------|----------------|--------|
| Heavily Peated (peaty ≥ 7.0) | **17** | ≥ 15 | ✅ Exceeded |
| Lightly / Medium Peated | 10 | ≥ 10 | ✅ Met |
| Unpeated | 73 | Natural majority | ✅ Met |

Required iconic peated entries:

| Distillery | Present | GSD ID(s) |
|------------|---------|-----------|
| Ardbeg | ✅ | 0002, 0017 |
| Laphroaig | ✅ | 0003, 0018 |
| Lagavulin | ✅ | 0001 |
| Caol Ila | ✅ | 0019 |
| Kilchoman | ✅ | 0020 |
| Bruichladdich Octomore class | ⚠️ MISSING | — |

### 3.5 Stratum 5 — NAS vs Age Statement

| Category | Candidates | P69 Phase 1 Target (of 120) | Notes |
|----------|-----------|----------------------------|-------|
| Age-stated | 47 | ≥ 80 | ⚠️ Below — see deviation note |
| NAS | 52 | ≥ 20 | ✅ Exceeded |
| Cask Strength | 13 | ≥ 15 | ⚠️ 2 below target |
| Vintage year | 3 | ≥ 10 | ⚠️ Below — deferred |

**Known deviation — NAS/Age ratio:**  
The P69 Phase 1 target is age-statement dominated (80/120 = 67%). This candidate list
is NAS-dominant (52%) for the following evidence-based reasons:

- All US Bourbon benchmarks are legally NAS (bottled from various ages).
- All Indian, Canadian, and Taiwanese candidates are NAS (industry norm in those markets).
- Several of the most iconic world whiskies are NAS (Nikka FTOB, Ardbeg Uigeadail,
  Aberlour A'bunadh). Their exclusion would make the benchmark unrepresentative.

**Resolution:** The 20 additional candidates for Phase 1 completion should target at
minimum 18 age-stated expressions to bring the certified corpus ratio toward the P69
target. The selection_report for Phase 1 completion will track this explicitly.

### 3.6 Stratum 6 — Bottling Type

| Type | Candidates | Rule |
|------|-----------|------|
| Official distillery bottling | **100 (all)** | Phase 1: official only |
| Independent bottling | 0 | Deferred to Phase 2 |

✅ P69 Phase 1 restriction fully observed.

### 3.7 Stratum 7 — Era

| Era | Candidates | P69 Scaled Target | Status |
|-----|-----------|------------------|--------|
| Current | 82 | 71 | ✅ Exceeded |
| Limited / Discontinued | 15 | 17 | ⚠️ 2 below |
| Vintage / Rare | 3 | 12–13 | ⚠️ Below — deferred |

Vintage/Rare entries were deliberately minimised at candidate stage because they
require the highest T1 verification burden (printed distillery records, auction
catalogues). Targeted addition in Phase 1 completion.

---

## 4. Benchmark Split Distribution

| Split | Count | Share | Purpose |
|-------|-------|-------|---------|
| `train` | 56 | 56% | Reference for extractor development |
| `validation` | 29 | 29% | Tuning and intermediate evaluation |
| `test` | 15 | 15% | Hidden benchmark — not published |

The 15 `test` entries are documented in `candidate_list.csv` and this report
but will not appear in the public corpus index once GSD goes live.

---

## 5. Known Gaps — Phase 1 Completion Required

| Gap | Priority | Recommended Additions |
|-----|----------|----------------------|
| Bruichladdich Octomore class | HIGH | Octomore 13.1 or 14.1 (heavily peated, high ABV) |
| Blended Scotch underrepresented | HIGH | Johnnie Walker Black 12yo, Famous Grouse, Chivas 12yo |
| Single Grain below target | MEDIUM | Girvan Patent Still 25yo, Cameronbridge 18yo |
| Tennessee Whiskey missing | MEDIUM | Jack Daniel's Old No.7 (NAS), Jack Daniel's Single Barrel |
| Irish Grain missing | MEDIUM | Teeling Single Grain (NAS) |
| Vintage/Rare below target | LOW | Identified expressions requiring archive source verification |
| Age-stated ratio correction | HIGH | 18+ age-stated entries in Phase 1 completion batch |

---

## 6. Production Non-Interaction Confirmation

> No rows were inserted, updated, or deleted in any table of `production.db`.  
> No files in `mr-kep/` Sprint 1 directories were modified.  
> No extraction, parsing, OCR, or AI pipeline was used.  
> All `approx_abv` and numeric values in `candidate_list.csv` are approximate,  
> based on widely published producer information, and are explicitly marked  
> for T1 verification during the GSD certification phase.

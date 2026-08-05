# Malt Whisky Yearbook 2013–2019 — Edition-Delta + Entity-Saturation + Open-Vocabulary Discovery Audit

**Status:** CLOSED (human-approved) · **Mode:** STRICT READ-ONLY FORENSICS · **Date:** 2026-07-25
**Scope:** All 7 verified annual editions (2013–2019). 2019 = ingested B1 baseline.
**Result type:** Analysis / reconciliation only. No ingestion, staging, promotion, or DB mutation performed.

> This is a durable, read-only record of a completed forensic audit. It documents a
> decision, not an active task. Any future entity promotion or alias merge is a
> SEPARATE human-reviewed identity-resolution task, NOT a continuation of this audit.

---

## LOCKED DECISION

| Edition | Decision | Rationale |
|---------|----------|-----------|
| **2019** | **KEEP / CANONICAL BASELINE** | B1, already ingested; covers the entity frontier |
| **2014–2018** | **HOLD / REDUNDANT — out of ingest scope** | net-new current operating distillery = 0; differences are OCR variants, historical narrative, unbuilt projects, alias/rename candidates |
| **2013** | **HISTORICAL_OPTIONAL — HOLD** | pre-boom narrative value only; NOT required for entity expansion |

**Critical conclusion (two independent methods agree):**

> 2019 baseline + production.db → **net-new current distillery from 2013–2018 = 0**
> (lexicon-anchored audit ✔ AND open-vocabulary discovery ✔ converge)

**Rule confirmed:** 2013–2018 Yearbook ingestion must NOT be done for entity-expansion purposes.

---

## FILE IDENTITY (SHA-256, verified against disk)

| Edition | ISBN-13 | Pages | SHA-256 (prefix) | Text layer |
|---------|---------|-------|------------------|-----------|
| 2013 | 9780955260797 | 300 | `cf1515bba0d7d1de` | TEXT (no OCR needed) |
| 2014 | 9780957655300 | 300 | `4422c03e1252676a` | TEXT |
| 2015 | 9780957655317 | 300 | `7e7952c38b7c2f92` | TEXT |
| 2016 | 9780957655324 | 300 | `dcaba7a748ab95a6` | TEXT |
| 2017 | 9780957655331 | 300 | `8205da11f20d3c31` | TEXT |
| 2018 | 9780957655348 | 300 | `2fa8652ac6e08c42` | TEXT |
| 2019 | 9780957655355 | 300 | `056ab6524af784b3` | TEXT (ingested B1; byte-dup pair with `annas-arch-21eb2f4fc714.pdf`) |

All 7 distinct SHA-256; no accidental cross-edition byte duplicates. 2019 baseline unchanged.

---

## METHOD 1 — Lexicon-anchored edition delta (production coverage per edition)

Matched 2,129 canonical distillery names (of 2,144) via word-boundary regex against each
edition's full text. Deterministic and reproducible.

### Year-to-year delta

| Transition | prev | curr | NEW | PERSISTENT | DISAPPEARED |
|------------|-----:|-----:|----:|-----------:|------------:|
| 2013→2014 | 399 | 450 | 77 | 373 | 26 |
| 2014→2015 | 450 | 494 | 59 | 435 | 15 |
| 2015→2016 | 494 | 522 | 55 | 467 | 27 |
| 2016→2017 | 522 | 560 | 66 | 494 | 28 |
| 2017→2018 | 560 | 576 | 43 | 533 | 27 |
| 2018→2019 | 576 | 579 | 39 | 540 | 36 |

Monotonic growth (399→579) tracks the 2013–2019 new-distillery boom. "DISAPPEARED"
entries are overwhelmingly editorial omissions (dropped entities remain `Operating` in
production), NOT closures.

### Cumulative net-new + production saturation

| Edition | Detected | Net-new vs earlier | Production saturation |
|---------|---------:|-------------------:|----------------------:|
| 2013 | 399 | 399 | 18.6% |
| 2014 | 450 | 77 | 21.0% |
| 2015 | 494 | 55 | 23.0% |
| 2016 | 522 | 49 | 24.3% |
| 2017 | 560 | 45 | 26.1% |
| 2018 | 576 | 35 | 26.9% |
| 2019 | 579 | 26 | 27.0% |

Union 2013–2019 = **686 distinct canonical distilleries = 32.0% of production's 2,144.**
Distilleries in 2013–2018 but absent from 2019 = 107, of which only 7 have a real
production status — and all 7 are still `Operating` (absence = matching/editorial, not closure).

**Gap left by Method 1:** cannot detect distilleries present in a Yearbook but absent from
production.db (search space limited to known names). Closed by Method 2.

---

## METHOD 2 — Open-vocabulary discovery (out-of-production entities)

Extracted `<Name> Distillery` candidates WITHOUT limiting to production names.
835 raw → 414 residual (after subtracting production lexicon, whisky/brand names, noise).
Decisive test: which residuals are genuinely absent from the 2019 baseline text AND absent
from production.

**Result: TRUE_NEW_CURRENT_DISTILLERY unique to a pre-2019 edition = 0.**

Verification found ~70% of apparent "absent from 2019" names were actually present in 2019
under OCR variance (Overeem, White Oak, Nantou, Redlands, Shene, Het Anker, Alazana,
Seven Stills, Vikre, Victoria Caledonian, Torabhaig, ...).

### Historical / project findings (book-authoritative evidence; NOT production entities)

| Name | Editions | Classification | Evidence |
|------|----------|----------------|----------|
| Gartbreck | 2014–2018 | HISTORICAL (abandoned project) | Jean Donnay's planned 9th Islay distillery on Loch Indaal — never completed |
| The Longship | 2015–2016 | POSSIBLE_RENAME (announcement) | Swedish owner announced move to Orkney — plan, not built |
| Hillock Park | 2015–2018 | HISTORICAL (German micro) | ~50 casks/year micro-producer; faded from later editions |
| Wilsons Willowbank | 2013–2018 | HISTORICAL (closed NZ) | Decommissioned Dunedin distillery; historical stock only |
| Strathmeldrum | 2013–2016 | NON_ENTITY | Appears only inside Glen Garioch's 1837 history timeline |

These are deferred to a possible future **historical/project knowledge layer** — NOT a
production entity-expansion justification.

### Rename / alias review (NO auto-merge; deferred to identity-resolution task)

| Old / variant | Current (in 2019 + production) | Confidence |
|---------------|-------------------------------|-----------|
| Yuan Shan / Yuanshan | Kavalan (King Car, Taiwan) | HIGH → REVIEW |
| Glengarioch | Glen Garioch (spacing) | HIGH |
| Cardow | Cardhu | HIGH → REVIEW |
| Pitilie | Aberfeldy | MEDIUM → REVIEW |
| Aldour | Edradour | MEDIUM → REVIEW |
| `*-Glenlivet` suffixes (Tomintoul-, Linkwood-, Glenlossie-, Tamnavulin-, Speyburn-, Balmenach-) | base distillery already in production | HIGH |

---

## FINAL DECISION TABLE

| Edition | TRUE NEW current | TRUE HISTORICAL | Rename/Merge | Net incremental entity value | Decision |
|---------|-----------------:|----------------:|-------------:|------------------------------|----------|
| 2013 | 0 | 2 | 3 | Minimal (oldest snapshot) | HISTORICAL_OPTIONAL |
| 2014 | 0 | 2 | 3 | ~0 | HOLD_REDUNDANT |
| 2015 | 0 | 1 | 2 | ~0 | HOLD_REDUNDANT |
| 2016 | 0 | 1 | 2 | ~0 | HOLD_REDUNDANT |
| 2017 | 0 | 0 | 1 | ~0 | HOLD_REDUNDANT |
| 2018 | 0 | 0 | 1 | ~0 | HOLD_REDUNDANT |
| 2019 | baseline | — | — | ingested (B1) | KEEP / BASELINE |

---

## SAFETY GATE (audit execution)

- production.db SHA before: `5cdac019caca84689b22510692c777995251de8dd25260b1547acffe66777b58`
- production.db SHA after:  `5cdac019caca84689b22510692c777995251de8dd25260b1547acffe66777b58` (UNCHANGED)
- production.db modified? NO (opened `mode=ro`) · knowledge.db touched? NO · staging touched? NO
- ingestion? NO · staging insertion? NO · promotion? NO · PromotionGate invoked? NO
- files modified/renamed/moved/deleted? NO · DENY ACE / filesystem protection touched? NO

Temporary analysis artifacts were kept under `%LOCALAPPDATA%\Temp\` during the audit and
cleaned up after this report was written.

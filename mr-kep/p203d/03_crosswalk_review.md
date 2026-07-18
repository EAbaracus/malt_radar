# P203D — Task 3: Crosswalk Review (`review_required = true`)

> 8 records require review. Read-only. **No aliases created. No canonical
> entities created.** Candidate matches below are computed by read-only
> substring lookup against `production.distilleries` for human reference only.
> Decision default = **KEEP REVIEW** (await human promotion gate).

| evidence_id | external (distillery_raw) | reason | candidate matches (distilleries) | decision |
|---|---|---|---|---|
| EDR-848b11c0a2bc77d9 | `millstone` | unmatched; canonical_distillery_id NULL, crosswalk_confidence=0 | `D1658` "T" (false-pos substring) — no real Millstone | **KEEP REVIEW** |
| EDR-9966e1386d85e89d | `a` (parse artefact) | unmatched | D0001 Aberlour, D0002 Laphroaig, D0004 Talisker … (all false — 'a' is a stopword) | **KEEP REVIEW** |
| EDR-4729c2981c6e18ff | `black` (parse artefact) | unmatched | (none relevant) | **KEEP REVIEW** |
| EDR-ee993542bf9862ae | `curraghmore` | unmatched | (none) — Curraghmore not in distilleries | **KEEP REVIEW** |
| EDR-c488862aa5c275b7 | `hollow` (parse artefact) | unmatched | (none) | **KEEP REVIEW** |
| EDR-a58ff50909dbfa5b | `kwun` (parse artefact) | unmatched | (none) — Kwun Cheung Chinese malt not in distilleries | **KEEP REVIEW** |
| EDR-03658c1c6fca47ab | `curraghmore` (dup of ee99) | unmatched | (none) | **KEEP REVIEW** |
| EDR-81750202464cb39d | `copperworks` (parse artefact) | unmatched | (none) — Copperworks not in distilleries | **KEEP REVIEW** |

## Notes
- **5 of 8** are distillery-parse artefacts (`a`, `black`, `hollow`, `kwun`,
  `copperworks`) — clearly not real canonical distillery names. They are
  correctly queued, not force-matched.
- **3 of 8** are genuinely-absent real-world distilleries (`millstone`,
  `curraghmore`, `kwun`/Kwun Cheung) — coverage gaps in `distilleries`,
  analogous to the P203B bourbon gaps. Resolvable only by extending
  `distilleries` coverage (out of scope for P203D).
- No candidate match meets the P203B deterministic exact/normalized rule, so
  **0 auto-accepts** and **0 rejects-with-fabrication** occurred.
- All 8 remain in `review_required` for the human promotion gate.

## Decision tally
- accept: **0**
- keep review: **8**
- reject: **0**

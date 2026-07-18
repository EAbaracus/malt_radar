# P95B Phase 12 — Promotion Report

**Scope:** promote validated P95B book + crosswalk-resolved tasting-note evidence into
`production.db` (`flavor_evidence` + `flavor_profiles`), preserving the frozen canonical
7-axis contract (`smoky, peaty, fruity, sweet, spicy, maritime, sherry` @0-100).

---

## What was promoted
| Source | Candidates | Promoted to flavor_evidence | Skipped | Profiles inserted |
|---|---|---|---|---|
| Book (7-axis complete, has whisky_id) | 8 | 8 (`source='book'`) | 0 | 0 (all wids had profile) |
| Tasting notes (crosswalk-resolved, not rejected) | 263 | 188 (`source='tasting_note'`) | 75 | 0 (all wids had profile) |
| **Total** | **271** | **196** | **75** | **0** |

## Canonical contract compliance
- All 196 new `flavor_evidence` rows carry the **7 canonical axes** (0-100 scale).
- **`maritime` preserved end-to-end**: 196/196 new rows have `vector_maritime` non-NULL
  (book values 35–68; tasting-note values derived via canonical reducer from real
  "sea/salt/seaweed" text).
- **`rich` never entered canonical output**: new rows store `vector_rich = NULL`
  (legacy `vector_rich` on the 791 pre-existing rows is retained, never dropped).
- **No legacy axes leaked** (oak/winey/waxy/malty/…) — only the canonical 7.

## Authority preservation (no overwrite)
- Promotion is **INSERT-only**. Any `whisky_id` already present in `flavor_evidence`
  was skipped (book: 0 such; tasting: rows whose wid already had evidence).
- `flavor_profiles` rows were **never UPDATEd** — 0 profiles inserted because all 196
  promoted `whisky_id`s already owned a profile row (T1/T2 authority intact).

## Skipped rows (with reasons)
75 tasting notes skipped: `matched_master_whisky_id` resolved + not rejected, but the
free-text note contained **no canonical descriptor tokens** (lexicon: sea/salt/peat/apple/
honey/…). These were NOT force-fit into a canonical vector — they are reported in
`promotion_audit_log.json` (each with `whisky_id`, `staging_note_id`, reason) for
later human review / lexicon expansion.

## Normalization
Staging book axis columns are already 0-100; the canonical reducer emits 0-100.
Promoted `flavor_evidence` values are stored consistently at 0-100 (the canonical scale).
No 0-1 → 0-100 rescale was needed because no promoted row came from a 0-1 source.

## Sample promoted evidence (verified)
```
P95B_…  W002573  book        44 55 50 50 35 35 44   (maritime=35)
P95B_…  W000014  book        50 55 72 68 59 68 44   (maritime=68)
P95B_…  W001980  tasting_note 50 55 50 35 35 35 35   (maritime=35)
```

## Final Status
**PASS — Phase 12 completed successfully.** 196 canonical-evidence rows promoted with
`maritime` intact; 75 non-canonical notes skipped with reasons; 0 authority overwrites.

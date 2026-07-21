# P95B-FIX-03 — Promotion Rehearsal Report

**Mode:** READ-ONLY. No schema migration, no production/staging writes, no commit/push/tag.
**Date:** 2026-07-17
**Method:** the full promotion pipeline was executed **entirely in memory** against live staging data,
using the canonical reducer + db_read_service normalization from P95B-FIX-02. production.db was
opened read-only (`mode=ro` + `PRAGMA query_only=ON`).

---

## 1. Pipeline exercised (in-memory)
```
staging_*  ──►  promotion mapper (canonical 7-axis)  ──►  canonical reducer
   (axis       (FlavorMapper: descriptor/axis -> canonical)   (AxisReducer: 1-5 -> 0-100,
    columns                                                        emits frozen 7 incl maritime)
    + free-text
    tasting notes)                                           ──►  canonical_vectors (7 axes)
                                                               ──►  db_read_service._normalize_flavor_profile
                                                                    ──►  candidate flavor_profile JSON
```
The reducer/mapper are the canonical P95B-FIX-02 versions (maritime included). Free-text
tasting notes were tokenized to descriptor words and run through the canonical reducer (real
text→canonical path, e.g. `salt`/`sea`/`seaweed` → `maritime`).

## 2. Representative records selected (covering all 7 canonical axes)
| Src | Label | Whisky | whisky_id | Covers |
|---|---|---|---|---|
| book | all7_1..5 | BUNNAHABHAIN, Loch Lomond, ardbeg, Glen Scotia, Benriach | W002573…W002288 | all 7 axes **incl maritime** |
| tasting_note | text_1..3 | (free-text; seaweed/salt/peat notes) | *None in staging* | all 7 incl maritime (text path) |
| book | oak_legacy | Paul John Edited | W001042 | legacy `oak` present → must be dropped |
| notebooklm | smoky | paul john edited | W001042 | cross-source path (maritime=0) |

## 3. Canonical flavor_profile JSON produced
See `canonical_profile_samples.json` (8 samples + per-sample checks) and
`canonical_profile_samples_extra.json` (legacy + notebooklm). Example (ardbeg, W001980):
```json
{"smoky":50.0,"peaty":55.0,"fruity":50.0,"sweet":35.0,"spicy":35.0,"maritime":35.0,"sherry":35.0}
```
Note-text sample (real "seaweed…Salty, seaweedy" note) → `{"peaty":60,"maritime":100,…}` — maritime
correctly surfaced from free text.

## 4. Verification (all required gates)
| Check | Result |
|---|---|
| All 7 canonical axes present in every candidate | ✅ 8/8 |
| maritime preserved end-to-end (book + free-text) | ✅ 35/35/35/68/35 (book); 100/60/60 (text) |
| `rich` never appears in canonical output | ✅ 0 occurrences |
| No legacy axes leak (oak/winey/waxy/malty/nutty/herbal/oily/light_body/rich_body) | ✅ 0 leaks (oak dropped from W001042) |

## 5. Diff vs current production profiles
For the 5 book candidates that already have a `flavor_profiles` row, the candidate adds/refreshes the
canonical 7-axis vector **including `maritime`** (currently absent from production `flavor_evidence`
and only partially present in `flavor_profile`). No spurious axis appears. (Full per-axis diff in
`production_diff_report.md`.)

## 6. Findings beyond the pass criteria
- **F1 (notebooklm cannot contribute maritime):** `staging_notebooklm_flavor_profiles.maritime`
  is 0 for all 17 rows → maritime from NotebookLM sources is unavailable. Non-blocking; book + note
  text cover maritime.
- **F2 (tasting-note whisky_id is NULL):** `staging_tasting_notes.whisky_id` is `None` for the
  maritime-bearing rows. The in-memory rehearsal mapped them correctly to canonical axes, but at real
  promotion these notes must be bound to a `whisky_id` (via the existing crosswalk from P203B) before
  they become candidates. **Action item for Phase 12, not a blocker for this rehearsal.**

## 7. VERDICT — GO ✅
The complete promotion pipeline, executed entirely in memory against live staging, produces canonical
7-axis `flavor_profile` candidates that: contain all seven canonical axes, preserve `maritime`
end-to-end (from both structured staging columns and free-text notes), never emit `rich`, and leak no
legacy axes. Combined with P95B-FIX-02 (regression 7/7) this clears the Phase 12 content gates.

**Caveat:** the single remaining gate is the *schema* step — `vector_maritime` must be added to
production `flavor_evidence` via `migration.sql` (gated, not yet executed; see P95B-FIX-02). The
rehearsal proves the **data/layer logic is correct**; the schema mutation remains pending explicit GO.

**No production mutation occurred.** production.db SHA `8350fe9d…` unchanged.

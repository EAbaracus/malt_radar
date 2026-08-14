# P251 — 03 — NAMESPACE MERGE SIMULATION (Wave B)

**Mode:** READ_ONLY · **In-memory dry-run.** Canonicalize D1091 → D0010 (MERGE_SAFE from P250).

## 1. The duplicate

| | loser | survivor |
|---|-------|----------|
| `distillery_id` | **D1091** (`Glenﬁddich`, U+FB01) | **D0010** (`Glenfiddich`, Speyside, Operating) |
| `data_confidence` | `staged_import` | (canonical) |

## 2. Repoint set (simulated, no write)

| Child table | Rows repointed D1091→D0010 | Evidence note |
|-------------|---------------------------:|--------------|
| `whiskies` | **5** (W002110, W002141, W002269, W002537, W002554) | distinct expressions (post-NFKC overlap with D0010 = 0) |
| `tasting_notes` | **5** | Whisky Advocate, scores 89–94, `data_confidence='high'` |
| `flavor_profiles` | **5** | linked via `whisky_id` (no `distillery_id` col) |

## 3. Evidence-loss check (the critical assertion)

- `flavor_evidence` rows referencing the 5 D1091 whiskies: **0** → nothing lost.
- `flavor_profiles` rows referencing them: **5** → **preserved** via repoint.
- `tasting_notes`: **5** high-value rows → **preserved** via repoint.
- `distillery_company_links` for D1091: **0** (no orphan links).

→ **Evidence loss = 0.** All 15 child records carry over to D0010 intact. No `whisky_id` changes;
the 5 whiskies keep their identities, merely re-parented to the canonical distillery.

## 4. Identity & FK after Wave B

- `whiskies.distillery_id` of the 5 rows → D0010 (valid, Speyside). FK intact.
- D0010 whisky count would rise 24 → 29; D1091 would become orphan → deprecated (not deleted).
- No name change on the 5 whiskies in Wave B (name normalization is Wave C).

## 5. Idempotency

Repoint is keyed on current `distillery_id='D1091'`. After wave 1, D1091 has 0 children → re-apply
changes 0 rows. ✅

## 6. Conclusion

Wave B is simulation-verified: 5+5+5 records repointed, **zero evidence loss**, FK-valid,
idempotent. The P250 MERGE_SAFE decision is confirmed safe to execute. No write.

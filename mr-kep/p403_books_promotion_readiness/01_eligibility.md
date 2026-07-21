# P403 — 01 Eligibility

**READ-ONLY preparation. Production SHA: `3c56de601c53…`**

| Metric | Count |
|---|---|
| Total rows | 2,577 |
| Invalid whisky_id rows (`UNRESOLVED_P32` etc.) | **774** (excluded) |
| Valid rows | 1,803 |
| Duplicate whisky_id rows (among valid) | 1,799 |
| Distinct valid whisky_ids | 64 |
| Already `promoted` | 2 |
| Pending review | 2,575 |
| **Eligible rows (deduped, 1 best/whisky)** | **64** |
| Eligible distinct whiskies | 64 |

**Eligibility rule applied:** valid `Wxxxx` id + not already promoted + deduped to the single best-populated row per whisky_id. The 774 `UNRESOLVED_P32` placeholder rows and the 1,799 duplicate rows are excluded.

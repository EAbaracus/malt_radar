# P140 — Field Census (Phase 1)

- doc_version: P140-1
- date_utc: 2026-07-17
- mode: READ-ONLY. production.db opened `mode=ro` + `query_only=ON`. No writes.
- table: whiskies (4,749 rows). All TEXT/numeric columns censused.

## Per-column census
| column | NULL | empty-string '' | whitespace | non-empty | "" % |
|---|---|---|---|---|---|
| name | 0 | 0 | 0 | 4749 | 0.00 |
| original_name | 3376 | 0 | 0 | 1373 | 0.00 |
| country | 4614 | 0 | 0 | 135 | 0.00 |
| region | 3619 | **713** | 0 | 417 | 15.01 |
| type | 2892 | 0 | 0 | 1857 | 0.00 |
| age_statement | 2722 | **791** | 0 | 1236 | 16.66 |
| nas | 4601 | 0 | 0 | 148 | 0.00 |
| bottle_size | 4710 | 0 | 0 | 39 | 0.00 |
| cask_type | 4068 | 0 | 0 | 681 | 0.00 |
| finish_type | 4749 | 0 | 0 | 0 | 0.00 |
| cask_strength | 4749 | 0 | 0 | 0 | 0.00 |
| completed_fields | 4749 | 0 | 0 | 0 | 0.00 |
| notes_for_review | 4749 | 0 | 0 | 0 | 0.00 |
| brand | 2880 | 0 | 0 | 1869 | 0.00 |

## Key finding
- **Only TWO columns contain empty-string `''`: `region` (713) and `age_statement` (791).**
- **FOUR columns (`finish_type`, `cask_strength`, `completed_fields`, `notes_for_review`) are 100% NULL** — they never contain `''`.
- Every other populated column uses NULL (never `''`).
- **Conclusion:** the schema's established convention for "no data" is **SQL NULL**.
  The `''` values in `region`/`age_statement` are an **inconsistency / anomaly**, not a
  deliberate encoding. This directly supports the P139 hypothesis that the 530 skipped
  rows were skipped because they held `''`, not NULL.

## Machine-readable
See `missing_value_statistics.csv` (generated, per-column counts + percentages).

# P142 — Region Coverage: Before / After

- doc_version: P142-1 (corrected)
- date_utc: 2026-07-17
- total whiskies: 4749
- Baseline region breakdown from P140 census (post-P139, pre-P141): real-nonempty=417,
  empty-string ''=713, NULL=3619 (IS NOT NULL = 1130, counting the 713 '').

## Region completeness timeline (real non-empty values, '' excluded)
| snapshot | region real-nonempty | region '' (empty) | region NULL | completeness % |
|---|---|---|---|---|
| Before P139 (P140 census) | 417 | 713 | 3619 | 8.78% |
| After P139 (628 NULL_FILL) | 418 | 713 | 3618 | 8.80% |
| After P141 ('' -> NULL) | 417 | 0 | 4332 | 8.78% |
| **After P142 (530 deferred fills)** | **947** | **0** | **3802** | **19.94%** |

## Region completeness timeline (IS NOT NULL view, '' counted as "present")
| snapshot | region IS NOT NULL | region NULL | note |
|---|---|---|---|
| Before P139 | 1130 | 3619 | includes 713 '' |
| After P141 | 417 | 4332 | 713 '' -> NULL |
| After P142 | 947 | 3802 | +530 real fills |

## What each phase did
- **P139**: applied 628 NULL_FILL (627 cask_type + 1 region). 530 region candidates were
  skipped because they held `''` (non-NULL) — see P140.
- **P141**: normalized `''` -> NULL in `region` (713) + `age_statement` (791). This made the
  530 deferred region rows genuinely NULL (region real-nonempty stayed 417; IS NOT NULL dropped 1130 -> 417).
- **P142**: filled those 530 now-NULL region cells with high-confidence SMWS values.

## Net region gain (real non-empty)
- Before P139: 417 non-empty
- After P142: 947 non-empty
- **gain: +530 regions** (the deferred P139 set, exactly as planned)
- Live post-write verification: region real-nonempty = 947 (confirms all 530 applied).

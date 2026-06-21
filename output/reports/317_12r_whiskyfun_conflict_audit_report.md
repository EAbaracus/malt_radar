# 12R Whiskyfun Conflict Audit

## Sonuç

- Gate: `GO_MATCHER_TUNING_RECOMMENDED`
- Toplam satır: `11149`
- REJECT_CONFLICT: `6516`
- REJECT_LOW_CONFIDENCE: `2295`
- REVIEW score >= 94 yükseltme adayı: `430`
- Distillery-only score >= 90 yükseltme adayı: `0`
- Full text sızıntısı: Yok
- production.db kullanıldı mı: Hayır
- Source public output var mı: Hayır

## Decision dağılımı

decision
REJECT_CONFLICT                 6516
REJECT_LOW_CONFIDENCE           2295
REVIEW_PRODUCT_FEATURE          1497
KEEP_DISTILLERY_FEATURE_ONLY     664
KEEP_PRODUCT_FEATURE             177

## En sık conflict flag

- low_name_score: 5889
- age_mismatch: 5371
- vintage_mismatch: 1416
- release_mismatch: 630
- distillery_mismatch: 111
- bottler_mismatch: 63
- cask_mismatch: 55

## En sık conflict kombinasyonları

- age_mismatch|low_name_score: 4351
- age_mismatch|low_name_score|vintage_mismatch: 492
- age_mismatch: 436
- low_name_score|release_mismatch|vintage_mismatch: 410
- low_name_score|vintage_mismatch: 378
- release_mismatch: 132
- distillery_mismatch|low_name_score: 71
- low_name_score|release_mismatch: 48
- vintage_mismatch: 48
- age_mismatch|bottler_mismatch|low_name_score: 28
- age_mismatch|bottler_mismatch|low_name_score|vintage_mismatch: 18
- age_mismatch|cask_mismatch|low_name_score|vintage_mismatch: 16
- distillery_mismatch|low_name_score|vintage_mismatch: 10
- age_mismatch|cask_mismatch|distillery_mismatch|low_name_score|release_mismatch|vintage_mismatch: 9
- cask_mismatch|low_name_score: 8
- distillery_mismatch|low_name_score|release_mismatch|vintage_mismatch: 7
- bottler_mismatch|low_name_score|release_mismatch: 6
- bottler_mismatch|low_name_score|release_mismatch|vintage_mismatch: 6
- cask_mismatch|low_name_score|vintage_mismatch: 6
- age_mismatch|cask_mismatch|low_name_score|release_mismatch|vintage_mismatch: 5

## Öneri

REJECT_CONFLICT oranı yüksekse matcher fazla muhafazakâr olabilir.

Bir sonraki aşamada:
- Age/vintage mismatch güçlü conflict olarak kalmalı.
- Cask/bottler mismatch bazı durumlarda REJECT yerine REVIEW yapılabilir.
- Low name score tek başına varsa distillery-level feature olarak değerlendirilebilir.

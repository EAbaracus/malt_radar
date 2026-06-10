# Pending Candidate Sources Status Report

## 1. Çekirdek Production Hattı — 67_FINAL / Whisky.com
- **Production DB’ye işlendi mi?** Evet, update-only metadata backfill olarak.
- **Distillery count:** 990
- **whisky_com_url:** 82
- **bottle_count metadata:** 77
- **region patch:** 6
- **insert/delete/overwrite:** 0
- **Durum:** CLOSED / LOCKED

## 2. Malt List
- **Production DB’ye işlendi mi?** Hayır.
- **LOW risk historical_menu_price candidate:** 23
- **Manual review price candidate:** 57
- **current_price olarak kullanılabilir mi?** Hayır
- **Tasting note extraction durumu:** mevcut parse yetersiz, PDF reparse gerekir
- **Durum:** CANDIDATE / PENDING

## 3. Whisky Edition API
- **Production DB’ye işlendi mi?** Hayır.
- **fetched review:** 523
- **parsed tasting note candidate:** 522
- **source_verified tasting note candidate:** 522
- **new product candidate:** 518
- **manual review:** 5
- **automatic patch:** hayır
- **AŞAMA 3 entity model gerekli mi?** Evet
- **Durum:** CANDIDATE / STAGING

## 4. WhiskeyFYI
- **Production DB’ye işlendi mi?** Hayır.
- **68_FINAL candidate üretildi**
- **19 safe description enrichment candidate**
- **knowledge regions/glossary/guides preview hazır**
- **Durum:** CANDIDATE / AŞAMA 3 KNOWLEDGE

## 5. Genel Sonuç
- Çekirdek production hattı tamamlandı.
- Malt List, Whisky Edition API ve WhiskeyFYI production’a alınmadı.
- Bunlar AŞAMA 3 / staging / manual approval sürecine aktarılacak.
- Yeni import/patch yapılmadan önce AŞAMA 3 schema ve approval workflow kurulmalı.

## 6. Sıradaki Tavsiye
- **AŞAMA 3:** Brands / Bottlers / Companies / External Links / Knowledge Tables / Product Candidate Staging
- Bu aşama ayrı branch, ayrı migration, ayrı dry-run olarak başlatılmalı.

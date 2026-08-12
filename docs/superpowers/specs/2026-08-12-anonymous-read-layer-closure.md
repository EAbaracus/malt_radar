---
title: Anonymous Read Layer — Closure Report
date: 2026-08-12
status: CLOSED
tags: [anonymous-read-layer, guest-mode, allowlist, public-api, closure]
related_spec: docs/superpowers/specs/2026-08-12-anonymous-read-layer-design.md
related_plan: docs/superpowers/plans/2026-08-12-anonymous-read-layer.md
production_sha_before: a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4
production_sha_after:  a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4
---

# Anonymous Read Layer — Kapanış Raporu

**Hedef:** Malt Radar uygulamasını denemek isteyen anonim kullanıcılara, kayıt/login engeli olmaksızın küratörlü, sınırlı bir katalog alt kümesini (N=150 Tier A viski) güvenli ve SEO uyumlu biçimde açmak.

**Sonuç:** Mimarisi doğrulandı, 4 aşamalı TDD planı uygulandı, veritabanı bütünlüğü korundu (`production.db` SHA değişmedi), backend pytest (117 passed, 1 skipped) ve frontend Flutter test (108 passed) süitleri %100 yeşil teslim edildi.

---

## Modül ve Commit Özeti

| Aşama | Commit | Kapsam | Kabul |
|---|---|---|---|
| **Task 1 (AL-A)** | `3dd3ef9` | `scripts/build_anonymous_allowlist.py` (deterministik allowlist scripti), `ProductionReadAdapter.raw_connection()` (izole read seam), `backend/tests/test_allowlist_build.py` | PASSED (7 test) |
| **Task 2 (AL-B)** | `ace18ed` | `backend/app/services/anonymous_catalog_service.py` (allowlist intersect + 8-axis presentation shaping + fiyat temizleme), `backend/tests/test_anonymous_catalog_service.py` | PASSED (4 test) |
| **Task 3 (AL-C)** | `e73f8d5` | `backend/app/routers/db_public_api.py` (bağımsız `/api/db/public/*` router), `backend/app/main.py` (router mount), `backend/tests/test_db_public_api.py` | PASSED (4 test) |
| **Task 4 (AL-D)** | `be028bc` | `frontend/lib/core/api/db_whisky_api_client.dart` (`_basePath` routing), `AuthScreen` ("Misafir Olarak İncele" butonu), `main.dart` (`guestModeProvider`), `guest_mode_navigation_test.dart` | PASSED (108 test) |
| **Dokümantasyon** | `5153a67` | `docs/superpowers/specs/2026-08-12-anonymous-read-layer-design.md`, `docs/superpowers/plans/2026-08-12-anonymous-read-layer.md` | COMPLETE |

---

## Güvenlik ve Mimari Garantiler

1. **Sıfır DB Mutasyonu:** `production.db` SHA `a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4` aynen korundu. Tüm okumalar `ProductionReadAdapter` (`mode=ro` + `PRAGMA query_only=ON`) üzerinden yapıldı.
2. **Product Rule Koruması:** Fiyat kolonları (`production_price`, `price_value`, `price_context`, `pour_size_ml`) `AnonymousCatalogService._shape_whisky` seviyesinde kesin olarak temizlendi.
3. **Route İzolasyonu (Option A):** `/api/db/public/whiskies/{id}/evidence` ve `/price-history` endpoint'leri public router'da tanımlanmadı (404). Authenticated `/api/db/*` router'ı üye kullanıcılar için korundu.
4. **Cache & Scope İzolasyonu:** Yollar fiziksel olarak ayrıldığı için CDN/Cloudflare edge cache karışması ve authenticated yanıt sızıntısı riski ortadan kaldırıldı.

---

## Doğrulama Sonuçları

- **Backend Pytest Suite:** 117 passed, 1 skipped (`test_seeder_script_fails_loudly` — manuel seed scripti koruma testi).
- **Frontend Flutter Test Suite:** 108 passed, 0 failed.
- **Pre-commit Gates:** Tüm repo state, DB mutation guard, G4 write-path guard ve brand token kontrollerinden başarıyla geçti.

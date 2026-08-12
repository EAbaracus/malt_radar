# Anonim Okuma Katmanı — Design Spec

- **Tarih:** 2026-08-12
- **Durum:** NİHAİ (Spec Review Passed)
- **Kapsam:** Anonim Okuma Katmanı (allowlist + `/api/db/public/*` namespace + response shaping + guest UI + verification)
- **Mimari Karar:** Option 2 (Authenticated-only evidence/price) + Option A (Ayrı `/api/db/public/*` namespace)
- **Önceki kararlar:** ff28225 (2026-08-10, per-user bearer gate restore) — bu spec onun **bilinçli kapsam genişletmesi**dir.

---

## 1. Problem ve Amaç

Flutter uygulamasında katalog tamamen login arkasında (`main.dart:107`). Denemek isteyen kullanıcılar zorunlu kayıt engeline takılıyor.

**SEO Katmanı Tutarsızlığı:** SEO katmanı (`seo/` SSG + `deploy/Caddyfile` `@seo`) 2.483 Tier A viskiyi public statik HTML olarak sunuyor (`Cache-Control: public, max-age=3600`). Sayfalarda `flavor_profile` 8 app eksenine dönüştürülmüş, fiyat yok, ham JSON yok.

Bu spec, Flutter uygulamasına aynı veriyi **aynı kurallarla (response shaping)** ve **sınırlı bir alt küme (bounded allowlist, N=150)** ile ayrı bir kamu namespace'i (`/api/db/public/*`) üzerinden açar.

---

## 2. Governance Kararları

| # | Karar | Gerekçe |
|---|-------|---------|
| **G1** | **Bilinçli Kapsam Genişletmesi** | ff28225 kararı bozulmaz. Maruziyet artırılmaz, SEO katmanının sınırı API'ye aktarılır. |
| **G2** | **Katman Ayrımı (Hardening Scope Dışı)** | WAF, bot koruması, ToS/robots güncellemeleri ayrı operasyonel hardening fazındadır. |
| **G3** | **Ayrı Namespace: `/api/db/public/*` (Option A)** | Auth-optional aynı path karmaşası biter. Path-level cache, WAF ve static lint garantisi sağlanır. |
| **G4** | **Evidence & Price Authenticated-Only (Option 2)** | Logged-in kullanıcılar "Resmî Kaynaklar"ı görmeye devam eder (`/api/db/*`). `/api/db/public/*` altında bu route'lar **hiç tanımlanmaz**. |
| **G5** | **Build-Time Deterministik Allowlist** | Allowlist `artifacts/anonymous_allowlist.json` build çıktısıdır. Runtime re-derive etmez. |
| **G6** | **SEO Response Shaping Parity** | `flavor_profile` ham JSON değil 8 eksen map; ham evidence row yok, fiyat yok. |

---

## 3. Mimari ve API Yüzeyi

### Public Router: `backend/app/routers/db_public_api.py` (`/api/db/public`)

- Hiçbir `get_current_user` bağımlılığı içermez.
- Tüm sorgular `AnonymousCatalogService` üzerinden `artifacts/anonymous_allowlist.json` kümesiyle **intersect** edilir.

| Endpoint | Erişim | Davranış |
|---|---|---|
| `GET /api/db/public/whiskies` | Public | Bounded allowlist alt kümesi (`offset/limit` allowlist boyutu N ile sınırlı) |
| `GET /api/db/public/whiskies/{id}` | Public | id ∉ allowlist → 404 |
| `GET /api/db/public/whiskies/{id}/flavor-profile` | Public | id ∉ allowlist → 404. Shaped 8 eksen |
| `GET /api/db/public/search` | Public | Sonuçlar allowlist ile filtrelenir |
| `GET /api/db/public/distilleries` | Public | Yalnızca allowlist viskilerinin damıtımevleri |
| `GET /api/db/public/filters` | Public | Sabit filtre vokabüleri |
| `GET /api/db/public/whiskies/{id}/evidence` | **YOK (404)** | Public router'da tanımlı değil |
| `GET /api/db/public/whiskies/{id}/price-history` | **YOK (404)** | Public router'da tanımlı değil |

### Authenticated Router: `backend/app/routers/db_api.py` (`/api/db`)
- Mevcut `Depends(get_current_user)` koruması aynen devam eder.
- `GET /api/db/whiskies/{id}/evidence` ve `price-history` üye kullanıcılar için çalışmaya devam eder.

---

## 4. Cache Kontratı (Yapısal İzolasyon)

Ayrı namespace tercih edildiği için CDN / Proxy seviyesindeki karmaşıklık çözülmüştür:

1. **`/api/db/public/*`:** `Cache-Control: public, max-age=300` (veya Caddy varsayılanı). Yanıtlar sınırlı ve shaped olduğu için public edge-cache güvenlidir.
2. **`/api/db/*` (Authenticated):** `Cache-Control: private, no-store` ( FastApi katmanında zorunlu).
3. URL yolları farklı olduğu için public ve authenticated yanıtların birbirine sızma ihtimali **fiziksel olarak imkansızdır**.

---

## 5. Allowlist Build Katmanı (`scripts/build_anonymous_allowlist.py`)

- **Kaynak:** `production.db` (Read-only URI)
- **Filtre:** `seo.tiers.tier_map()` → Tier A ∩ Sitemap
- **Sıralama:** `evidence_count DESC, name ASC, whisky_id ASC`
- **Sınır:** İlk N kayıt (`ANONYMOUS_CATALOG_LIMIT`, varsayılan 150)
- **Çıktı:** `artifacts/anonymous_allowlist.json` (`version`, `build_date`, `db_sha256`, `ids`)

---

## 6. Guest UI (Flutter)

1. `AuthScreen` içerisine **"Misafir Olarak İncele"** seçeneği eklenir.
2. Guest modunda `DbWhiskyApiClient` istekleri `/api/db/public/*` adresine yönlendirilir.
3. Detay ekranında `isLoggedIn == false` ise "Resmî Kaynaklar" bölümü gizlenir (public API'de route 404 olduğu için).
4. Favorilere ekleme veya kişisel not gibi yazma eylemleri login ekranına yönlendirir.

---

## 7. Verification Test Matrisi

- **T1 Allowlist Determinism:** Aynı DB + N → Birebir SHA256 eşleşen artifact JSON.
- **T2 Containment & Boundary:** Public API sonuç kümesi ⊆ allowlist `ids`. `offset=149, limit=100` → Taşma hatası vermez, sınır sonrası boş dizi döner.
- **T3 Response Shaping & Leakage:** Public yanıtlarda `production_price`, `price_value`, ham `flavor_evidence` satırları asla yer almaz.
- **T4 Route Isolation:** `/api/db/public/whiskies/{id}/evidence` isteği doğrudan 404 döner.
- **T5 Auth Regression:** `/api/db/*` Bearer auth akışı ve 53+ pytest testi yeşil kalır.
- **T6 Guest UI Integration:** Flutter widget testleri guest gezinmesini doğrular.

---

## 8. Uygulama Sıralaması (Sequencing)

1. `build_anonymous_allowlist.py` scripti ve `test_allowlist_build.py` doğrulaması.
2. `AnonymousCatalogService` ve `db_public_api.py` backend router'ının yazılması.
3. `/api/db/public` endpoint ve shape testlerinin (T1-T5) çalıştırılması.
4. Flutter `DbWhiskyApiClient` public endpoint adaptasyonu ve Guest UI entegrasyonu (T6).

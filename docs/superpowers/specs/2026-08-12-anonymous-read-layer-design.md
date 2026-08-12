# Anonim Okuma Katmanı — Design Spec

- **Tarih:** 2026-08-12
- **Durum:** TASLAK — insan onayı bekliyor (spec review gate)
- **Kapsam:** Anonim Okuma Katmanı (allowlist + anonymous `/api/db/*` read + response shaping + guest UI + cache contract + verification)
- **Sözlük:** /codebase-design — module, interface, seam, contract, bounded set
- **Önceki kararlar:** ff28225 (2026-08-10, per-user bearer gate restore) — bu spec onun **bilinçli kapsam genişletmesi**, sessiz tersine çevrilmesi DEĞİL (bkz. §1, §2 G1)

---

## 1. Problem

Flutter app'te katalog **tamamen login arkasında**: `main.dart:107` — `!auth.isLoggedIn → AuthScreen`. Kullanıcı geri bildirimi: "if I can't see or try an app without creating a login and providing personal information, the app is not for me."

**Tutarsızlık:** SEO katmanı zaten aynı veriyi anonim servis ediyor. `deploy/Caddyfile` @seo bloğu `/w/* /tr/* /en/* /sitemap.xml /llms.txt /robots.txt` → `/srv/web-seo` statik, `Cache-Control: public, max-age=3600`, auth yok. `seo/generator.py` her whisky için `/tr/w/{id}` + `/en/w/{id}` üretir; sayfada `flavor_profile` **ham JSON değil** `_axes.map_to_app(parse_profile(...))` çıktısı, tek `original_tasting_note`, `evidence_count` sayısı, fiyat yok. Tier A = 2.483 whisky (canlı production.db, 2026-08-12 ölçümü; hardcode DEĞİL).

Yani "anonim kullanıcı flavor radar'ı görsün mü" sorusu SEO tarafında zaten **evet**; Flutter tarafında **hayır**. Bu spec, Flutter app'e aynı veriyi **aynı kurallarla** (response shaping) ama **bounded subset** ile açar. Yeni maruziyet yaratmaz; mevcut SEO sınırını app'e taşır.

**Kök neden (product):** login wall, deneme sürtünmesi yaratıyor. **Kök neden (güvenlik):** tam anonim katalog = `flavor_evidence`, canonical vector'ler gibi aylarca süren entity resolution/source audit emeğinin bulk scrape'e açılması. Çözüm: anonim erişim, SEO'nun zaten public ettiği verinin **küçük, deterministik, shaped** bir dilimiyle sınırlanır.

## 2. Governance kararları (bu spec)

| # | Karar | Gerekçe |
|---|-------|---------|
| G1 | Bu spec, ff28225'in (2026-08-10, catalog per-user bearer restore) **bilinçli kapsam genişletmesi**dir; "anonim açalım" diye sessizce geçiştirilen bir geri dönüş değildir. Gerekçe burada: hangi alt küme, hangi alanlar, neden bu sınır scrape maliyetini kabul edilebilir tutuyor. | Sessiz kapsam kayması (`knowledge_*` örneği) altı ay sonra "neden böyleydi" sorusuna dönüşür; bu spec o soruyu önden cevaplar |
| G2 | **Katman ayrımı:** Anonim Okuma Katmanı = erişim/ürün kontratı. Rate-limit tuning, Cloudflare bot/WAF, ToS, robots.txt politikası, bot/abuse monitoring, CDN/SEO hardening = **ayrı hardening fazı**, bu spec'in scope dışı. | İkisini aynı spec'e koymak değişiklik yüzeyini büyütür, test başarısızlığında hangi kontratın bozulduğunu belirsizleştirir |
| G3 | Allowlist üyeliği, `evidence`/`price-history`/`tasting-notes` endpoint'lerine **anonim erişim hakkı VERMEZ**. Bu üç endpoint **her koşulda authenticated-only**dir. | "Allowlist'te olmak" ≠ "her endpoint'e anonim erişim". İmplisit varsayım kırılır; evidence (kaynak referansları) ve fiyat en korunaklı veri sınıfıdır |
| G4 | Allowlist **build-time artifact**; runtime asla yeniden türetmez. Kontrat artifact'tir. | DB değişince davranış değişsin diye değil, deploy başına deterministik, test edilebilir bir sınır sabitlensin diye |
| G5 | Anonim response-shaping = **SEO sayfası alanlarıyla birebir**; `seo.generator` kontratı referans alınır, yeniden icat edilmez. | Tek kontrat, iki yüzey (statik sayfa + API) aynı dili konuşur; drift riski sıfırlanır |

## 3. Allowlist build (build-time, deterministic)

```
live production.db (mode=ro, ProductionReadAdapter üzerinden)
→ seo.tiers.tier_map()  (yeniden icat YOK — seo/tiers.py import edilir)
→ Tier A (canlı DB: 2.483 — hardcode DEĞİL, build-time hesaplanır)
→ sitemap üyeliği (C_no hariç; zaten sitemap dışı)
→ stable sort: evidence_count DESC, name COLLATE NOCASE, whisky_id (tie-break)
→ first N   (N = env ANONYMOUS_CATALOG_LIMIT, default 150)
→ artifacts/anonymous_allowlist.json
```

Artifact şeması:

```json
{
  "version": 1,
  "build_date": "2026-08-12",
  "db_sha256": "<sha256 of production.db at build time>",
  "n_limit": 150,
  "tier_a_total": 2483,
  "ids": ["<whisky_id x150>"]
}
```

- `db_sha256`, DB değişince artifact'in bayat olduğunu kanıtlar (yeniden build zorunluluğu).
- N dışında hiçbir kayıt anonim API'den erişilebilir değildir — enforcement §4'te.
- Yeni script: `scripts/build_anonymous_allowlist.py` (seo.tiers + seo.axes import eder; read-only connect; production.db'ye dokunmaz).
- Yarın Tier A 2.600 olursa spec eski `2483` sayısına kilitlenmez — build-time hesaplanır.

## 4. API yüzeyi — Strategy B (aynı path, auth-optional)

- `get_current_user` router-level dependency'den çıkar; **per-endpoint Optional** yapılır.
- Authenticated istek → mevcut `DbReadService` davranışı **hiç değişmez** (auth regression testi bunu kanıtlar, §8).
- Anonim istek → yeni ince `AnonymousCatalogService`: her sonucu artifact ID setiyle **intersect** eder + §5 shaping'i uygular.
- Frontend `DbWhiskyApiClient` **zaten token null iken Authorization header'sız istek atıyor** (`db_whisky_api_client.dart:60-63`) — guest modda client değişikliği gerekmez, sadece token yok.
- Yanıt zarfına `"scope": "anonymous"` alanı eklenir (aynı URL iki davranış döndüğü için client'a netleştirme sinyali; authenticated yanıtta `"scope": "user"`).

### Endpoint politikası

**Anonim açık:**
| Endpoint | Davranış |
|---|---|
| `GET /api/db/whiskies` | allowlist ⊆ sonuç; `offset/limit` allowlist boyutunu aşamaz |
| `GET /api/db/whiskies/{id}` | id ∉ allowlist → 404 |
| `GET /api/db/whiskies/{id}/flavor-profile` | id ∉ allowlist → 404 |
| `GET /api/db/search` | sonuçlar allowlist'e kırpılır |
| `GET /api/db/distilleries` | yalnızca allowlist'teki whiskylerin distillery'leri |
| `GET /api/db/filters` | vocab sabitleri — sızıntı yok |

**Authenticated-only (sıfır istisna, G3):**
| Endpoint | Neden |
|---|---|
| `GET /api/db/whiskies/{id}/evidence` | `official_source_references` — aylarca süren source audit emeği; kaynak/url/domain |
| `GET /api/db/whiskies/{id}/price-history` | Product Rule: fiyat ASLA API/UI'da; redaction katmanına ek olarak endpoint seviyesinde kapalı |
| `GET /api/db/whiskies/{id}/tasting-notes` | tam liste anonimde yok; anonim yalnızca §5'teki tek shaped notu alır |

- `offset/limit` artık `CATALOG_MAX_OFFSET` değil, **allowlist boyutu** ile sınırlanır — parametre ne olursa olsun sonuç kümesi bounded subset'tir (escape testi §8).
- Mevcut rate limit'ler (120/min per-IP) bu spec'te **değişmez** (tuning = hardening fazı, G2).

## 5. Response shaping kontratı (SEO parity — G5)

Anonim yanıt alanları = SEO sayfası alanlarıyla birebir (`seo/generator.py` `w_data` yapısı referans):

| Alan | Değer |
|---|---|
| `flavor_profile` | `_axes.map_to_app(parse_profile(...))` — 8 app ekseni; **ham `flavor_profile` JSON ASLA** |
| `tasting_note` | tek `original_tasting_note` |
| `evidence_count` | sayı; **ham `flavor_evidence` row'ları ASLA** |
| fiyat | **YOK** (Product Rule; ProductionReadAdapter redaction'ına ek katman) |
| kaynak alanları | `SourceGuard.sanitize_collection(..., is_manual=False)` zaten public path'te uygulanıyor — korunur |

- Client'ın okuduğu JSON key'leri korunur (guest UI = mevcut ekranlar, sadece login'siz).
- `flavor_profile` normalize mantığı `DbReadService._normalize_flavor_profile`/`_map_canonical_to_app_axes` ile aynıdır; `seo.axes` ile ayna tutarlılığı zaten var (tiers.py docstring, REVİZYON R1) — anonim servis bu iki yerden birini çağırır, üçüncü kopya yazılmaz.

## 6. Cache contract (ZORUNLU — bu spec'in parçası)

**Problem:** Aynı path hem token'lı hem token'sız çağrılabiliyor, farklı response shape dönüyor. Cloudflare `Authorization` header'ını varsayılan cache key'e almaz → zengin (authenticated) yanıt cache'lenip anonim isteğe servis edilebilir ya da tersi. G3'ün "sıfır istisna" kuralını uygulamada bozabilecek tek mekanizma budur — `evidence`/`price-history` gibi authenticated-only endpoint'lerin yanıtı cache üzerinden anonim tarafa sızabilir.

**Mevcut durum:** `deploy/Caddyfile` `/api/*` bloğu zaten `header Cache-Control no-store` gönderiyor (api:8080 reverse proxy). Bu iyi bir taban ama tek başına yeterli değil — davranış proxy katmanına bağımlı.

**Spec kararları:**

1. **`evidence`, `price-history`, `tasting-notes` endpoint'leri (authenticated-only):** response'a `Cache-Control: private, no-store` header'ı **app katmanında** (FastAPI response header) eklenir — proxy/Caddy katmanına bağımlılık olmadan CF edge cache'i bypass edilir. Vary eklenmesine gerek yok: `private, no-store` cache'i tamamen devre dışı bırakır.
2. **Anonim açık endpoint'ler:** response `Cache-Control: public, max-age=<kısa TTL>` olabilir (SEO statik katmanıyla tutarlı, `max-age=3600` üst sınır — tuning hardening fazında). Yanıt zaten shaped + bounded olduğundan public cache güvenli.
3. **Aynı path iki scope döndürdüğü için (Strategy B):** authenticated yanıtlara `Cache-Control: private, max-age=0` uygulanır — böylece **herhangi bir** authenticated yanıt (yalnızca evidence değil) CF'de cache'lenmez; anonim yanıtlar public kalır. Bu, scope sızıntısını path bazında değil **auth durumu bazında** engeller. **Öncelik:** §6.1'deki üç endpoint (`evidence`/`price-history`/`tasting-notes`) `private, no-store` alır — bu, §6.3'ün genel `private, max-age=0` kuralını **ezer**; `no-store` her zaman kazanır.
4. Alternatif/ileri seviye (bu spec'te zorunlu DEĞİL, hardening fazına not): cache key'e `Authorization`/scope dahil etme — Caddy `header_up Authorization` + CF Cache Key custom rule. Şimdilik 1-3 yeterli.

## 7. Guest UI (frontend)

- `main.dart:107` — `!auth.isLoggedIn → AuthScreen` yerine: `AuthScreen`'e **"Misafir olarak keşfet"** butonu eklenir → `MainNavigationScreen(guest: true)`.
- `guest: true` iken: katalog/searş/detail ekranları token'sız `DbWhiskyApiClient` çağrılarıyla çalışır; sync/auth yazma eylemleri (favori, kayıt, profil) "giriş yap" CTA'sına yönlendirir.
- Authenticated path davranışı değişmez.
- Detail screen "Resmî Kaynaklar" bölümü (`detail_screen.dart:85,310`) **logged-in kullanıcılarda kalır** (değişiklik yok); guest'te endpoint 404/403 döneceği için bölüm gizlenir (client tarafı koşul: `isLoggedIn` ise göster).

## 8. Verification (test matrisi)

| # | Test | Beklenti |
|---|------|----------|
| T1 | Allowlist determinism | Aynı DB + aynı N → aynı artifact (sha256 birebir) |
| T2 | Allowlist containment | Anonim sonuç kümesi ⊆ artifact `ids`; `offset/limit` ile escape denemesi (büyük offset, `limit=100`) → boş/404, allowlist dışı kayıt DÖNMEZ. **Edge-case:** allowlist boyutu = 150 iken `offset=149, limit=100` → 149. kayıttan sonrası **boş dizi döner, hata DEĞİL** (boundary'de offset+limit > boyut = boş sonuç, 4xx değil); `offset=150` → boş |
| T3 | Response-shape leakage | Anonim yanıtta `production_price`/`price_value` YOK; `flavor_profile` ham canonical JSON DEĞİL (app-axes map); `flavor_evidence` ham row YOK |
| T4 | Allowlist-üyeliği ≠ endpoint hakkı (G3) | Allowlist'teki bir id'nin `evidence`/`price-history`/`tasting-notes` endpoint'ine **anonim** istek → 401/403 |
| T5 | Auth regression | Token'lı istekler mevcut davranışı birebir korur; mevcut backend suite (53 test) yeşil kalır |
| T6 | **Cache leak regresyon (ZORUNLU)** | Aynı `whisky_id`'ye **önce token'lı, sonra token'sız** istek → yanıtlar farklı kalır (authenticated zengin, anonim shaped); authenticated yanıtta `Cache-Control: private` var; cache üzerinden scope sızıntısı yok. Test, cache header'larını da assert eder |
| T7 | Guest UI/API integration | Flutter: guest akışı (age gate → "Misafir olarak keşfet" → katalog görünür); authenticated akış regresyonsuz |

**Kabul kriterleri:**
- T1–T7 yeşil; backend suite yeşil; frontend guest akışı manuel doğrulanmış.
- `grep -rn "Cache-Control" backend/app` → authenticated-only endpoint'lerde `private` (T6 ile kilitli).
- production.db'ye yazma YOK (tüm testler read-only / temp copy; HARD RULE).

## 9. Scope dışı — ayrı hardening fazı (bilinçli, G2)

- Rate-limit tuning (per-IP + per-session, agresif kısa pencere)
- Cloudflare bot/WAF kuralları (bot management, anonim pattern throttle/captcha)
- ToS güncellemesi (scraping yasağı), `robots.txt` politika değişiklikleri
- Bot/abuse monitoring (anormal trafik loglama)
- CDN/SEO hardening (cache-key'e scope dahil etme dahil)
- `/admin/review/*` rate-limit (security audit bulgusu — ayrı iş)

## 10. İlgili varlıklar

- `backend/app/routers/db_api.py` (auth gate değişimi)
- `backend/app/services/anonymous_catalog_service.py` (YENİ — ince; `DbReadService`'i sarar, allowlist intersect + shaping; DbReadService'e metod eklenmez)
- `backend/app/auth/routes.py` (`get_current_user` Optional kullanımı)
- `seo/tiers.py`, `seo/axes.py` (allowlist build import kaynağı)
- `scripts/build_anonymous_allowlist.py` (YENİ)
- `artifacts/anonymous_allowlist.json` (build çıktısı; git'e girmez — build artifact)
- `frontend/lib/main.dart`, `frontend/lib/features/auth/presentation/auth_screen.dart` (guest girişi)
- `deploy/Caddyfile` (referans: @seo zaten public; /api cache header'ları zaten no-store)

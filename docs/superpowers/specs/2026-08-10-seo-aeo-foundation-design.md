# Malt Radar SEO/AEO Foundation — Tasarım Dokümanı

- **Tarih:** 2026-08-10
- **Durum:** Onaylandı (kullanıcı GO — bölüm bazlı inceleme sonrası)
- **Kapsam:** Alt sistem 1 (SEO/AEO teknik temel) + ölçüm çekirdeği. Bu spec'in terminal hedefi: tam otonom üretim + deploy + ölçüm.
- **İlgili kararlar:** Pazar TR+EN paralel • Başarı ölçütü: kayıtlı kullanıcı (email register) • İçerik kapsamı: 4.750 viski + listeler, kalite katmanlı • Otonomi: tam (üretim+deploy+submit otomatik)

---

## 1. Amaç

Malt Radar'ın organik büyümesi için **indexlenebilir + answer-engine alıntılanabilir** statik içerik katmanı kurmak. Funnel: keşif (Google / LLM answer engine / X) → statik sayfa → register CTA → app (Flutter, mevcut). Dönüşüm ölçütü: kayıt.

Mevcut durumda site tek Flutter canvas'ıdır — her URL aynı boş HTML döndürür (sitemap.xml dahil SPA fallback), crawler ve LLM'ler içerik göremez. Bu spec bunu çözer.

## 2. Mimari

Ayrı statik SEO katmanı (SSG). Flutter uygulamasına sıfır risk: ayrı dizin, ayrı süreç, ayrı deploy.

```
seo/                          # YENİ modül — production.db'ye ASLA yazmaz (salt okunur)
├── generator.py              # SSG: DB → statik HTML + sitemap + llms.txt (stdlib-only)
├── templates/                # f-string şablonlar (jinja2 YOK — sunucuda dep yok)
├── build/                    # çıktı (gitignore; commit edilmez)
│   ├── tr/w/<whisky_id>/index.html   # 4.392 viski × 2 dil (indexlenebilir)
│   ├── en/w/<whisky_id>/index.html
│   ├── tr/w/<whisky_id>/index.html   # aynı desen; C-noindex 358 × 2 (noindex,follow, sitemap dışı)
│   ├── tr/bolgeler/...  en/regions/...  # bölge/ülke/üretici listeleri
│   ├── tr/  en/                        # landing sayfaları
│   ├── sitemap.xml           # tr+en, lastmod'lu
│   ├── llms.txt              # AEO: LLM erişim haritası
│   └── robots.txt            # Disallow /api/ + Sitemap: referansı
└── deploy_seo.sh             # ssh → generate → verify → swap → submit (fail-loud)
```

**Servis (Caddy, mevcut VM):**

| Yol | Kaynak |
|---|---|
| `/w/*`, `/tr/*`, `/en/*`, `/sitemap.xml`, `/llms.txt`, `/robots.txt` | `deploy/web-seo/` (yeni, statik) |
| `/` + geri kalan | `deploy/web-build/` (Flutter; hash-routing → çakışma yok, doğrulandı) |

Flutter routing hash-based (`#/...`) — statik yollarla çakışma yok (doğrulandı). Cloudflare: statik sayfalar cache-friendly.

## 3. İçerik modeli — deterministik Tier kuralı

Kural tek geçişli, tam bölümleme, örtüşme yok. `completed_fields` ölü alan (tümü 0) — kullanılmaz.

| Tier | Kural (production.db'den) | Adet (lokal baseline 4.750) | Sayfa |
|---|---|---|---|
| **A** | `flavor_profile` JSON ≥2 aktif eksen VE ≥1 `flavor_evidence` | 2.371 | tam: h1, meta, JSON-LD, SVG radar + eksen metin listesi, tadım notları, evidence kaynakları, bölge/üretici linkleri, CTA |
| **B** | `flavor_profile` boş değil, A değil | 1.204 | kısa: h1, meta, minimal JSON-LD, "veri ekleniyor" + CTA |
| **C-indexable** | profile yok + `name` + `distillery_id` dolu | 817 | minimal: h1, canonical, CTA |
| **C-noindex** | profile yok + `distillery_id` eksik (name hep dolu) | 358 | üretilir, `noindex, follow`, **sitemap'e girmez** |

Sitemap'e giren toplam: (2.371+1.204+817) × 2 dil = **8.784** + liste sayfaları. Thin dilim %7.5.

**Listeler:** bölge × ülke × üretici (TR+EN), viski kartları + CTA. Landing: `/tr/`, `/en/`.

**Üretim verisi notu:** tier sayıları lokal baseline'dan (4.750). Canlı sunucu DB 4.598 — ilk canlı build'de oranlar kayar; bu beklenen, tier dağılımı her build'de raporlanır (bkz. §7 test 8).

## 4. Canonical & hreflang

**Self-canonical + hreflang ikilisi.** App'in per-whisky indexlenebilir URL'si yok (hash-routing + canvas) → statik sayfa içeriğin kendisidir.

```html
<link rel="canonical" href="https://maltradar.com/tr/w/W003805/">
<link rel="alternate" hreflang="tr" href="https://maltradar.com/tr/w/W003805/">
<link rel="alternate" hreflang="en" href="https://maltradar.com/en/w/W003805/">
```

TR↔EN eşleşmesi generator'da; her iki URL sitemap'e girer.

## 5. Schema & AEO

- **JSON-LD:** her viski sayfasında `BreadcrumbList`; sitede `Organization`. Tier A'da ayrıca `Product` (`name`, `description`, `category`, `brand`).
- **`offers`/`price` alanı JSON-LD'de YOK** (Product Rule).
- **`aggregateRating` YOK**: `meta_critic_score` eleştirmen puanıdır, gerçek yorum sayısı değil — Google rich-result politikası riski. Puan sayfada düz metin olarak görünür, şemada değil.
- **`llms.txt`** — site tanımı, ana bölümler, örnek sayfalar (answer engine erişim standardı, $0).
- **Semantik HTML:** tek h1, heading hiyerarşisi, tanımlı listeler.

## 6. Eksen vokabüleri (brand kararı)

- HTML'de görünen eksenler: **7 app ekseni** (`fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal`) — app'in radar chart'ıyla aynı vokabüler, TR/EN lokalize.
- **`vector_*` depolama sütunları HTML'de YOK** (evidence depolama katmanı, dışarıda).
- **Etiketli radar**: SVG + metin listesi. Karar gerekçesi: 7 eksen zaten public açık JSON API'de kimliksiz servis ediliyor (format değişimi, maruziyet değil); medalyon logo'dur, radar veri görselleştirmesidir; AEO için etiketli metin alıntılanabilir içeriktir.
- **Fiyat HTML'e asla** — `production_price` şablonlara girmez (filter katmanı + test 2).

## 7. DB erişim mekanizması (guard'a dokunmaz)

**Bağlantı:** `sqlite3.connect('file:...?mode=ro', uri=True)` — sqlite yazma denemesinde kendisi fail eder.

**İzin modeli — platform ayrımı (doğrulanmış / çıkarım):**
- **Windows (lokal, DOĞRULANDI):** `icacls` DENY ACE yalnız `WD`+`AD`'yi (yazma) engeller; `RD` (okuma) açıktır. Bu oturumdaki salt-okunur sorgular düz kullanıcı process'i olarak çalıştı (tier dağılımı, schema, coverage).
- **Linux (sunucu, ÇIKARIM — kurulumda test edilecek):** POSIX mode bits aynı ayrımı verir; tek seferlik kurulumda deploy kullanıcısının canlı DB'ye okuma izni doğrulanır.

**Kısıtlar:**
- `db_write_guard.py`'a **sıfır değişiklik** — "guard-reassert" tartışması SEO'ya bulaşmaz; generator yazma yolunda değildir.
- **ACL lift YOK** — mevcut koruma aynen kalır.
- **Sunucu izin (scope-minimal):** `chown :deploygroup /srv/data/production.db` + `chmod 640` + deploy kullanıcısını gruba ekle. `chmod o+r` DEĞİL (tüm kullanıcılara okuma = gereksiz maruziyet).
- **Fiziksel güvence üçlüsü:** OS DENY (yazamaz) + `mode=ro` (sqlite reddeder) + read-only assertion testi (ihlal yakalanır).

## 8. Otonomi & Deploy

**Governance (kural 15 istisnası — bu oturumda kullanıcı tarafından verildi):**
Tam otonom onay **scoped**: yalnızca `seo/` modülü + `deploy_seo.sh` + Caddyfile. Backend/frontend koduna dokunmaz, production.db'ye yazmaz, `social/`'e karışmaz.

**Üretim yeri: sunucuda, canlı DB'den.** Lokal DB (4.750) ≠ sunucu canlı DB (4.598) — SSG lokalden üretirse sayfalar canlı API ile tutarsız olur (kırık CTA). Generator stdlib-only (f-string şablonlar) → sunucuda `python3` yeterli, pip dep yok.

**deploy_seo.sh akışı (`set -euo pipefail`, fail-loud):**
1. ssh VM: generator'ı canlı DB ile çalıştır → `build.tmp`
2. Doğrulama (`build.tmp` üstünde): fiyat grep, `_FORBIDDEN`, hreflang bütünlüğü, sitemap XML, iç linkler, tier dağılımı raporu + aralık kontrolü
3. **No-op optimizasyonu:** production.db SHA256 (mevcut basın çizgisi mekanizması — yeni şema icat edilmez) `.last_db_sha256` ile aynıysa → deploy atla
4. scp → `/srv/.../web-seo/` (mevcut dizine KOPYALA — dizini asla rm etme; bind-mount pitfall'ı, deploy_web.sh deseni)
5. Sitemap submit (GSC API) — başarısızsa log + sonraki tick retry, deploy'u bloklamaz
6. Canlı doğrulama: örnek URL'ler 200 + sitemap çekilebilir

**Cron'lar:**
| Cron | Sıklık | İş |
|---|---|---|
| deploy_seo | günlük TR 03:00 | yukarıdaki akış (no_agent script) |
| monitor | haftalık | GSC + GA4 + bozuk-link taraması → rapor |

**Hata yönetimi:**
- Generator/doğrulama hatası → exit non-zero → deploy yok, eski sürüm canlı kalır
- SSH erişilemez → fail-loud (alert), sonraki tick retry — sessiz başarısızlık yok
- Rollback: `web-seo.prev/` — deploy sonrası doğrulama bozuksa geri al
- Sitemap submit hatası → deploy'u bloklamaz

**GSC/GA4 kimlikleri:** `deploy/.env` (gitignored, 600). `deploy_seo.sh` loglarına env değeri asla — "never print token/API key/secret" kuralı log sanitization testiyle bağlanır.

## 9. Test matrisi

Ad-hoc harness + deploy adımı (repo suite'ine girmez):

| # | Test | Beklenti |
|---|---|---|
| 1 | Determinizm | aynı DB → 2 koşu aynı build hash |
| 2 | **Fiyat sızıntısı** | `production_price\|₺\|$\|€\|£\|TL\|price` grep → 0 |
| 3 | TR mevzuat | `_FORBIDDEN` desenleri (content.py'den) → 0 |
| 4 | Hreflang bütünlüğü | tr↔en çiftleri çift yönlü, canonical self |
| 5 | Sitemap | geçerli XML, URL sayısı == hesaplanan, noindex yok, çift yok |
| 6 | İç linkler | tüm hedefler build'de var |
| 7 | Read-only assertion | mode=ro bağlantıda yazma → fail |
| 8 | Tier dağılımı | rapor + aralık kontrolü (hard invariant: sitemap URL sayısı == hesaplanan; oran kayması warn) |
| 9 | E2E canlı | örnek URL'ler (A/B/C × tr/en + liste) 200; robots Sitemap satırı |
| 10 | XSS | tüm dinamik değerler `html.escape` |

## 10. Ölçüm (Cron 2 — haftalık)

- **GSC:** indexlenen sayfa (8.784 hedefine karşı), gösterim/tıklama/konum, top sorgular, TR↔EN kırılımı
- **GA4:** oturum, kaynak (organik / answer-engine referral / X / direct), **kayıt dönüşümü** (register event)
- **Bozuk link:** kendi domain'inde 404 taraması
- **AEO spot-check:** Perplexity/ChatGPT'ye örnek sorgu → maltradar alıntılanıyor mu (rapora eklenir)

**30 günlük eşikler:** indexlenen sayfa > 0 • organik gösterim > 0 ve artış • register hunisi ölçülüyor • ≥1 AEO alıntılanma

## 11. Açık kalemler (insan adımı / ayrı iş)

1. **Sunucu DB 4.598 vs lokal 4.750** — SSG canlı DB'den üretir; sayfa sayısı 4.598'i yansıtır. Sunucu DB güncellemesi istenirse ayrı promotion işi (ProductionGate + GO).
2. Sunucuda `python3` varlığı doğrulanacak (yoksa tek apt adımı).
3. Sunucu izin provisioning: `chown :deploygroup` + `chmod 640` + grup üyeliği (cron'a girmeden önce; Linux okuma erişimi bu adımda doğrulanır — §7).
4. GSC + GA4 API kimlikleri (Google hesabı — bir kez, sonra otonom).
5. Caddyfile güncellemesi (web-seo route'ları) — tek seferlik web deploy ile.

## 12. İlgili varlıklar

- Skill: `deploy-sqlite-webapp-anti-scrape` (anti-scrape desenleri, deploy pitfall'ları)
- Skill: `malt-radar-social` (içerik gate deseni `_FORBIDDEN`)
- Mevcut: `deploy_web.sh` (deploy deseni), `frontend/web/robots.txt`, açık `/api/db` (sayfa tavanı `limit ≤ 100` mevcut; rate limit/offset guard hardening ayrı iş)
- Governance: AGENTS.md kural 15 istisnası bu pipeline'a özel, kullanıcı GO'su ile kayıtlıdır

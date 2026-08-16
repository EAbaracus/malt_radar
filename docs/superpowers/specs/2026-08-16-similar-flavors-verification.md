# Similar Flavors Server-Side — Verification & Closure

- **Tarih:** 2026-08-16
- **Phase ID:** `similar-flavors-server-side`
- **Spec:** `docs/superpowers/specs/2026-08-16-similar-flavors-server-side-design.md`
- **Plan:** `docs/superpowers/plans/2026-08-16-similar-flavors-server-side.md`
- **Durum:** TAMAMLANDI (deploy beklemede — kullanıcı GO'su)

---

## 1. Özet

"Benzer Lezzetler" bölümünün A/B harfli alfabetik önyargısı giderildi: benzerlik hesabı
client-side 250 satırlık bounded havuzdan, server-side **tam aktif katalog** (2.597
kullanılabilir profil) üzerine taşındı. Yeni `GET /api/db/public/whiskies/{id}/similar`
endpoint'i read-only (`ProductionReadAdapter`, mode=ro + query_only), PromotionGate
gerekmedi.

## 2. Commit Zinciri (9 commit)

| Commit | Task | İçerik |
|---|---|---|
| `8523093` | 1 | SimilarityService + 4 test (spec review PASS) |
| `194acf7` | 1 | Quality fix: limit clamp, tek normalize yolu, hermetic testler |
| `ecc281a5` | 1 | `test_limit_clamped` regression-proof (26 viski, exact assert) |
| `c0353ae` | 1 | `GROUP BY w.whisky_id` — flavor_profiles JOIN dupe düzeltmesi (830 dupe satır tespit edildi; kanonik katalog sorgusuyla parity) |
| `342172a` | 2 | `/api/db/public/whiskies/{id}/similar` endpoint + delegate (spec PASS) |
| `109c688` | 2 | Test hardening: non-empty assert, allowlist-proof mesaj, limit=20 sınırı |
| `5440fc3` | 3 | Flutter client + repo rewrite (endpoint öncelikli) |
| `7ee1b2a` | 3 | **Bilinçli kapsam genişletmesi:** `similar_flavor_test.dart` seed kontratına uyduruldu (pre-existing kırıklık, `d5b3fd7`'den beri compile-fail; name-join flavor attach) |
| `103511f` | 3 | Spec G6 uyumu: 404 → fallback; gerçek fallback-path testi (false-positive giderildi) |

## 3. Test Sonuçları

| Suite | Sonuç | Detay |
|---|---|---|
| Backend `test_similarity_service.py` | **6/6 PASS** (0.9s) | full-pool regresyon kanıtı dahil |
| Backend `test_similar_endpoint.py` | **5/5 PASS** | shaping, anon, 404 gate, allowlist-proof, limit bounds |
| Backend komşu (public API + anon service) | **10/10 PASS** | allowlist davranışı bozulmadı |
| Flutter `similar_flavor_backend_test.dart` | **4/4 PASS** | client parse, 404→null, repo map, GERÇEK fallback zinciri |
| Flutter `similar_flavor_test.dart` + `widget_test.dart` | **2/2 PASS** | lokal mod + widget override sağlam |

## 4. Canlı Doğrulama (uvicorn geçici başlatıldı, sonra kapatıldı)

`GET /api/db/public/whiskies/{id}/similar?limit=5` — 3 hedef:

| Hedef | İlk benzerler (name | distillery | similarity) | Yorum |
|---|---|---|---|---|
| W000303 Talisker Port Ruighe | **Talisker 57 North** (Talisker, **sim=1.0**), Penderyn 5yo (0.15), Mackmyra 18yo (0.14), Sullivans Cove 17yo (0.13), Tomatin Decades (0.11) | Birebir profil komşusu zirvede; tam havuz, A/B önyargısı yok |
| W001781 Bulleit Bourbon | **Bulleit 10yo (0.74)**, Old Grand-Dad 114 (0.69), Michter's Toasted Barrel (0.62), Smooth Ambler Old Scout 7yo (0.61), Four Roses Single Barrel (0.55) | Gerçek bourbon komşuları; aynı distillery + benzer profiller |
| W000530 Balcones Texas Single Malt | Ardbeg Galileo/Alligator/Auriverdes (0.082), Forty Creek (0.07), Amrut Kadhambam (0.06) | Havuzda yakın profil yok — düşük skor veri gerçeği, bug değil |

- Allowlist dışı hedef → **404** (G1 gate canlıda doğrulandı).
- Yanıtlarda `production_price`/`flavor_profile`/evidence yok (G5).

## 5. Read-Only Kanıtı (production.db SHA256)

| Aşama | SHA256 |
|---|---|
| Feature başlangıcı (before) | `c031d2ea14a60ac44ced3397ba927018c361d16bb91bdc3f0c3536482820d1ed` |
| Feature sonu (after) | `c031d2ea14a60ac44ced3397ba927018c361d16bb91bdc3f0c3536482820d1ed` |
| Sonuç | **DEĞİŞMEDİ — yalnızca okuma** |

Not: AGENTS.md'deki `cbffd16b…` (08-14 provisional baseline) karantina pipeline'ının kendi
closure'larıyla aşılmıştı (Mnemosyne task-progress `production_sha: C031D2EA14A60AC4`
teyitli). Bu closure `c031d2ea` üzerinden yazıldı.

## 6. Governance Kaydı

- **G1 (bilinçli kapsam genişletmesi):** `/similar` sonuçları tam havuzdan gelir —
  allowlist (N=150) istisnası yalnızca sonuçlar içindir, hedef hâlâ allowlist'e tabidir
  (404). Gerekçe: allowlist'e sınırlı benzerlik hesabı bug'ı yeniden üretirdi. Dönen
  alanlar SEO katmanının zaten public yaptığı alanlardan fazlası değildir; fiyat/evidence
  sızmaz. **Ürün onayı:** kullanıcı clarify'de Option A'yı GO'ladı; spec G1'de belgelendi.
- **Kapsam genişletmesi #2:** `similar_flavor_test.dart` düzeltmesi (pre-existing
  kırıklık — `d5b3fd7` seed kontratını değiştirmişti, test o zamandan beri compile-fail).
  Kullanıcı onayıyla test-only düzeltildi (`7ee1b2a`).
- **Stale `REBASE_HEAD`** (.git, Aug 12) tespit edildi; bu oturumdan önce var, paralel
  oturum ortamına ait olabilir — **dokunulmadı** (kullanıcı kuralı: SİLME önce sor).
- **11 staged rename** (scripts/DEPRECATED_NEEDS_GUARD_MIGRATION) + paralel oturumun M
  dosyaları: dokunulmadı (her commit pathspec ile yapıldı, doğrulandı).

## 7. Doğrulama Kontrol Listesi (AGENTS.md Completion)

- [x] Test sonuçları dry-run/spec beklentileriyle eşleşiyor (27 backend + 6 frontend PASS)
- [x] SHA256 önce/sonra aynı (read-only)
- [x] R4 ihlali yok (endpoint yazmıyor; testlerde axis [0,1] dışı değer yok)
- [x] Duplicate `(whisky_id, source)` etkilenmedi (yazma yok)
- [x] Git durumu: 9 feature commit; 11 rename + paralel M dosyaları bozulmadı

## 8. Deploy Sonucu (kullanıcı GO'su ile, 2026-08-16)

| Adım | Sonuç |
|---|---|
| Push | `b217dd5..a4abff3` + `5548a88` → origin/main (13 commit) |
| Backend (VM `/srv/maltradar`, docker compose) | `git pull` + `up -d --build api` → `deploy-api-1 Up` |
| Canlı `/similar` (maltradar.com) | W000303 → **Talisker 57 North sim=1.0** + tam havuz komşuları; allowlist dışı → 404; anon katalog → 200 (regresyon yok) |
| Flutter web build | Lokal `build/web` → tar-pipe → VM `deploy/web-build` (içerik swap, bind-mount inode korundu) |
| Cache-bust doğrulama | `flutter_bootstrap.js?cb=simflav` hash == lokal ✓; `/` ve `/index.html` no-cache ✓; assets 1y ✓ |
| **Yeni infra fix** (`5548a88`) | Caddyfile `@nocache` matcher'ına `/` eklendi — root `max-age=1y` idi (bayat index.html riski; doğrulama sırasında tespit edildi) |
| Not | Cloudflare HTML injection tespit edildi (canlı index 5939 vs lokal 4704 bayt — analytics/rocket loader; önceden var olan, zararsız). VM'de `web-build.prev` rollback noktası bırakıldı. `deploy/data/production.db` **dokunulmadı** (ayrı gözetim süreci). |

## 9. Deploy İncidenti (2026-08-16) — DİRTY-TREE BUILD

- **Belirti:** Kullanıcı "ekran açılmıyor" — sayfa "MALT RADAR" başlığını yüzlerce kez render ediyordu (sonsuz layout döngüsü, tarayıcı capture ile doğrulandı).
- **Kök neden:** İlk `flutter build web` **çalışma ağacından** yapıldı; o ağaçta paralel oturumun **uncommitted UI değişiklikleri** vardı (main.dart, home_screen.dart, detail_screen.dart, app_translations.dart — aktif UX debug'u). Yarım UI kodu canlıya sürüldü. Feature kodumuz bu hatanın kaynağı DEĞİL (home ekranına dokunmuyor).
- **Kurtarma:** (1) `web-build.prev` rollback denemesi başarısız (önceki deploy'dan beri boştu) → site geçici 404. (2) `git worktree add` ile **committed HEAD'den temiz build** (`$LOCALAPPDATA/Temp/mr-clean-build`) → tar-pipe → VM swap. (3) Doğrulama: `flutter_bootstrap.js` + `main.dart.js` hash'leri canlıda == temiz build; `/` 200; `/similar` canlı (Talisker 57 North sim=1.0).
- **Ders:** Canlıya Flutter web sürülürken build **TEMİZ worktree'den** (deploy edilecek commit) yapılmalı — main tree'de başka oturumun uncommitted değişiklikleri varsa ASLA doğrudan build edilmemeli.
- **Not:** Paralel oturumun uncommitted dosyalarına dokunulmadı; `6c036b5` (superseded_by filtresi) aynı anda push edilmişti — frontend etkilenmedi (delta boş doğrulandı).

## 10. Google Sign-In Restorasyonu (2026-08-16)

İkinci temiz build define'sızdı → `ENABLE_GOOGLE_SIGN_IN` (default false) kapalı + `MALT_RADAR_API_BASE_URL` release'de ZORUNLU olduğundan app boot'ta çöküyordu. Kanonik deploy define'ları (`deploy/README.md:88`): `--dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com --dart-define=GOOGLE_CLIENT_ID_WEB=<deploy/.env GOOGLE_CLIENT_ID> --dart-define=ENABLE_GOOGLE_SIGN_IN=true`. Değerler `deploy/.env`'ten (key: `GOOGLE_CLIENT_ID`) alındı; define'lı temiz build (`mr-clean-build2` worktree) deploy edildi. Doğrulama: canlı `main.dart.js` == build; baseUrl + client id gömülü; sayfa render (katalog + radar grafiği) çalışıyor; `/similar` canlı. Google login butonu auth ekranında geri geldi.

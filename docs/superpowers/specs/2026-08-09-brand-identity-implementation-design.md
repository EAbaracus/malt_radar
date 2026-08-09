# Malt Radar — Marka Kimliği Uygulaması (App + Web)

Tarih: 2026-08-09
Kapsam: Flutter frontend (`frontend/`) marka kimliğine tam süpürme. Web = Flutter `build/web` çıktısı (Caddy, maltradar.com). Ayrı HTML yok.

## Onaylanan kararlar

| # | Konu | Karar |
|---|---|---|
| 1 | Amblem etiketleri | **Etiketsiz medallion.** Canonical eksen isimleri yalnızca app içindeki gerçek radar chart'ta. `AXES` / SM-PT-SH-FR-SW-SP-MR sabiti ve label render'ı GELMEZ. |
| 2 | Webapp kapsamı | **Tek Flutter codebase.** Web = build/web, mobile = APK. Ayrı landing HTML yok. |
| 3 | Fontlar | **4 .ttf asset bundle** (Fraunces, Source Serif 4, Courier Prime, Inter). `google_fonts` runtime indirme kaldırılır. Web+mobile tek kaynak, offline-safe. |
| 4 | Tema süpürmesi | **Tam süpürme (one-shot).** Dark-only bu sprint; light theme ayrı planlanır. |
| 5 | Medallion | **`CustomPainter`** tek true-source (`level:` master/icon/micro). Launcher ikonu ayrı statik PNG (`flutter_launcher_icons`). |

## Blokaj çözümü — eksen vokabüleri

Ürünün gerçek canonical eksen seti (production.db `flavor_profiles.flavor_profile` JSON + app `maltRadarFlavorAxes`, `flavor_profile_normalizer.dart:3` — BİREBİR aynı):

```
fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal
```

Marka dokümanı açılışındaki SM/PT/SH/FR/SW/SP/MR seti ingestion/sourcing vokabülerinden türetilmiş; app canonical setiyle uyuşmuyor (`smoky_peaty` tek eksen → SM/PT ayrımı yapay bölünme). Çözüm: medallion etiketsiz kalır, isimler yalnızca app radar chart'ta. Amblem "7 eksenli ölçüm"ün sabit sembolüdür; vokabüler iki yerde senkron tutulmaz.

## Mimari & bileşenler

```
frontend/lib/
  core/theme/app_theme.dart            → marka tokenları + font haritası
  core/theme/app_theme_colors.dart     → marka palet sabitleri + MedallionPalette (YENİ)
  core/branding/brand_medallion.dart   → MedallionPainter (master|icon|micro) (YENİ)
  core/branding/brand_medallion_widget.dart → Medallion widget + sweep animasyonu (YENİ)
  features/flavor/presentation/widgets/flavor_radar_chart.dart → renk AppTheme'e; canonical isimler korunur
frontend/pubspec.yaml        → 4 font asset, flutter_launcher_icons (dev)
frontend/android/...launcher → mipmap PNG + adaptive icon
docs/repo-check veya justfile → brass/gold anti-regresyon gate
frontend/test/brand_medallion_test.dart (YENİ)
```

### MedallionPainter kademeleri

| level | Çizim | Kullanım |
|---|---|---|
| `master` | 7-gen + 2 dış mühür halkası + orta/iç poligon hatları + köşe noktaları + ibre | splash / hero / neck-tag |
| `icon` | 7-gen + dış mühür halkası + köşe noktaları + ibre | app bar, list kartları, detail |
| `micro` | sadece 7-gen + ibre, tek çizgi kalınlığı | bildirim / küçük rozet |

- Etiketsiz her kademede; köşe noktaları (dots) durur = "7 eksenli ölçüm" sembolü.
- Renkler `AppTheme`/`MedallionPalette` token'larından: web/dot=copper, rim/needle=brass (light bg); dark bg'de zıt varyant.
- Geometri: marka dokümanındaki 7-gen vertex koordinatları ([100,30],[154.73,56.35]...) Flutter'a taşınır.

## Splash (kod gerçeğiyle teyit edildi)

İki katman, ikisi de uygulanır:
- **Native (ilk frame):** `android/app/src/main/res/drawable*/launch_background.xml` + mevcut mipmap'lar → char zemin + statik medallion drawable. Native'de animasyon yok.
- **In-app loading:** `lib/main.dart:40,59` `initAsync.loading` → `Scaffold + CircularProgressIndicator(AppTheme.primary)` → **medallion sweep animasyonunun tek yeri.** `CircularProgressIndicator` (infinite spinner) → `Medallion(level:'master', animate:true)` ile değişir. Tek sefer sweep→settle (0→410°→360°, easing .2,.7,.15,1), sonra sabit. Loop YASAK (marka kuralı).
- `prefers-reduced-motion`: `MediaQuery.disableAnimations` / aksesuar ile sweep kapanır (default `animate:false`, `true` yalnız loading).

## AppTheme palet mapping (mevcut → marka)

Mevcut (`app_theme.dart`): gold `#D4AF37` primary, amber `#B8860B` secondary, obsidian `#0F0F0F` bg, `#1A1A1A` surface. Dark-only.

| Mevcut | → Marka | Kullanım |
|---|---|---|
| `background` `#0F0F0F` | CaskChar `#1A120B` | zemin |
| `surface` `#1A1A1A` | `#241a10`; elevated `#2B1F14` | kartlar (koyu tema) |
| `primary` `#D4AF37` | Kettle Copper `#A6672C` | CTA, seçili, filtre çipleri, focusedBorder, slider |
| `secondary` `#B8860B` | Verdigris `#5C7A6E` | ikincil rozet, metadata, öneriler |
| `accent` `#F3E5AB` | Copper-dim `#8A5424` | alt vurgu |
| `error` `#E57373` | Oxblood `#6B1E23` | yalnız uyarı/hata (nadir) |
| `textPrimary` `#FDFDFD` | Parchment `#EDE1C8` | gövde (koyu zeminde) |
| `textSecondary` `#A5A6AC` | Parchment-lt / opak beyaz | ikincil metin |

## Brass kuralı enforcement (~%5)

- `brass` token'ı `AppTheme`'e KONMAZ; yalnız `app_theme_colors.dart` içinde `MedallionPalette.rimNeedle` değeri olarak yaşar → UI widgetları `AppTheme.brass` çağıramaz, tek kullanım noktası amblem.
- Mühür/ibre `MedallionPainter`'a `palette.rim/needle=brass`, `palette.web/dot=copper`.
- Gate (repo-check): `grep -rn "C9A227" frontend/lib` → yalnız `app_theme_colors.dart`; `grep -rn "D4AF37" frontend/lib` → 0 (eski gold kalıntısı); `grep -rn "assets/data.*csv" frontend/lib frontend/test` → temiz (anti-scrape).

## Font haritası

- display → Fraunces (Playfair Display gider)
- gövde (bodyLarge/Medium/Small) → Source Serif 4 (şu an Inter)
- UI (labelSmall, labelMedium, titleMedium, input, button) → Inter
- Courier Prime → bundle'lanır, temada hazır (damga kullanımı sonra)
- `google_fonts` paketi sadece `app_theme.dart`'ta import ediliyor → kaldırılır, `TextStyle(fontFamily:...)` kullanılır. Offline-safe, deterministik, Play-safe.

## Test planı

1. Envanter doğrulaması: hiçbir test renk assert etmiyor (gold/AppTheme/0xFF aramaları boş) → token swap test-odaklı değildir, suite yeşil kalması yeterli. TDD "kır/geçir" adımı YOK.
2. `brand_medallion_test.dart`: 3 level'de 7-gen + rim + needle path varlığı; master vs micro çizim yoğunluğu farkı; `animate:false` default (`pumpAndSettle` güvenli).
3. Splash/loading testi: sweep tek sefer biter, döngü yok; reduced-motion'daysa anim kapalı.
4. Tüm suite: `flutter test --no-pub` (iOS ephemeral `.packages` fix: `chmod -R u+w ios/Flutter/ephemeral/Packages/` + stale `.packages` temizliği).

## Değişmeyenler (koruma)

- `AppConfig.useDbApi` default (`MALT_RADAR_USE_DB_API` defaultValue:true) — DOKUNULMAZ (protected).
- Catalog CSV'ler client bundle'a ASLA geri gelmez. Font asset girer, `assets/data/*.csv` giremez.
- `production.db`'ye hiçbir yazma. Backend/schema DEĞİŞMEZ — tamamen frontend rebrand.

## Implement sırası

1. `app_theme_colors.dart` + palet sabitleri + `MedallionPalette`
2. `MedallionPainter` + `brand_medallion_widget.dart` + unit test (etiketsiz, 3 level)
3. `app_theme.dart` token swap + font haritası (google_fonts kaldır)
4. Ekran sweep'i: radar chart, filtre çipleri, bottom nav, detail, lists, settings + native launcher bg
5. In-app loading: `main.dart` CircularProgressIndicator → Medallion(animate:true)
6. Launcher ikonu (`flutter_launcher_icons`, micro/icon kademe PNG)
7. Brass/gold/csv gate'leri repo-check'e
8. `flutter test --no-pub` full suite yeşil
9. Nodata probe (web): `find build/web -name "*.csv"` boş, AssetManifest'te CSV yok

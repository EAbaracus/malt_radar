# "Beni Hatırla" + İsim Casing — Uygulama & Doğrulama Closure

- **Tarih:** 2026-08-16
- **Plan:** `.hermes/plans/2026-08-16_141500-remember-me-name-casing.md` (kullanıcı GO)
- **Yürütme:** subagent-driven-development (tüm task'ler spec+quality review ile)

## Feature A — Kalıcı Oturum ("Beni Hatırla")

| Commit | Task | Sonuç |
|---|---|---|
| `6520c6d` | A1+A2 | Teşhis: web'de drift worker/wasm pin'siz (drift/main + sqlite3 2.4.6) → protokol uyumsuz → sessiz in-memory fallback → token her reload'da uçar. Fix: `drift_worker.js`→drift-2.33.0 release, `sqlite3.wasm`→sqlite3-3.3.2 (SHA256 provenance doğrulandı). **Review APPROVED** |
| `42be983` | A3 | `_restore` artık token'ı `api.me()` ile doğrular: 401→clearSession+guestMode (anonim katalog, login'e DEĞİL), offline→cache koru, splash hang yok. **Review APPROVED** |

## Feature B — İsim Casing ("kesinlikle çözelim")

| Commit | Task | Sonuç |
|---|---|---|
| `7ad2300` | B1+B3 | Teşhis: production'da `name` KANONİK, `original_name` ham küçük ikiz (3.791); frontend DTO original_name'i tercih ediyordu. İlk title-case agresifti → **869 regresyon** (review REQUEST_CHANGES). |
| `2dfe99e` | B4 | Brand/ürün istisna listesi (ImpEx, WhistlePig, anCnoc, GlenDronach, SMWS, Mc/Mac possessive'leri... web-doğrulanmış) + possessive `'s` kuralı. |
| `924ce0c` | B3-fix | **KOŞULLU GATE**: yalnızca `name == name.lower()` isimler title-case (143 hedef), kanonik isimlere dokunmaz → **korpus 143 değişim / 0 regresyon** (review APPROVED). |
| (çıkarıldı) | B2 | Dart util gereksiz — backend tek kanonik katman (YAGNI, bilinçli). |

## Deploy (kullanıcı GO, TEMİZ worktree build dersi 2026-08-16)

- Backend: casing gate canlıya (`git pull` + `docker compose up -d --build api`).
- Frontend: temiz worktree'den (HEAD) kanonik define'lar + yeni drift worker/wasm ile build → VM swap.
- **Canlı doğrulama:** bootstrap hash == build; `drift_worker.js`+`sqlite3.wasm` 200; "/similar" kanonik isimler (Talisker 57 North, Penderyn 5yo, Mackmyra 18yo); allowlist "Aberlour A'Bunadh" / "10yo" korunmuş; root 200; Google login flag+client id gömülü.

## Kullanıcı E2E (yapılacaklar — tarayıcıda)
1. **Hard reload** (Ctrl+Shift+R) — yeni build + drift worker v4.
2. Google ile login → **reload** → oturum KALMALI ("Beni Hatırla" — IndexedDB persist). Eskiden reload'da login isterdi.
3. Katalog + detail sayfalarında isimler tutarlı (Aberlour A'Bunadh, WhistlePig, BenRiach).

## Bilinen Notlar (pre-existing / kapsam dışı)
- `distilleries.name` "Angel'S Envy Cask" — **pre-existing kaynak-veri hatası** (doğrusu "Angel's Envy"); similar sonuçlarında görünür. Ayrı govern edilmiş PromotionGate fazı gerektirir (bu kapsam dışı).
- A3 non-blocking review notu: komşu `FakeAuthApi`'ye `me` override önerilir (flake riski) — takip.
- 22 staged rename + paralel oturum dosyaları dokunulmadı; stale `REBASE_HEAD` (Aug 12, ölü) yine de görünüyor — dokunulmadı.
